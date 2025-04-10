from fastapi import APIRouter, Depends, HTTPException, status, Response, Form, UploadFile, File, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
import os
import httpx
import asyncio
import json
import base64
import pysbd
import re
import uuid

from app.db.database import get_db
from app.schemas.story import (
    StoryGenRequest, 
    StoryResponse, 
    StoryHistoryResponse,
    StoryPreferencesCreate,
    StoryPreferences
)
from app.core.story_generator import StoryGenerator
from app.db import crud
from app.llm.factory import LLMFactory
from app.tts.factory import TTSFactory
from app.config import AUDIO_DIR, NETWORK_SHARE_PATH # Import config values

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Create a singleton instance of StoryGenerator
story_generator = StoryGenerator()

# Initialize once (outside the request handler)
segmenter = pysbd.Segmenter(language="en", clean=False)

@router.post("/generate", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def generate_story(story_request: StoryGenRequest, db: Session = Depends(get_db)):
    """
    Generate a new story based on the provided parameters
    """
    try:
        logger.info(f"Story generation request received: {story_request.dict()}")
        
        # Set environment variables if needed for provider selection
        if story_request.llm_provider:
            os.environ["LLM_PROVIDER"] = story_request.llm_provider
            
        if story_request.tts_provider:
            os.environ["TTS_PROVIDER"] = story_request.tts_provider
            
        # Set voice ID if provided
        if story_request.voice_id:
            os.environ["TTS_VOICE_ID"] = story_request.voice_id
            
        # If using Azure OpenAI, check if we need to set deployment name
        if story_request.llm_provider and story_request.llm_provider.lower() in ["azure", "azure_openai"] and story_request.deployment_name:
            os.environ["AZURE_OPENAI_DEPLOYMENT"] = story_request.deployment_name
            
        # If using local OpenAI API, set the URL from the request or preferences
        if story_request.llm_provider == "local":
            # First try to use the URL from the request if provided
            if hasattr(story_request, "local_api_url") and story_request.local_api_url:
                os.environ["LOCAL_OPENAI_API_URL"] = story_request.local_api_url
                logger.info(f"Using Local OpenAI API URL from request: {story_request.local_api_url}")
                
                # Set the model for the local provider if specified in the request
                if story_request.model:
                    os.environ["LOCAL_MODEL"] = story_request.model
                    logger.info(f"Using specified local model: {story_request.model}")
        
        # Get user preferences
        preferences = crud.get_preferences(db)
        pref_dict = None
        
        # If preferences don't exist yet, create them from this request
        if not preferences:
            try:
                # Extract basic preferences from the request
                new_prefs = {
                    "child_name": story_request.child_name or "Wesley",
                    "llm_provider": story_request.llm_provider,
                    "voice_id": story_request.voice_id,
                    "tts_provider": story_request.tts_provider
                }
                
                # If not randomized, also save universe, setting, theme, and story length
                if not story_request.randomize:
                    new_prefs["favorite_universe"] = story_request.universe
                    new_prefs["favorite_setting"] = story_request.setting
                    new_prefs["favorite_theme"] = story_request.theme
                    new_prefs["preferred_story_length"] = story_request.story_length
                    
                    # Save a favorite character (pick the first one that's not the child)
                    if story_request.characters and len(story_request.characters) > 0:
                        for char in story_request.characters:
                            if char.character_name != story_request.child_name:
                                new_prefs["favorite_character"] = char.character_name
                                break
                
                # Save the new preferences
                logger.info(f"Creating initial preferences from story request: {new_prefs}")
                preferences = crud.save_preferences(db, new_prefs)
                
                # Set the preferences for this request
                pref_dict = new_prefs
                
            except Exception as prefs_err:
                logger.warning(f"Failed to create initial preferences: {str(prefs_err)}")
        else:
            pref_dict = {
                "child_name": preferences.child_name,
                "favorite_universe": preferences.favorite_universe,
                "favorite_character": preferences.favorite_character,
                "favorite_setting": preferences.favorite_setting,
                "favorite_theme": preferences.favorite_theme,
                "preferred_story_length": preferences.preferred_story_length
            }
            
            # Add local_api_url to environment if using local provider
            if story_request.llm_provider == "local" and hasattr(preferences, "local_api_url"):
                # Safely get the local_api_url value and convert it to a string
                local_api_url = getattr(preferences, "local_api_url", None)
                if local_api_url is not None and str(local_api_url).strip():
                    os.environ["LOCAL_OPENAI_API_URL"] = str(local_api_url)
                    logger.info(f"Using custom Local OpenAI API URL from preferences: {local_api_url}")
                    
                    # Set the model for the local provider if specified in the request
                    if story_request.model:
                        os.environ["LOCAL_MODEL"] = story_request.model
                        logger.info(f"Using specified local model: {story_request.model}")
                    elif hasattr(preferences, "llm_model"):
                        # Safely get the llm_model value
                        llm_model = getattr(preferences, "llm_model", None)
                        if llm_model is not None and str(llm_model).strip():
                            os.environ["LOCAL_MODEL"] = str(llm_model)
                            logger.info(f"Using model from preferences for local API: {llm_model}")
        
        # Extract characters from the request and convert to the format expected by StoryGenerator
        characters = []
        if story_request.characters:
            # Convert StoryCharacterInput objects to simple character names
            characters = [char.character_name for char in story_request.characters]
        
        # Try to generate story with preferred provider, with fallback to OpenAI if needed
        try:
            logger.info(f"Generating story with {os.environ.get('LLM_PROVIDER', 'default provider')}")
            
            # Call the generator with extracted parameters
            story = story_generator.generate_story(
                universe=story_request.universe,
                setting=story_request.setting,
                theme=story_request.theme,
                characters=characters,
                story_length=story_request.story_length,
                child_name=story_request.child_name,
                preferences=pref_dict
            )
            
            # Generate audio if story created successfully
            if story and story.get("id"):
                try:
                    audio_path = story_generator.generate_audio(story["id"])
                    story["audio_path"] = audio_path
                except Exception as audio_err:
                    logger.error(f"Audio generation error: {str(audio_err)}")
                    # Continue without audio
            
            return story
            
        except Exception as provider_err:
            # Log error and attempt fallback to OpenAI if not already using it
            logger.warning(f"Provider error: {str(provider_err)}. Attempting fallback to OpenAI.")
            
            if os.environ.get("LLM_PROVIDER", "").lower() != "openai":
                os.environ["LLM_PROVIDER"] = "openai"
                
                # Try again with OpenAI
                story = story_generator.generate_story(
                    universe=story_request.universe,
                    setting=story_request.setting,
                    theme=story_request.theme,
                    characters=characters,
                    story_length=story_request.story_length,
                    child_name=story_request.child_name,
                    preferences=pref_dict
                )
                
                # Generate audio if requested
                if story and story.get("id"):
                    try:
                        audio_path = story_generator.generate_audio(story["id"])
                        story["audio_path"] = audio_path
                    except Exception as audio_err:
                        logger.error(f"Audio generation error: {str(audio_err)}")
                        # Continue without audio
                
                return story
            else:
                # If already using OpenAI, re-raise the exception
                raise
            
    except Exception as e:
        error_msg = f"Failed to generate story: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.get("/history", response_model=Dict[str, Any])
async def get_story_history(page: int = 1, items_per_page: int = 10, db: Session = Depends(get_db)):
    """
    Get the history of generated stories with pagination
    
    Args:
        page: Page number (starting from 1)
        items_per_page: Number of items per page
        db: Database session
    """
    try:
        # Get the total number of stories
        total_stories = crud.get_story_count(db)
        
        # Calculate total pages
        total_pages = (total_stories + items_per_page - 1) // items_per_page
        
        # Ensure page is within valid range
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Use the CRUD function with pagination
        stories = crud.get_recent_stories(db, page, items_per_page)
        
        # Format the response to match the expected schema
        formatted_stories = []
        for story in stories:
            # Get the title from the database or use a default
            title = getattr(story, "title", None) or "Bedtime Story"
            
            formatted_story = {
                "id": story.id,
                "title": title,
                "universe": story.universe,
                "setting": story.setting,
                "theme": story.theme,
                "story_length": story.story_length,
                "characters": [
                    {"character_name": char.character_name, "id": char.id, "story_id": char.story_id}
                    for char in story.characters
                ],
                "prompt": story.prompt,
                "story_text": story.story_text,
                "audio_path": story.audio_path,
                "created_at": story.created_at
            }
            formatted_stories.append(formatted_story)
        
        # Return the stories along with pagination info
        return {
            "stories": formatted_stories,
            "pagination": {
                "total_stories": total_stories,
                "total_pages": total_pages,
                "current_page": page,
                "items_per_page": items_per_page,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving story history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve story history: {str(e)}"
        )

@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_stories(page: int = 1, items_per_page: int = 10, db: Session = Depends(get_db)):
    """
    Get recent stories with pagination (alias for history endpoint)
    """
    return await get_story_history(page, items_per_page, db)

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str):
    """
    Get a specific story by ID
    """
    try:
        # Convert string ID to integer
        try:
            numeric_id = int(story_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid story ID format: {story_id}. Must be an integer."
            )
            
        # We now use the DB session inside the StoryGenerator
        story = crud.get_story_by_id(story_generator.db, numeric_id)
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found"
            )
        
        # Format the response to match the expected schema
        # Get the title from the database or use a default
        title = getattr(story, "title", None) or "Bedtime Story"
        formatted_story = {
            "id": story.id,
            "title": title,
            "universe": story.universe,
            "setting": story.setting,
            "theme": story.theme,
            "story_length": story.story_length,
            "characters": [
                {"character_name": char.character_name, "id": char.id, "story_id": char.story_id}
                for char in story.characters
            ],
            "prompt": story.prompt,
            "story_text": story.story_text,
            "audio_path": story.audio_path,
            "created_at": story.created_at
        }
        
        return formatted_story
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving story: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve story: {str(e)}"
        )

@router.post("/preferences", response_model=StoryPreferences)
async def save_preferences(preferences: StoryPreferencesCreate, db: Session = Depends(get_db)):
    """
    Save user preferences for story generation
    """
    try:
        # Convert to dict with empty strings converted to None
        prefs_dict = preferences.dict()
        for key, value in prefs_dict.items():
            if value == "":
                prefs_dict[key] = None
                
        # Save the preferences
        db_preferences = crud.save_preferences(db, prefs_dict)
        return db_preferences
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error saving preferences: {error_msg}", exc_info=True)
        
        # Check for common SQLite errors related to missing columns
        if "no such column" in error_msg.lower():
            error_msg = "Database schema needs to be updated. Please run the migration script."
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preferences: {error_msg}"
        )

@router.get("/preferences", response_model=StoryPreferences)
async def get_preferences(db: Session = Depends(get_db)):
    """
    Get user preferences for story generation
    """
    try:
        preferences = crud.get_preferences(db)
        
        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preferences found"
            )
        
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error retrieving preferences: {error_msg}", exc_info=True)
        
        # Check for common SQLite errors related to missing columns
        if "no such column" in error_msg.lower():
            error_msg = "Database schema needs to be updated. Please run the migration script."
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {error_msg}"
        )

@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(story_id: str, db: Session = Depends(get_db)):
    """
    Delete a story by ID
    """
    try:
        # Convert string ID to integer
        try:
            numeric_id = int(story_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid story ID format: {story_id}. Must be an integer."
            )
            
        # Get the story to check if it exists
        story = crud.get_story_by_id(db, numeric_id)
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found"
            )
        
        # Delete the story
        crud.delete_story(db, numeric_id)
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting story: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete story: {str(e)}"
        )

@router.get("/config/settings")
async def get_story_settings():
    """
    Get story settings from config
    """
    try:
        from app.config import STORY_SETTINGS
        return STORY_SETTINGS
    except Exception as e:
        logger.error(f"Error retrieving story settings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve story settings: {str(e)}"
        )

@router.get("/models/local", response_model=List[str])
async def get_local_models(api_url: Optional[str] = None):
    """Get available models from local API."""
    try:
        # Determine the API base URL
        api_base = api_url or os.getenv("LOCAL_OPENAI_API_URL", "http://localhost:8080/v1")
        
        logger.info(f"Attempting to connect to local API at: {api_base}")
        
        # Validate API URL format
        if not api_base.startswith(("http://", "https://")):
            api_base = f"http://{api_base}"
        
        if not api_base.endswith("/v1"):
            api_base = f"{api_base.rstrip('/')}/v1"
            
        logger.info(f"Using normalized API URL: {api_base}")
        
        # Extract host and port for logging
        from urllib.parse import urlparse
        parsed_url = urlparse(api_base)
        host = parsed_url.hostname
        port = parsed_url.port
        logger.info(f"Connecting to host: {host}, port: {port}")
        
        # Create a client with a short timeout for faster response
        client = httpx.Client(timeout=10.0)
        
        # Add detailed logging for the request
        logger.info(f"Making request to: {api_base}/models")
        
        # Make the API call
        response = client.get(f"{api_base}/models")
        
        # Log response status
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            models_data = response.json()
            # Extract model IDs from the response
            models = [model["id"] for model in models_data.get("data", [])]
            logger.info(f"Successfully retrieved {len(models)} models from local API")
            return models
        else:
            logger.error(f"Failed to get models with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get models from local API: {response.text}"
            )
    
    except httpx.ConnectError as e:
        logger.error(f"Connection error: {str(e)}")
        # Check if the error is related to port 1234
        error_str = str(e)
        
        if "port=1234" in error_str:
            detail = "Cannot connect to LM Studio on port 1234. Make sure the server is running and try again. The server log shows it's running, so there might be another issue with the connection."
        else:
            detail = f"Cannot connect to local API: {error_str}. Check if the server is running and the URL is correct."
        
        raise HTTPException(status_code=503, detail=detail)

@router.post("/generate_streaming", status_code=status.HTTP_200_OK)
async def generate_story_streaming(story_request: StoryGenRequest, request: Request, db: Session = Depends(get_db)):
    """
    Generate a new story with streaming text and audio based on the provided parameters
    """
    try:
        logger.info(f"Streaming story generation request received: {story_request.dict()}")
        
        # Set environment variables if needed for provider selection
        if story_request.llm_provider:
            os.environ["LLM_PROVIDER"] = story_request.llm_provider
            
        if story_request.tts_provider:
            os.environ["TTS_PROVIDER"] = story_request.tts_provider
            
        # Set voice ID if provided
        if story_request.voice_id:
            os.environ["TTS_VOICE_ID"] = story_request.voice_id
        
        # Extract characters from the request
        characters = []
        if story_request.characters:
            characters = [char.character_name for char in story_request.characters]
        
        # Create a request dictionary with the story elements
        story_elements = {
            "universe": story_request.universe or "",
            "setting": story_request.setting or "",
            "theme": story_request.theme or "",
            "characters": characters or [],
            "story_length": story_request.story_length or "Short (3-5 minutes)",
            "child_name": story_request.child_name or "Wesley",
            "randomize": True if not (story_request.universe and 
                                    story_request.setting and 
                                    story_request.theme and 
                                    characters) else False
        }
        
        # Determine if we want streaming audio
        generate_audio = request.query_params.get("audio", "true").lower() == "true"
        
        # Create LLM and TTS providers
        llm_provider = LLMFactory.get_provider(os.environ.get("LLM_PROVIDER", "openai"))
        tts_provider = None
        if generate_audio:
            tts_provider = TTSFactory.get_provider(os.environ.get("TTS_PROVIDER", "elevenlabs"))
        
        async def generate_streaming_content():
            try:
                # Add a 10-second delay at the very beginning
                # await asyncio.sleep(10) # Removed this server-side delay
                
                # Start with a JSON metadata chunk
                metadata = {
                    "event": "metadata",
                    "data": {
                        "universe": story_elements["universe"],
                        "setting": story_elements["setting"],
                        "theme": story_elements["theme"],
                        "characters": story_elements["characters"],
                        "story_length": story_elements["story_length"],
                        "child_name": story_elements["child_name"],
                    }
                }
                yield f"data: {json.dumps(metadata)}\n\n"
                
                # Buffer for collecting the story text as it's generated
                full_text = ""
                chunk_buffer = ""
                full_audio_data = b"" # Initialize buffer for full audio
                
                # Get the streaming response from the LLM provider and properly await it
                try:
                    async for text_chunk in llm_provider.generate_story_streaming(story_elements): # type: ignore
                        full_text += text_chunk
                        chunk_buffer += text_chunk
                        
                        # Send text chunk to the client
                        text_event = {
                            "event": "text",
                            "data": {"chunk": text_chunk}
                        }
                        yield f"data: {json.dumps(text_event)}\n\n"
                        
                        # If we're generating audio and have enough text, process it
                        if generate_audio and tts_provider and len(chunk_buffer) >= 50:
                            # Look for sentence endings to make natural breaks
                            sentences = segmenter.segment(chunk_buffer)
                            if sentences and len(sentences) > 1:
                                # Process complete sentences except the last one which might be incomplete
                                text_to_process = " ".join(sentences[:-1])
                                chunk_buffer = sentences[-1]  # Keep the potentially incomplete sentence
                                
                                try:
                                    # Process each audio chunk directly
                                    async for audio_chunk in tts_provider.generate_audio_streaming( # type: ignore
                                        text=text_to_process,
                                        voice_id=story_request.voice_id
                                    ):
                                        # Convert binary audio chunk to base64 to send via SSE
                                        b64_audio = base64.b64encode(audio_chunk).decode('utf-8')
                                        
                                        audio_event = {
                                            "event": "audio",
                                            "data": {
                                                "chunk": b64_audio,
                                                "text": text_to_process
                                            }
                                        }
                                        yield f"data: {json.dumps(audio_event)}\n\n"
                                        # Accumulate raw audio data
                                        full_audio_data += audio_chunk
                                except Exception as audio_err:
                                    logger.error(f"Error generating streaming audio: {str(audio_err)}")
                                    # Continue with text generation even if audio fails
                
                    # Process any remaining text for audio
                    if generate_audio and chunk_buffer and tts_provider:
                        try:
                            # Process final chunk
                            async for audio_chunk in tts_provider.generate_audio_streaming( # type: ignore
                                text=chunk_buffer,
                                voice_id=story_request.voice_id
                            ):
                                b64_audio = base64.b64encode(audio_chunk).decode('utf-8')
                                
                                audio_event = {
                                    "event": "audio",
                                    "data": {
                                        "chunk": b64_audio,
                                        "text": chunk_buffer
                                    }
                                }
                                yield f"data: {json.dumps(audio_event)}\n\n"
                                # Accumulate raw audio data
                                full_audio_data += audio_chunk
                        except Exception as audio_err:
                            logger.error(f"Error generating final streaming audio: {str(audio_err)}")
                            # Continue with saving the story even if audio fails
                
                except Exception as text_err:
                    logger.error(f"Error generating streaming text: {str(text_err)}")
                    error_event = {
                        "event": "error",
                        "data": {"message": f"Text generation error: {str(text_err)}"}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    return
                
                # Save the complete story to the database
                try:
                    # Extract title from first line if possible
                    title = "Bedtime Story"
                    story_lines = full_text.strip().split("\n")
                    if story_lines and not story_lines[0].startswith("Once upon a time"):
                        title = story_lines[0].strip()
                        # Remove common title markers
                        for marker in ["Title:", "# ", "## "]:
                            if title.startswith(marker):
                                title = title[len(marker):].strip()
                    
                    # Save audio file if data exists
                    audio_path = None
                    if full_audio_data:
                        try:
                            # Generate filename (using logic similar to TTS providers)
                            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
                            safe_universe = re.sub(r'[^\w\s-]', '', story_elements["universe"]).strip().replace(' ', '_')
                            filename = f"{safe_universe[:20]}_{safe_title[:30]}_{uuid.uuid4().hex[:8]}.mp3"
                            
                            local_file_path = os.path.join(AUDIO_DIR, filename)
                            network_file_path = os.path.join(NETWORK_SHARE_PATH, filename)
                            audio_path = f"audio/{filename}" # Relative path for DB/URL

                            # Save to local directory
                            with open(local_file_path, 'wb') as f:
                                f.write(full_audio_data)
                            logger.info(f"Saved streamed audio to {local_file_path}")

                            # Save to network share if available
                            if NETWORK_SHARE_PATH and os.path.exists(os.path.dirname(NETWORK_SHARE_PATH)):
                                try:
                                    with open(network_file_path, 'wb') as f:
                                        f.write(full_audio_data)
                                    logger.info(f"Copied streamed audio to network share: {network_file_path}")
                                except Exception as share_err:
                                    logger.warning(f"Failed to save streamed audio to network share: {share_err}")
                        except Exception as save_err:
                            logger.error(f"Failed to save accumulated streamed audio: {save_err}")
                            audio_path = None # Ensure path is None if saving failed

                    # Save story to database
                    story_data = {
                        "title": title,
                        "universe": story_elements["universe"],
                        "setting": story_elements["setting"],
                        "theme": story_elements["theme"],
                        "story_length": story_elements["story_length"],
                        "characters": [{"character_name": char} for char in story_elements["characters"]],
                        "prompt": "",  # We don't have the prompt in streaming mode
                        "story_text": full_text,
                        "child_name": story_elements["child_name"],
                        "audio_path": audio_path # Add the saved audio path
                    }
                    
                    db_story = crud.create_story(db, story_data)
                    
                    # Send completion event with story ID
                    complete_event = {
                        "event": "complete",
                        "data": {
                            "story_id": db_story.id,
                            "title": title
                        }
                    }
                    yield f"data: {json.dumps(complete_event)}\n\n"
                    
                except Exception as db_err:
                    logger.error(f"Error saving streamed story to database: {str(db_err)}")
                    error_event = {
                        "event": "error",
                        "data": {"message": f"Failed to save story: {str(db_err)}"}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            except Exception as e:
                logger.error(f"Unexpected error in streaming content generation: {str(e)}", exc_info=True)
                error_event = {
                    "event": "error",
                    "data": {"message": f"Unexpected error: {str(e)}"}
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        # Return a streaming response with event-stream content type
        return StreamingResponse(
            generate_streaming_content(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        error_msg = f"Failed to generate streaming story: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

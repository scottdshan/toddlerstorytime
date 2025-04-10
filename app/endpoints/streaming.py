# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.responses import StreamingResponse
# from sqlalchemy.orm import Session
# from typing import Dict, Any, Optional, AsyncGenerator
# import json
# import logging
# import base64

# from app.db.database import get_db
# from app.schemas.story import StoryElementsRequest
# from app.db.crud import save_story
# from app.llm.base import LLMProvider
# from app.llm.factory import get_llm_provider
# from app.tts.base import TTSProvider
# from app.tts.factory import get_tts_provider

# # Constants
# MIN_CHUNK_SIZE = 100  # Minimum characters before processing audio

# # Set up logger
# logger = logging.getLogger(__name__)

# router = APIRouter()

# @router.post("/story")
# async def generate_streaming_content(
#     story_elements: StoryElementsRequest,
#     db: Session = Depends(get_db),
#     llm_provider: LLMProvider = Depends(get_llm_provider),
#     tts_provider: Optional[TTSProvider] = Depends(get_tts_provider),
# ):
#     """
#     Generate story content and audio in a streaming fashion.
    
#     Args:
#         story_elements: The elements to include in the story
#         db: Database session
#         llm_provider: Language model provider for story generation
#         tts_provider: Text-to-speech provider for audio generation
        
#     Returns:
#         StreamingResponse with story content and audio chunks
#     """
#     # Base settings
#     generate_audio = tts_provider is not None and story_elements.audio
#     full_text = ""
#     chunk_buffer = ""
#     story_id = None
    
#     try:
#         # Main streaming process
#         async for text_chunk in await llm_provider.generate_story_streaming(story_elements.dict()):
#             try:
#                 full_text += text_chunk
#                 chunk_buffer += text_chunk
                
#                 # Create audio for the text chunk if needed
#                 audio_chunk = None
#                 if generate_audio:
#                     try:
#                         if len(chunk_buffer) >= MIN_CHUNK_SIZE:
#                             # Process a complete sentence if possible
#                             sentence_end = max(
#                                 chunk_buffer.rfind("."), 
#                                 chunk_buffer.rfind("!"), 
#                                 chunk_buffer.rfind("?")
#                             )
                            
#                             if sentence_end > 0:
#                                 text_to_process = chunk_buffer[:sentence_end + 1]
#                                 chunk_buffer = chunk_buffer[sentence_end + 1:]
                                
#                                 # Generate audio
#                                 async for audio_data in await tts_provider.generate_audio_streaming(text_to_process):
#                                     audio_chunk = base64.b64encode(audio_data).decode("utf-8")
#                                     yield json.dumps({
#                                         "type": "chunk",
#                                         "text": text_chunk,
#                                         "audio": audio_chunk
#                                     }) + "\n"
#                             else:
#                                 yield json.dumps({
#                                     "type": "chunk",
#                                     "text": text_chunk
#                                 }) + "\n"
#                         else:
#                             yield json.dumps({
#                                 "type": "chunk",
#                                 "text": text_chunk
#                             }) + "\n"
#                     except Exception as e:
#                         logger.error(f"Error generating audio chunk: {str(e)}")
#                         # Continue with text only if audio fails
#                         yield json.dumps({
#                             "type": "chunk",
#                             "text": text_chunk
#                         }) + "\n"
#                 else:
#                     # Text-only mode
#                     yield json.dumps({
#                         "type": "chunk",
#                         "text": text_chunk
#                     }) + "\n"
#             except Exception as e:
#                 logger.error(f"Error processing text chunk: {str(e)}")
#                 yield json.dumps({
#                     "type": "error",
#                     "message": f"Error processing chunk: {str(e)}"
#                 }) + "\n"
        
#         # Process any remaining text for audio
#         if generate_audio and chunk_buffer and tts_provider:
#             try:
#                 # Generate audio for remaining text
#                 async for audio_data in await tts_provider.generate_audio_streaming(chunk_buffer):
#                     audio_chunk = base64.b64encode(audio_data).decode("utf-8")
#                     yield json.dumps({
#                         "type": "chunk",
#                         "text": "",
#                         "audio": audio_chunk
#                     }) + "\n"
#             except Exception as e:
#                 logger.error(f"Error generating final audio: {str(e)}")
        
#         # Save the complete story to the database
#         try:
#             story_id = save_story(
#                 db=db,
#                 title=story_elements.title,
#                 age=story_elements.age,
#                 content=full_text,
#                 elements=story_elements.dict()
#             )
#             yield json.dumps({
#                 "type": "complete",
#                 "storyId": story_id
#             }) + "\n"
#         except Exception as e:
#             logger.error(f"Error saving story to database: {str(e)}")
#             yield json.dumps({
#                 "type": "error",
#                 "message": f"Story generated but could not be saved: {str(e)}"
#             }) + "\n"
            
#     except Exception as e:
#         logger.error(f"Unexpected error in streaming content generation: {str(e)}", exc_info=True)
#         yield json.dumps({
#             "type": "error",
#             "message": f"Error generating content: {str(e)}"
#         }) + "\n" 
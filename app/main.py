import os
import sqlite3
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.endpoints import stories, audio, integrations, preferences, streaming, esp32
from app.db.database import Base, engine
from app.config import TEMPLATES_DIR, STATIC_DIR, AUDIO_DIR, APP_NAME, DEBUG, BASE_DIR, DATABASE_URL, LOCAL_OPENAI_API_URL

# Configure logging
log_file = os.path.join(BASE_DIR, "logs.txt")
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Check if the database needs migration
def check_database_schema():
    try:
        # Only check SQLite databases
        if not DATABASE_URL.startswith("sqlite:///"):
            return

        # Get database path
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL[10:]
            if not db_path.startswith('/'):
                db_path = os.path.join(BASE_DIR, db_path)
        else:
            return
        
        # Check if the database exists
        if not os.path.exists(db_path):
            logger.info("Database doesn't exist yet. It will be created.")
            return
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the story_preferences table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='story_preferences'")
        if not cursor.fetchone():
            logger.info("story_preferences table doesn't exist. No migration check needed.")
            conn.close()
            return
        
        # Check for the new columns
        cursor.execute("PRAGMA table_info(story_preferences)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Define the columns that should be present
        expected_columns = [
            "id", "child_name", "favorite_universe", "favorite_character", 
            "favorite_setting", "favorite_theme", "preferred_story_length", 
            "llm_provider", "llm_model", "tts_provider", "voice_id", 
            "audio_dir", "network_share_path", "network_share_url", "updated_at"
        ]
        
        # Check for missing columns
        missing_columns = [col for col in expected_columns if col not in columns]
        
        if missing_columns:
            logger.warning(f"Database schema is missing columns: {missing_columns}")
            logger.warning("Consider running the migration script (python migrate.py)")
        else:
            logger.info("Database schema is up to date")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error checking database schema: {e}")

# Run schema check
check_database_schema()

# Create the database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title=APP_NAME, debug=DEBUG)

# Add exception handlers for better error messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handling with detailed error information"""
    errors = exc.errors()
    logger.error(f"Validation error: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
##app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
#app.include_router(streaming.router, prefix="/api/streaming", tags=["streaming"])
app.include_router(esp32.router, prefix="/api/esp32", tags=["esp32"])

@app.get("/")
async def index(request: Request):
    """Render the home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/story-builder")
async def story_builder(request: Request):
    """Render the story builder page"""
    return templates.TemplateResponse("story_builder.html", {"request": request})

@app.get("/history")
async def story_history(request: Request):
    """Render the story history page"""
    return templates.TemplateResponse("index.html", {"request": request, "active_page": "history"})

@app.get("/preferences")
async def preferences(request: Request):
    """Render the preferences page"""
    return templates.TemplateResponse("preferences.html", {
        "request": request,
        "local_api_url": LOCAL_OPENAI_API_URL
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/debug")
async def debug_page(request: Request):
    """Debugging page for API testing"""
    logger.info("Debug page accessed")
    return templates.TemplateResponse("debug.html", {"request": request})

@app.get("/audio-debug")
async def audio_debug_page(request: Request):
    """Audio debugging page for testing audio files"""
    logger.info("Audio debug page accessed")
    return templates.TemplateResponse("audio_debug.html", {"request": request})

@app.get("/esp32")
async def esp32_debug_page(request: Request):
    """ESP32 control and debugging page"""
    logger.info("ESP32 debug page accessed")
    return templates.TemplateResponse("esp32_debug.html", {"request": request})

# Run the application with uvicorn when this file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.endpoints import stories, audio
from app.db.database import Base, engine
from app.config import TEMPLATES_DIR, STATIC_DIR, AUDIO_DIR, APP_NAME, DEBUG, BASE_DIR

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
    return templates.TemplateResponse("index.html", {"request": request, "active_page": "preferences"})

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

# Run the application with uvicorn when this file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

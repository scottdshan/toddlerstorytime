import logging
from app.db.database import Base, engine, SessionLocal
from app.db.models import StoryHistory, StoryCharacter, StoryPreferences

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """
    Initialize the database by creating all tables defined in models.
    """
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Check if we need to create default preferences
    db = SessionLocal()
    try:
        preferences = db.query(StoryPreferences).first()
        if not preferences:
            logger.info("Creating default story preferences...")
            default_preferences = StoryPreferences(
                child_name="Wesley",
                preferred_story_length="medium",
                llm_provider="openai"
            )
            db.add(default_preferences)
            db.commit()
            logger.info("Default preferences created successfully.")
    except Exception as e:
        logger.error(f"Error creating default preferences: {e}")
    finally:
        db.close()
    
    logger.info("Database initialization completed.")

if __name__ == "__main__":
    init_db() 
import os
import sqlite3
import logging
from pathlib import Path

from app.config import DATABASE_URL, BASE_DIR

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_path():
    """Extract the SQLite database path from the DATABASE_URL"""
    if DATABASE_URL.startswith('sqlite:///'):
        relative_path = DATABASE_URL[10:]
        # Handle both relative and absolute paths
        if relative_path.startswith('/'):
            return relative_path
        else:
            return os.path.join(BASE_DIR, relative_path)
    else:
        raise ValueError(f"Unsupported database URL format: {DATABASE_URL}")

def migrate_db():
    """
    Migrate the database schema to add new columns to the story_preferences table
    """
    try:
        db_path = get_db_path()
        logger.info(f"Migrating database at {db_path}")
        
        # Verify the database exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the story_preferences table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='story_preferences'")
        if not cursor.fetchone():
            logger.warning("story_preferences table doesn't exist. No migration needed.")
            conn.close()
            return
        
        # Get current columns in the story_preferences table
        cursor.execute("PRAGMA table_info(story_preferences)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Current columns: {columns}")
        
        # Add new columns if they don't exist
        new_columns = {
            "llm_model": "TEXT",
            "tts_provider": "TEXT DEFAULT 'elevenlabs'",
            "audio_dir": "TEXT",
            "network_share_path": "TEXT",
            "network_share_url": "TEXT"
        }
        
        for column, data_type in new_columns.items():
            if column not in columns:
                logger.info(f"Adding column {column} to story_preferences table")
                try:
                    cursor.execute(f"ALTER TABLE story_preferences ADD COLUMN {column} {data_type}")
                    conn.commit()
                    logger.info(f"Successfully added column {column}")
                except sqlite3.OperationalError as e:
                    logger.error(f"Error adding column {column}: {str(e)}")
            else:
                logger.info(f"Column {column} already exists")
        
        conn.close()
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error migrating database: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_db() 
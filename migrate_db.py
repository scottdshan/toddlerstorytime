import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "storyteller.db"

def migrate_database():
    """Add the local_api_url column to the story_preferences table if it doesn't exist"""
    
    logger.info(f"Checking database at {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file {DB_PATH} not found")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(story_preferences)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "local_api_url" not in column_names:
            logger.info("Adding local_api_url column to story_preferences table")
            cursor.execute("ALTER TABLE story_preferences ADD COLUMN local_api_url VARCHAR(255)")
            conn.commit()
            logger.info("Successfully added local_api_url column")
        else:
            logger.info("Column local_api_url already exists")
        
        # Close the connection
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error migrating database: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        logger.info("Database migration completed successfully")
    else:
        logger.error("Database migration failed") 
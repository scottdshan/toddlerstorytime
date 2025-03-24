#!/usr/bin/env python
"""
Database migration script for Toddler Storyteller
"""
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Apply database migrations"""
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('storyteller.db')
        cursor = conn.cursor()
        
        # Check if duration columns exist in story_history table
        cursor.execute("PRAGMA table_info(story_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Add llm_duration column if it doesn't exist
        if 'llm_duration' not in column_names:
            logger.info("Adding llm_duration column to story_history table")
            cursor.execute("ALTER TABLE story_history ADD COLUMN llm_duration REAL")
        
        # Add tts_duration column if it doesn't exist
        if 'tts_duration' not in column_names:
            logger.info("Adding tts_duration column to story_history table")
            cursor.execute("ALTER TABLE story_history ADD COLUMN tts_duration REAL")
        
        # Commit changes
        conn.commit()
        logger.info("Database migration completed successfully")
    except Exception as e:
        logger.error(f"Error in database migration: {str(e)}")
    finally:
        # Close connection
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database() 
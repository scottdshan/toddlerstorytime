#!/usr/bin/env python
"""
Database migration script for Toddler Storyteller
"""
import logging
from app.db.migrate_db import migrate_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting database migration...")
    migrate_db()
    logger.info("Migration finished.") 
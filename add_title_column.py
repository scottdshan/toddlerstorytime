import sqlite3
import os

try:
    # Connect to the database
    conn = sqlite3.connect('storyteller.db')
    
    # Execute ALTER TABLE command
    conn.execute('ALTER TABLE story_history ADD COLUMN title TEXT;')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print('Title column added successfully!')
except Exception as e:
    print(f"Error adding title column: {str(e)}") 
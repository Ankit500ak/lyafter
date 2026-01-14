"""
Database models and schema initialization for the Lyftr AI webhook API.
"""
import sqlite3
from pathlib import Path
from typing import Optional
from app.config import config


def init_db() -> None:
    """Initialize the database schema."""
    db_path = config.get_db_path()
    
    # Create parent directory if it doesn't exist
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create messages table with PRIMARY KEY on message_id for uniqueness
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            from_msisdn TEXT NOT NULL,
            to_msisdn TEXT NOT NULL,
            ts TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create index on ts for ordering and filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_ts
        ON messages(ts ASC, message_id ASC)
    """)
    
    # Create index on from_msisdn for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_from
        ON messages(from_msisdn)
    """)
    
    conn.commit()
    conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection."""
    db_path = config.get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def check_db_health() -> bool:
    """Check if database is healthy and schema is applied."""
    try:
        db_path = config.get_db_path()
        
        # Check if database file exists and is accessible
        if not Path(db_path).exists():
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if messages table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='messages'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception:
        return False

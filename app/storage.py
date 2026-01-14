"""
Storage layer for database operations.
Handles message insertion, retrieval, and aggregation.
"""
from datetime import datetime
from typing import Any, Optional
from app.models import get_db_connection


class MessageStorage:
    """Database operations for messages."""
    
    @staticmethod
    def insert_message(
        message_id: str,
        from_msisdn: str,
        to_msisdn: str,
        ts: str,
        text: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Insert a new message into the database.
        Returns: (success, error_message)
        Handles duplicate key gracefully (idempotency).
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            created_at = datetime.utcnow().isoformat() + "Z"
            
            cursor.execute("""
                INSERT INTO messages
                (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, from_msisdn, to_msisdn, ts, text, created_at))
            
            conn.commit()
            conn.close()
            
            return True, None
        except sqlite3.IntegrityError:
            # Duplicate key - this is expected for idempotency
            return False, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def message_exists(message_id: str) -> bool:
        """Check if a message with the given ID already exists."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM messages WHERE message_id = ?",
                (message_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
        except Exception:
            return False
    
    @staticmethod
    def get_messages(
        limit: int = 50,
        offset: int = 0,
        from_msisdn: Optional[str] = None,
        since: Optional[str] = None,
        q: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Retrieve messages with pagination and filters.
        Returns: (messages_list, total_count)
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if from_msisdn:
                where_conditions.append("from_msisdn = ?")
                params.append(from_msisdn)
            
            if since:
                where_conditions.append("ts >= ?")
                params.append(since)
            
            if q:
                where_conditions.append("text LIKE ?")
                params.append(f"%{q}%")
            
            where_clause = " AND ".join(where_conditions)
            if where_clause:
                where_clause = " WHERE " + where_clause
            
            # Count total matching records
            count_query = f"SELECT COUNT(*) as count FROM messages{where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()["count"]
            
            # Fetch paginated results
            query = f"""
                SELECT message_id, from_msisdn, to_msisdn, ts, text
                FROM messages{where_clause}
                ORDER BY ts ASC, message_id ASC
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            messages = [dict(row) for row in rows]
            
            return messages, total
        except Exception as e:
            return [], 0
    
    @staticmethod
    def get_stats() -> dict[str, Any]:
        """Get analytical stats about messages."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Total messages count
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            total_messages = cursor.fetchone()["count"]
            
            # Senders count
            cursor.execute("SELECT COUNT(DISTINCT from_msisdn) as count FROM messages")
            senders_count = cursor.fetchone()["count"]
            
            # Messages per sender (top 10)
            cursor.execute("""
                SELECT from_msisdn, COUNT(*) as count
                FROM messages
                GROUP BY from_msisdn
                ORDER BY count DESC
                LIMIT 10
            """)
            messages_per_sender = [
                {"from": row["from_msisdn"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
            
            # First and last message timestamps
            cursor.execute("""
                SELECT MIN(ts) as first_ts, MAX(ts) as last_ts
                FROM messages
            """)
            row = cursor.fetchone()
            first_message_ts = row["first_ts"]
            last_message_ts = row["last_ts"]
            
            conn.close()
            
            return {
                "total_messages": total_messages,
                "senders_count": senders_count,
                "messages_per_sender": messages_per_sender,
                "first_message_ts": first_message_ts,
                "last_message_ts": last_message_ts,
            }
        except Exception as e:
            return {
                "total_messages": 0,
                "senders_count": 0,
                "messages_per_sender": [],
                "first_message_ts": None,
                "last_message_ts": None,
            }


import sqlite3

# File: db/postgres.py
import json
import logging
from contextlib import contextmanager
from typing import List, Optional
from psycopg2 import pool
from core.config import settings
from db.schemas import (
    ChatMessageRecord,
    MessageRecord,
    CallRecord,
    ContactRecord,
    TimelineRecord,
    MediaRecord,
    NetworkGraphRecord
)

logger = logging.getLogger("PostgresManager")

class PostgresDatabase:
    """
    Manages a threaded connection pool for PostgreSQL evidence storage.
    Handles raw evidence retrieval, persistent chat history, and analysis caching.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgresDatabase, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        """Initializes the thread-safe connection pool using core settings."""
        try:
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD
            )
            logger.info("PostgreSQL connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for safe connection acquisition and release."""
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    def initialize_tables(self):
        """Sets up persistent storage tables for analysis results and chat history."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS nlp_analysis_results (
                case_id TEXT,
                sender TEXT,
                risk_score_sum FLOAT,
                detected_behaviors TEXT[],
                message_count INTEGER,
                last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (case_id, sender)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id SERIAL PRIMARY KEY,
                case_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS graph_cache (
                case_id TEXT PRIMARY KEY,
                graph_data JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for query in queries:
                        cursor.execute(query)
                    conn.commit()
            logger.info("Forensic persistence tables verified.")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")

    def get_image_binary(self, case_id: str, file_name: str) -> Optional[bytes]:
        """Retrieves raw binary image data (BYTEA) for vision analysis or streaming."""
        query = "SELECT file_data FROM media_sharing WHERE case_id = %s AND file_name = %s LIMIT 1;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, file_name))
                    result = cursor.fetchone()
                    return bytes(result[0]) if result and result[0] else None
        except Exception as e:
            logger.error(f"Error retrieving image binary: {e}")
            return None

    def get_messages(self, case_id: str, limit: int = 1000) -> List[MessageRecord]:
        """Retrieves message logs for a specific forensic case."""
        query = "SELECT id, sender, receiver, timestamp, message FROM messages WHERE case_id = %s ORDER BY timestamp ASC LIMIT %s;"
        results = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, limit))
                    for row in cursor.fetchall():
                        results.append(MessageRecord(
                            id=row[0], sender=row[1], receiver=row[2], 
                            timestamp=row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "", 
                            message=row[4]
                        ))
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve messages: {e}")
            return []

    def get_calls(self, case_id: str, limit: int = 1000) -> List[CallRecord]:
        """Retrieves call logs for a specific forensic case."""
        query = "SELECT id, caller, receiver, timestamp, call_duration_seconds, call_type FROM calls WHERE case_id = %s ORDER BY timestamp ASC LIMIT %s;"
        results = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, limit))
                    for row in cursor.fetchall():
                        results.append(CallRecord(
                            id=row[0], caller=row[1], receiver=row[2], 
                            timestamp=row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "", 
                            call_duration_seconds=row[4], call_type=row[5]
                        ))
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve calls: {e}")
            return []

    def get_contacts(self, case_id: str) -> List[ContactRecord]:
        """Retrieves the contact list associated with a case."""
        query = "SELECT id, name, phone FROM contacts WHERE case_id = %s ORDER BY name ASC;"
        results = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    for row in cursor.fetchall():
                        results.append(ContactRecord(id=row[0], name=row[1], phone=row[2]))
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve contacts: {e}")
            return []

    def get_timeline(self, case_id: str, limit: int = 1000) -> List[TimelineRecord]:
        """Retrieves a chronological timeline of events for a case."""
        query = "SELECT id, timestamp, event_type, user_name, details FROM timeline WHERE case_id = %s ORDER BY timestamp ASC LIMIT %s;"
        results = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, limit))
                    for row in cursor.fetchall():
                        results.append(TimelineRecord(
                            id=row[0], 
                            timestamp=row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else "", 
                            event_type=row[2], user_name=row[3], details=row[4]
                        ))
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve timeline: {e}")
            return []

    def get_media_records(self, case_id: str, limit: int = 1000) -> List[MediaRecord]:
        """Retrieves sharing metadata for media files in a case."""
        query = "SELECT id, sender, receiver, timestamp, file_path, file_name, file_type FROM media_sharing WHERE case_id = %s ORDER BY timestamp ASC LIMIT %s;"
        results = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, limit))
                    for row in cursor.fetchall():
                        results.append(MediaRecord(
                            id=row[0], sender=row[1], receiver=row[2], 
                            timestamp=row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "", 
                            file_path=row[4], file_name=row[5], file_type=row[6]
                        ))
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve media records: {e}")
            return []

    def save_network_graph(self, case_id: str, graph_data: dict):
        """Caches the network topology JSON into the database."""
        query = """
        INSERT INTO graph_cache (case_id, graph_data, last_updated)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (case_id) DO UPDATE SET
            graph_data = EXCLUDED.graph_data,
            last_updated = CURRENT_TIMESTAMP;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, json.dumps(graph_data)))
                    conn.commit()
            logger.info(f"Network graph cached for case: {case_id}")
        except Exception as e:
            logger.error(f"Failed to cache network graph: {e}")

    def get_network_graph(self, case_id: str) -> Optional[NetworkGraphRecord]:
        """Retrieves the cached network topology for visualization."""
        query = "SELECT graph_data FROM graph_cache WHERE case_id = %s;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    result = cursor.fetchone()
                    return NetworkGraphRecord(**result[0]) if result and result[0] else None
        except Exception as e:
            logger.error(f"Failed to retrieve graph cache: {e}")
            return None

    def save_chat_message(self, case_id: str, role: str, content: str):
        """Persists an AI or Human message to the case history."""
        query = "INSERT INTO ai_chat_history (case_id, role, content) VALUES (%s, %s, %s);"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, role, content))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to save chat message: {e}")

    def get_chat_history(self, case_id: str) -> List[ChatMessageRecord]:
        """Retrieves the full conversational history for a case."""
        query = "SELECT role, content, timestamp FROM ai_chat_history WHERE case_id = %s ORDER BY timestamp ASC;"
        history = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    for row in cursor.fetchall():
                        history.append(ChatMessageRecord(
                            role=row[0], content=row[1], 
                            timestamp=row[2].strftime("%Y-%m-%d %H:%M:%S")
                        ))
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []

    def clear_chat_history(self, case_id: str):
        """Wipes the conversation history for a specific case context."""
        query = "DELETE FROM ai_chat_history WHERE case_id = %s;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    conn.commit()
            logger.info(f"Chat history cleared for case: {case_id}")
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")

    def close_all(self):
        """Safely terminates all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL pool closed.")

db_manager = PostgresDatabase()
def get_db(): return db_manager
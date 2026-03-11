import os
import logging
from contextlib import contextmanager
from typing import List, Dict, Any
from psycopg2 import pool
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PostgresManager")

load_dotenv()

# --- Pydantic Schemas for Data Integrity ---
class ChatMessageRecord(BaseModel):
    role: str = Field(..., description="The role of the sender: 'human' or 'ai'")
    content: str = Field(..., description="The content of the message")
    timestamp: str = Field(..., description="When the message was sent")

class PostgresDatabase:
    """
    Manages a threaded connection pool for PostgreSQL.
    Now supports Persistent AI Chat History and Forensic Analysis caching.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgresDatabase, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        """Sets up the threaded connection pool using environment variables."""
        try:
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "forensics"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "")
            )
            logger.info("PostgreSQL connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager to safely acquire and release connections."""
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    def initialize_tables(self):
        """
        Creates the persistent storage tables for AI Analysis and Chat History.
        """
        analysis_query = """
        CREATE TABLE IF NOT EXISTS nlp_analysis_results (
            case_id TEXT,
            sender TEXT,
            risk_score_sum FLOAT,
            detected_behaviors TEXT[],
            message_count INTEGER,
            last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (case_id, sender)
        );
        """
        
        # NEW: Table to permanently store user and AI conversations
        chat_query = """
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id SERIAL PRIMARY KEY,
            case_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(analysis_query)
                    cursor.execute(chat_query)
                    conn.commit()
            logger.info("Persistent storage tables (Analysis & Chat) verified/initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")

    # --- Chat History Management Methods ---

    def save_chat_message(self, case_id: str, role: str, content: str):
        """Saves a single message (human or AI) to the database."""
        query = "INSERT INTO ai_chat_history (case_id, role, content) VALUES (%s, %s, %s);"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id, role, content))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to save chat message to DB: {e}")

    def get_chat_history(self, case_id: str) -> List[ChatMessageRecord]:
        """Retrieves the full conversation history for a case, strictly typed via Pydantic."""
        query = "SELECT role, content, timestamp FROM ai_chat_history WHERE case_id = %s ORDER BY timestamp ASC;"
        history = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
                    for row in rows:
                        # Validate and serialize using Pydantic
                        record = ChatMessageRecord(
                            role=row[0], 
                            content=row[1], 
                            timestamp=row[2].strftime("%Y-%m-%d %H:%M:%S")
                        )
                        history.append(record)
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve chat history from DB: {e}")
            return []

    def clear_chat_history(self, case_id: str):
        """Deletes the conversation history for a specific case."""
        query = "DELETE FROM ai_chat_history WHERE case_id = %s;"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (case_id,))
                    conn.commit()
            logger.info(f"Database chat history cleared for case: {case_id}")
        except Exception as e:
            logger.error(f"Failed to clear chat history from DB: {e}")

    def close_all(self):
        """Closes all connections in the pool during system shutdown."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed.")

# Instantiate a global database manager
db_manager = PostgresDatabase()

def get_db():
    """Access point for the global database manager."""
    return db_manager

def get_postgres_connection():
    """Backward compatibility helper for legacy ingestion scripts."""
    return db_manager.connection_pool.getconn()
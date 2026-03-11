import os
import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Configure professional logging
logger = logging.getLogger("Neo4jManager")

# Load environment variables from .env
load_dotenv()

class Neo4jConnection:
    """
    A Singleton class to handle the Neo4j database connection pool.
    The Neo4j driver internally manages a thread-safe connection pool, 
    so keeping one global instance alive ensures maximum performance.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
            cls._instance._initialize_driver()
        return cls._instance

    def _initialize_driver(self) -> None:
        """Initializes the Neo4j driver and verifies database connectivity."""
        # Updated fallback to 127.0.0.1 matching your environment config 
        # to prevent Windows localhost/IPv6 resolution timeouts
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        try:
            self.driver: Optional[Driver] = GraphDatabase.driver(uri, auth=(user, password))
            # verify_connectivity fails instantly if the DB is down or credentials are wrong
            self.driver.verify_connectivity() 
            # Note: We keep startup logs minimal here as main.py handles the orchestration logging
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {e}")
            self.driver = None

    def close(self) -> None:
        """Safely closes the connection pool during system shutdown."""
        if self.driver is not None:
            self.driver.close()
            logger.info("Neo4j connection pool closed.")

    def get_driver(self) -> Optional[Driver]:
        """Provides access to the active Neo4j driver instance."""
        return self.driver

# Instantiate a single global instance to be imported across the app
neo4j_conn = Neo4jConnection()
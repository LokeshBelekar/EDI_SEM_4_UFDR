# File: db/neo4j.py
import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from core.config import settings

logger = logging.getLogger("Neo4jManager")

class Neo4jConnection:
    """
    Singleton class managing the Neo4j driver.
    Ensures a single thread-safe connection pool is used across the application.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
            cls._instance._initialize_driver()
        return cls._instance

    def _initialize_driver(self) -> None:
        """Initializes the driver and verifies connectivity to the Graph DB."""
        uri = settings.NEO4J_URI
        user = settings.NEO4J_USERNAME
        pwd = settings.NEO4J_PASSWORD
        
        try:
            # We use a longer connection timeout for initial startup
            self.driver: Optional[Driver] = GraphDatabase.driver(
                uri, 
                auth=(user, pwd),
                connection_timeout=5.0
            )
            self.driver.verify_connectivity() 
            logger.info("Connection to Neo4j Graph Database established.")
        except Exception as e:
            logger.error(f"Neo4j Connection Failed: {e}")
            logger.info("Check if Neo4j is 'Started' and listening on the configured port.")
            self.driver = None

    def close(self) -> None:
        """Closes the driver session on application shutdown."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection pool closed.")

    def get_driver(self) -> Optional[Driver]:
        """Returns the active driver or None if connection failed."""
        return self.driver

# Global instance
neo4j_conn = Neo4jConnection()
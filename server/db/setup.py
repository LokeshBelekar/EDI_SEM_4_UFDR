# File: db/setup.py
import logging
from db.postgres import db_manager
from db.neo4j import neo4j_conn

# Standardized professional logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DatabaseSetup")

def init_postgres_schema():
    """
    Initializes the PostgreSQL database schema for forensic evidence storage.
    Creates necessary tables with case isolation logic and data integrity constraints.
    """
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("Dropping legacy PostgreSQL evidence tables...")
                cursor.execute("""
                    DROP TABLE IF EXISTS messages CASCADE;
                    DROP TABLE IF EXISTS calls CASCADE;
                    DROP TABLE IF EXISTS contacts CASCADE;
                    DROP TABLE IF EXISTS media_sharing CASCADE;
                    DROP TABLE IF EXISTS timeline CASCADE;
                """)
                
                logger.info("Applying core PostgreSQL schema definitions...")
                cursor.execute("""
                    CREATE TABLE messages (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        sender VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        message TEXT
                    );

                    CREATE TABLE calls (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        caller VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        call_duration_seconds INTEGER,
                        call_type VARCHAR(50)
                    );

                    CREATE TABLE contacts (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        name VARCHAR(255),
                        phone VARCHAR(50)
                    );

                    CREATE TABLE media_sharing (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        sender VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        file_path VARCHAR(500),
                        file_name VARCHAR(255),
                        file_type VARCHAR(50),
                        file_data BYTEA
                    );

                    CREATE TABLE timeline (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        timestamp TIMESTAMP,
                        event_type VARCHAR(100),
                        user_name VARCHAR(255),
                        details TEXT
                    );
                """)
                conn.commit()
        
        logger.info("PostgreSQL evidence schema initialized successfully.")
        
        # Initialize internal analysis result tables and chat history
        db_manager.initialize_tables()
        
    except Exception as e:
        logger.error(f"Error during PostgreSQL schema initialization: {e}")

def init_neo4j_schema():
    """
    Configures Neo4j graph database schema, constraints, and wipes legacy nodes.
    """
    driver = neo4j_conn.get_driver()
    if not driver:
        logger.error("Neo4j driver unavailable. Skipping graph schema initialization.")
        return
        
    try:
        with driver.session() as session:
            logger.info("Clearing legacy Neo4j graph data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            logger.info("Configuring Neo4j unique identity constraints...")
            # Clean up deprecated constraints if they exist
            session.run("DROP CONSTRAINT person_name IF EXISTS")
            
            # Apply standard UID constraint for forensic entity resolution
            session.run("""
                CREATE CONSTRAINT person_uid IF NOT EXISTS 
                FOR (p:Person) REQUIRE p.uid IS UNIQUE
            """)
        logger.info("Neo4j schema constraints initialized successfully.")
    except Exception as e:
        logger.error(f"Error during Neo4j schema initialization: {e}")

if __name__ == "__main__":
    logger.info("Starting Enterprise Database Setup sequence...")
    init_postgres_schema()
    init_neo4j_schema()
    logger.info("Database setup sequence complete.")
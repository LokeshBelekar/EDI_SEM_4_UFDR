import logging
from database.postgres_db import get_db
from database.neo4j_db import neo4j_conn

# Configure professional logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SchemaInit")

def init_postgres_schema():
    """
    Builds the Postgres schema with case_id isolation.
    Safely utilizes the threaded connection pool to prevent leaks.
    """
    db = get_db()
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("Dropping old PostgreSQL tables...")
                cursor.execute("""
                    DROP TABLE IF EXISTS messages CASCADE;
                    DROP TABLE IF EXISTS calls CASCADE;
                    DROP TABLE IF EXISTS contacts CASCADE;
                    DROP TABLE IF EXISTS media_sharing CASCADE;
                    DROP TABLE IF EXISTS timeline CASCADE;
                """)
                
                logger.info("Creating new PostgreSQL tables with case_id isolation...")
                cursor.execute("""
                    CREATE TABLE messages (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        sender VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        message TEXT
                    );
                """)
                cursor.execute("""
                    CREATE TABLE calls (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        caller VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        call_duration_seconds INTEGER,
                        call_type VARCHAR(50)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE contacts (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        name VARCHAR(255),
                        phone VARCHAR(50)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE media_sharing (
                        id SERIAL PRIMARY KEY,
                        case_id VARCHAR(100),
                        sender VARCHAR(255),
                        receiver VARCHAR(255),
                        timestamp TIMESTAMP,
                        file_path VARCHAR(500),
                        file_type VARCHAR(50)
                    );
                """)
                cursor.execute("""
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
        
        logger.info("✅ PostgreSQL evidence schema initialized successfully.")
        
        # Automatically initialize the AI memory and NLP tables as well
        db.initialize_tables()
        
    except Exception as e:
        logger.error(f"❌ Error initializing Postgres schema: {e}")

def init_neo4j_schema():
    """Wipes old data and sets up the new UID constraint."""
    driver = neo4j_conn.get_driver()
    if not driver:
        logger.warning("⚠️ Neo4j not connected.")
        return
        
    try:
        with driver.session() as session:
            logger.info("Wiping old Neo4j graph data...")
            session.run("MATCH (n) DETACH DELETE n") # Completely clear the graph
            
            # Try to drop the old constraint if it exists
            try:
                session.run("DROP CONSTRAINT person_name IF EXISTS")
            except Exception:
                pass
            
            # Create the new single-property UID constraint
            session.run("""
                CREATE CONSTRAINT person_uid IF NOT EXISTS 
                FOR (p:Person) REQUIRE p.uid IS UNIQUE
            """)
        logger.info("✅ Neo4j constraints initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Error initializing Neo4j schema: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("      Initializing Enterprise Database Schemas    ")
    print("==================================================")
    init_postgres_schema()
    init_neo4j_schema()
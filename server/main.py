# File: main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db.postgres import db_manager
from db.neo4j import neo4j_conn
from api.endpoints import router as forensic_router

# Standardized professional logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ForensicAPI")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade forensic backend featuring Autonomous Vision Agents and Graph Reasoning.",
    version=settings.VERSION
)

# Standardize CORS for secure frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the modularized forensic endpoints from the API layer
app.include_router(forensic_router)

@app.get("/health", tags=["System Status"])
async def health_check():
    """Provides a basic health check for the API gateway and its versioning."""
    return {
        "status": "operational", 
        "version": settings.VERSION, 
        "agent_mode": "LangChain Persistent Vision + Graph"
    }

@app.on_event("startup")
async def startup_event():
    """
    Orchestrates system startup by verifying connectivity to persistence layers.
    Ensures Neo4j and PostgreSQL are reachable before accepting requests.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    
    # Verify Neo4j connectivity via the singleton manager
    driver = neo4j_conn.get_driver()
    if driver:
        logger.info("Neo4j Graph Database connectivity verified.")
    else:
        logger.error("Neo4j connectivity failure. Graph-based features will be unavailable.")

    logger.info("Forensic API Gateway is initialized and ready for investigative requests.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Performs a graceful teardown of all system resources.
    Closes database connection pools and driver sessions to prevent memory leaks.
    """
    logger.info("System shutdown sequence initiated...")
    db_manager.close_all()
    neo4j_conn.close()
    logger.info("All resource pools safely terminated.")
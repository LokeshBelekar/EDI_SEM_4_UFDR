import os
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Database and Infrastructure Imports
from database.postgres_db import db_manager, ChatMessageRecord
from database.neo4j_db import neo4j_conn

# Forensic Analysis Imports
from analysis.poi import poi_orchestrator

# Agentic Engine Imports
from agents.llm_core import llm_engine

# Load environment configuration
load_dotenv()

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ForensicAPI")

app = FastAPI(
    title="UFDR AI Forensic Analyzer",
    description="Enterprise-grade backend featuring Autonomous Tool-Calling Agents and Persistent Memory.",
    version="3.1.0" # Bumped version for Persistent Memory upgrade
)

# Standardize CORS for secure frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Internal Utilities ---

def validate_case_id(case_id: str):
    """
    Verifies that the requested case exists within the evidence repository.
    Acts as a security and integrity guardrail.
    """
    dataset_path = "touse"
    if not os.path.exists(os.path.join(dataset_path, case_id)):
        logger.warning(f"Access attempted for non-existent case identifier: {case_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Case context '{case_id}' not found in the forensic repository."
        )
    return case_id

# --- Data Transfer Objects ---

class ChatRequest(BaseModel):
    query: str
    case_id: str

class ChatResponse(BaseModel):
    case_id: str
    intent_detected: str = "AUTONOMOUS_AGENT"
    entities_extracted: Dict[str, Any] = {}
    forensic_report: str

# --- Lifecycle Management ---

@app.on_event("startup")
async def startup_event():
    """
    Initializes system components and verifies connectivity to persistence layers.
    """
    logger.info("Initializing UFDR Forensic Engine...")
    
    # Verify Neo4j Connectivity
    driver = neo4j_conn.get_driver()
    if driver:
        logger.info("Neo4j Graph Database connectivity verified.")
    else:
        logger.error("Neo4j connectivity failure. Graph analysis features will be disabled.")

    logger.info("API Gateway is now ready for autonomous investigative requests.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Safely terminates database connection pools and driver sessions.
    """
    logger.info("Commencing system shutdown...")
    db_manager.close_all()
    neo4j_conn.close()
    logger.info("All resource pools terminated.")

# --- Investigative Endpoints ---

@app.get("/health")
async def health_check():
    """System health and status reporting."""
    return {"status": "operational", "version": "3.1.0", "agent_mode": "LangChain Persistent"}

@app.get("/api/cases")
async def list_cases():
    """
    Scans the evidence repository and returns a list of active cases.
    """
    dataset_path = "touse"
    if not os.path.exists(dataset_path):
        return {"cases": []}
    
    cases = [d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))]
    return {"cases": sorted(cases)}

@app.get("/api/poi")
async def get_poi_rankings(case_id: str = Query(..., description="The unique identifier for the case")):
    """
    Retrieves the weighted threat matrix for all entities within a specific case.
    """
    valid_case = validate_case_id(case_id)
    
    try:
        rankings = poi_orchestrator.calculate_rankings(valid_case)
        return {
            "case_id": valid_case,
            "entity_count": len(rankings),
            "rankings": rankings
        }
    except Exception as e:
        logger.error(f"Error generating POI rankings for {valid_case}: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis engine failure.")

# --- NEW: Chat History Endpoint ---
@app.get("/api/chat/history/{case_id}", response_model=List[ChatMessageRecord])
async def get_case_chat_history(case_id: str):
    """
    Retrieves the persistent conversation history for a specific case.
    Returns a strictly typed list of Pydantic ChatMessageRecords.
    """
    valid_case = validate_case_id(case_id)
    
    try:
        history = db_manager.get_chat_history(valid_case)
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history for {valid_case}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat history.")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_evidence(request: ChatRequest):
    """
    Autonomous LangChain Agent Endpoint.
    The Agent determines which tools to use based on the user's query and the chat history.
    """
    valid_case = validate_case_id(request.case_id)
    
    logger.info(f"Received query for case {valid_case}: {request.query[:50]}...")

    # Define the strict operating parameters for the Agent
    system_instruction = f"""
    You are an elite Digital Forensic Analyst AI.
    You are currently investigating Case ID: {valid_case}.
    
    You have access to a suite of forensic database tools. 
    You must use these tools to find evidence to answer the investigator's questions.
    
    CRITICAL RULES:
    1. Base your answers ONLY on the data returned by your tools. Do not hallucinate or invent facts.
    2. If the tools return "no data", explicitly state that there is insufficient evidence.
    3. Always pass the exact case_id '{valid_case}' into your tools.
    4. Maintain a clinical, objective, professional tone.
    """

    # Hand off to the LangChain Agent
    final_report = llm_engine.generate_response(
        prompt=request.query, 
        system_instruction=system_instruction, 
        session_id=valid_case
    )

    return ChatResponse(
        case_id=valid_case,
        forensic_report=final_report
    )

@app.delete("/api/chat/{case_id}")
async def clear_case_memory(case_id: str):
    """
    Wipes the conversational memory (chat history) for a specific case.
    """
    valid_case = validate_case_id(case_id)
    llm_engine.clear_history(valid_case)
    return {"status": "success", "message": f"Memory cleared for {valid_case}"}
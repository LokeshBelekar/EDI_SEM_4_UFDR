# File: api/endpoints.py
import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

# Import centralized configuration and schemas
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

# Import persistence and analysis engines
from db.postgres import db_manager
from analysis.poi_engine import poi_orchestrator
from analysis.graph_engine import graph_engine
from agents.orchestrator import llm_orchestrator

logger = logging.getLogger("ForensicAPI")
router = APIRouter(prefix="/api", tags=["Forensic Intelligence"])

# --- Data Transfer Objects (DTOs) ---

class ChatRequest(BaseModel):
    query: str
    case_id: str

class ChatResponse(BaseModel):
    case_id: str
    intent_detected: str = "AUTONOMOUS_AGENT"
    entities_extracted: Dict[str, Any] = {}
    forensic_report: str

# --- Internal Utilities ---

def validate_case_id(case_id: str) -> str:
    """
    Verifies the existence of a case directory within the forensic repository.
    Acts as a security guardrail for multi-case context isolation.
    """
    case_path = os.path.join(settings.DATASET_PATH, case_id)
    if not os.path.exists(case_path) or not os.path.isdir(case_path):
        logger.warning(f"Access attempt for non-existent case: {case_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Case context '{case_id}' not found in the forensic repository."
        )
    return case_id

# --- System & Metadata Endpoints ---

@router.get("/cases", summary="List Active Cases")
async def list_cases():
    """Scans the repository and returns identifiers for all ingested forensic cases."""
    if not os.path.exists(settings.DATASET_PATH):
        return {"cases": []}
    
    cases = [d for d in os.listdir(settings.DATASET_PATH) if os.path.isdir(os.path.join(settings.DATASET_PATH, d))]
    return {"cases": sorted(cases)}

@router.get("/poi", summary="Retrieve Suspect Rankings")
async def get_poi_rankings(case_id: str = Query(..., description="Unique case identifier")):
    """Retrieves the weighted threat matrix for all entities within a specific case context."""
    valid_case = validate_case_id(case_id)
    try:
        rankings = poi_orchestrator.calculate_rankings(valid_case)
        return {
            "case_id": valid_case,
            "entity_count": len(rankings),
            "rankings": rankings
        }
    except Exception as e:
        logger.error(f"POI analysis failure for case {valid_case}: {e}")
        raise HTTPException(status_code=500, detail="Intelligence analysis engine failure.")

# --- Raw Evidence Retrieval Endpoints ---

@router.get("/evidence/{case_id}/messages", response_model=List[MessageRecord])
async def get_case_messages(case_id: str, limit: int = Query(1000)):
    """Retrieves raw message logs for forensic auditing."""
    return db_manager.get_messages(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/calls", response_model=List[CallRecord])
async def get_case_calls(case_id: str, limit: int = Query(1000)):
    """Retrieves call logs and duration metrics."""
    return db_manager.get_calls(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/contacts", response_model=List[ContactRecord])
async def get_case_contacts(case_id: str):
    """Retrieves the extracted address book/contacts list."""
    return db_manager.get_contacts(validate_case_id(case_id))

@router.get("/evidence/{case_id}/timeline", response_model=List[TimelineRecord])
async def get_case_timeline(case_id: str, limit: int = Query(1000)):
    """Retrieves a chronological event timeline for the case."""
    return db_manager.get_timeline(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/media", response_model=List[MediaRecord])
async def get_case_media(case_id: str, limit: int = Query(1000)):
    """Retrieves media sharing metadata (excluding binary content)."""
    return db_manager.get_media_records(validate_case_id(case_id), limit)

# --- Graph & Visual Intelligence Endpoints ---

@router.get("/evidence/{case_id}/network-graph", response_model=NetworkGraphRecord)
async def get_network_graph(case_id: str):
    """
    Returns the complete network topology for visualization. 
    Utilizes PostgreSQL JSONB caching for sub-100ms response times.
    """
    valid_case = validate_case_id(case_id)
    
    cached_graph = db_manager.get_network_graph(valid_case)
    if cached_graph:
        return cached_graph
        
    logger.info(f"Generating network topology for case: {valid_case}")
    graph_data = graph_engine.get_full_network_data(valid_case)
    db_manager.save_network_graph(valid_case, graph_data)
    
    return graph_data

@router.get("/media/{case_id}/{file_name}", summary="Stream Binary Media")
async def get_media_file(case_id: str, file_name: str):
    """Streams raw binary image data directly from the persistence layer. Uses optimized JPEG delivery."""
    valid_case = validate_case_id(case_id)
    image_binary = db_manager.get_image_binary(valid_case, file_name)
    
    if not image_binary:
        raise HTTPException(status_code=404, detail="Media asset not found.")
    
    # Force JPEG media type to match optimized vision engine output
    return Response(content=image_binary, media_type="image/jpeg")

# --- Autonomous Agent & Memory Endpoints ---

@router.get("/chat/history/{case_id}", response_model=List[ChatMessageRecord])
async def get_case_chat_history(case_id: str):
    """Retrieves the persistent conversation history for a specific investigation."""
    valid_case = validate_case_id(case_id)
    try:
        return db_manager.get_chat_history(valid_case)
    except Exception as e:
        logger.error(f"Memory retrieval failure for {valid_case}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversational history.")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Entry point for the Autonomous Forensic Agent. 
    Orchestrates multi-step tool execution and synthesizes forensic reports.
    """
    valid_case = validate_case_id(request.case_id)
    
    # CRITICAL FIX: Stricter instruction against hallucinating parallel tool calls
    system_instruction = (
        f"You are an elite Digital Forensic Analyst AI investigating Case ID: {valid_case}. "
        "1. Base your responses strictly on tool output. DO NOT guess or hallucinate data.\n"
        "2. If you need to analyze images, you MUST execute `find_shared_media` FIRST. "
        "Wait for the database to return the exact file names. ONLY THEN can you execute `analyze_image_content` "
        "using the exact file names provided. DO NOT guess file names like 'image1.jpg'.\n"
        "3. Use 'get_network_topology_report' for organizational analysis.\n"
        "4. If the user greets you, respond professionally without using tools."
    )

    final_report = llm_orchestrator.generate_response(
        prompt=request.query, 
        system_instruction=system_instruction, 
        session_id=valid_case
    )

    return ChatResponse(
        case_id=valid_case,
        forensic_report=final_report
    )

@router.delete("/chat/{case_id}")
async def clear_agent_memory(case_id: str):
    """Permanently wipes conversational history for a case context."""
    valid_case = validate_case_id(case_id)
    llm_orchestrator.clear_history(valid_case)
    return {"status": "success", "message": f"Memory context cleared for case {valid_case}"}
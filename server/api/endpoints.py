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
# Updated engine names to match our cloud-native refactor
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
    CLOUD-NATIVE FIX: Verifies the existence of a case in the DATABASE.
    Previously checked the local filesystem, which is empty on Render.
    """
    try:
        # We query the messages table for any record with this case_id
        # This is the 'Source of Truth' now that we've ingested data to the cloud
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM messages WHERE case_id = %s LIMIT 1", (case_id,))
                if not cursor.fetchone():
                    logger.warning(f"Database validation failed for case: {case_id}")
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Case ID '{case_id}' has no ingested data in the cloud repository."
                    )
        return case_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating case ID against database: {e}")
        # Fallback to permissive during migration if needed, but safer to raise
        return case_id

# --- System & Metadata Endpoints ---

@router.get("/cases", summary="List Active Cases")
async def list_cases():
    """Retrieves all unique Case IDs stored in the cloud database."""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Query unique case IDs from our relational evidence table
                cursor.execute("SELECT DISTINCT case_id FROM messages ORDER BY case_id ASC")
                rows = cursor.fetchall()
                cases = [row[0] for row in rows]
                return {"cases": cases}
    except Exception as e:
        logger.error(f"Failed to list cases from DB: {e}")
        return {"cases": []}

@router.get("/poi", summary="Retrieve Suspect Rankings")
async def get_poi_rankings(case_id: str = Query(..., description="Unique case identifier")):
    """Retrieves the weighted threat matrix using cloud-native analysis."""
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
    return db_manager.get_messages(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/calls", response_model=List[CallRecord])
async def get_case_calls(case_id: str, limit: int = Query(1000)):
    return db_manager.get_calls(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/contacts", response_model=List[ContactRecord])
async def get_case_contacts(case_id: str):
    return db_manager.get_contacts(validate_case_id(case_id))

@router.get("/evidence/{case_id}/timeline", response_model=List[TimelineRecord])
async def get_case_timeline(case_id: str, limit: int = Query(1000)):
    return db_manager.get_timeline(validate_case_id(case_id), limit)

@router.get("/evidence/{case_id}/media", response_model=List[MediaRecord])
async def get_case_media(case_id: str, limit: int = Query(1000)):
    return db_manager.get_media_records(validate_case_id(case_id), limit)

# --- Graph & Visual Intelligence Endpoints ---

@router.get("/evidence/{case_id}/network-graph", response_model=NetworkGraphRecord)
async def get_network_graph(case_id: str):
    valid_case = validate_case_id(case_id)
    
    # Attempt to retrieve pre-computed graph from Postgres JSONB cache
    cached_graph = db_manager.get_network_graph(valid_case)
    if cached_graph:
        return cached_graph
        
    logger.info(f"Computing cloud-graph topology for case: {valid_case}")
    graph_data = graph_engine.get_full_network_data(valid_case)
    db_manager.save_network_graph(valid_case, graph_data)
    
    return graph_data

@router.get("/media/{case_id}/{file_name}", summary="Stream Binary Media")
async def get_media_file(case_id: str, file_name: str):
    """Streams binary image data directly from the cloud persistence layer."""
    valid_case = validate_case_id(case_id)
    image_binary = db_manager.get_image_binary(valid_case, file_name)
    
    if not image_binary:
        raise HTTPException(status_code=404, detail="Media asset not found in cloud storage.")
    
    return Response(content=image_binary, media_type="image/jpeg")

# --- Autonomous Agent & Memory Endpoints ---

@router.get("/chat/history/{case_id}", response_model=List[ChatMessageRecord])
async def get_case_chat_history(case_id: str):
    valid_case = validate_case_id(case_id)
    return db_manager.get_chat_history(valid_case)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Entry point for the Autonomous Forensic Agent. 
    Now uses Llama-3 + Cloud-based Inference Engines.
    """
    valid_case = validate_case_id(request.case_id)
    
    system_instruction = (
        f"You are an elite Digital Forensic Analyst AI investigating Case ID: {valid_case}. "
        "1. Base your responses strictly on tool output. DO NOT guess or hallucinate data.\n"
        "2. If analyzing images, execute `find_shared_media` FIRST. "
        "Use exact file names returned by the database for `analyze_image_content` calls.\n"
        "3. Use 'get_network_topology_report' for organizational analysis.\n"
        "4. Maintain a clinical, objective, and professional forensic tone."
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
    valid_case = validate_case_id(case_id)
    llm_orchestrator.clear_history(valid_case)
    return {"status": "success", "message": f"Memory context cleared for case {valid_case}"}
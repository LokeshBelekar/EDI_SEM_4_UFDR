# File: agents/tools.py
import logging
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from db.postgres import db_manager
from db.neo4j import neo4j_conn
from analysis.poi_engine import poi_orchestrator
from analysis.graph_engine import graph_engine
from analysis.vision_engine import vision_engine

logger = logging.getLogger("ForensicTools")

# --- Input Schemas for Agentic Reasoning ---
# FIXED: Changed List[str] to str (comma-separated) to prevent LLM schema validation errors (400 Bad Request)

class SQLSearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    keywords: Optional[str] = Field(default="", description="Comma-separated keywords to search for in message content.")
    target_people: Optional[str] = Field(default="", description="Comma-separated specific individuals to filter as senders or receivers.")

class MediaSearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    target_people: Optional[str] = Field(default="", description="Comma-separated specific individuals to check for media sharing interactions.")

class ImageAnalysisInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    file_name: str = Field(..., description="The exact name of the image file to analyze visually.")

class GraphSearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    target_people: str = Field(..., description="Comma-separated specific individuals whose network connections require analysis.")

class BaseCaseInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")

# --- Forensic Tools Implementation ---

@tool("search_message_content", args_schema=SQLSearchInput)
def search_message_content(case_id: str, keywords: str = "", target_people: str = "") -> str:
    """
    Searches the relational database for specific message content, keywords, or 
    communications involving target individuals.
    """
    logger.info(f"Executing message search for case: {case_id}")
    query = "SELECT timestamp, sender, receiver, message FROM messages WHERE case_id = %s"
    params = [case_id]
    
    # Parse comma-separated strings from LLM back into Python lists
    kw_list = [k.strip() for k in keywords.split(",")] if keywords and keywords.strip() else []
    people_list = [p.strip() for p in target_people.split(",")] if target_people and target_people.strip() else []
    
    conditions = []
    if kw_list:
        keyword_conditions = " OR ".join(["message ILIKE %s" for _ in kw_list])
        conditions.append(f"({keyword_conditions})")
        params.extend([f"%{kw}%" for kw in kw_list])
        
    if people_list:
        people_conditions = " OR ".join(["sender ILIKE %s OR receiver ILIKE %s" for _ in people_list])
        conditions.append(f"({people_conditions})")
        for person in people_list:
            params.extend([f"%{person}%", f"%{person}%"])
            
    if conditions:
        query += " AND " + " AND ".join(conditions)
        
    query += " ORDER BY timestamp ASC LIMIT 50"
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return "Search complete: No relevant communications found in the database."
                
                results = "Forensic Database Search Results:\n"
                for row in rows:
                    results += f"[{row[0]}] {row[1]} -> {row[2]}: {row[3]}\n"
                return results
    except Exception as e:
        logger.error(f"SQL Tool error: {e}")
        return f"Database Retrieval Error: {str(e)}"

@tool("find_shared_media", args_schema=MediaSearchInput)
def find_shared_media(case_id: str, target_people: str = "") -> str:
    """
    Identifies media files (images, photos, screenshots) shared between suspects.
    Returns file names for subsequent visual analysis.
    """
    logger.info(f"Identifying media sharing for case: {case_id}")
    query = "SELECT timestamp, sender, receiver, file_name FROM media_sharing WHERE case_id = %s AND file_name IS NOT NULL"
    params = [case_id]
    
    # Parse comma-separated strings from LLM back into Python lists
    people_list = [p.strip() for p in target_people.split(",")] if target_people and target_people.strip() else []
    
    if people_list:
        people_conditions = " OR ".join(["sender ILIKE %s OR receiver ILIKE %s" for _ in people_list])
        query += f" AND ({people_conditions})"
        for person in people_list:
            params.extend([f"%{person}%", f"%{person}%"])
            
    query += " ORDER BY timestamp ASC LIMIT 20"
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return "No shared media records located for the specified criteria."
                
                results = "Media Sharing Logs Identified:\n"
                for row in rows:
                    results += f"[{row[0]}] {row[1]} transmitted to {row[2]} -> File: {row[3]}\n"
                return results
    except Exception as e:
        logger.error(f"Media retrieval tool error: {e}")
        return f"Evidence Retrieval Error: {str(e)}"

@tool("analyze_image_content", args_schema=ImageAnalysisInput)
def analyze_image_content(case_id: str, file_name: str) -> str:
    """
    Performs visual forensic analysis on a specific image or photo to extract 
    OCR text, object details, and situational context.
    """
    logger.info(f"Invoking vision analysis for: {file_name}")
    return vision_engine.analyze_image(case_id, file_name)

@tool("analyze_network_connections", args_schema=GraphSearchInput)
def analyze_network_connections(case_id: str, target_people: str) -> str:
    """
    Analyzes specific suspect interactions within the Neo4j graph to determine 
    connection strength and relationship types.
    """
    # Parse comma-separated strings from LLM back into Python lists
    people_list = [p.strip() for p in target_people.split(",")] if target_people and target_people.strip() else []
    logger.info(f"Querying graph interactions for: {people_list}")
    
    driver = neo4j_conn.get_driver()
    if not driver:
        return "Graph engine unavailable: Database connection failed."
        
    results = []
    try:
        with driver.session() as session:
            for person in people_list:
                query = """
                MATCH (a:Person)-[r:COMMUNICATED_WITH]->(b:Person)
                WHERE a.case_id = $case_id AND a.name =~ $person
                RETURN a.name AS Source, b.name AS Target, r.weight AS Weight
                ORDER BY r.weight DESC LIMIT 10
                """
                res = session.run(query, case_id=case_id, person=f"(?i).*{person}.*")
                for record in res:
                    results.append(f"Subject '{record['Source']}' is connected to '{record['Target']}' (Interaction Strength: {record['Weight']})")
                    
    except Exception as e:
        logger.error(f"Graph query tool error: {e}")
        return "Error: Failed to retrieve subject-specific graph data."
        
    if not results:
        return f"No network connections identified for: {', '.join(people_list)}."
        
    return "Forensic Network Interaction Analysis:\n" + "\n".join(results)

@tool("get_network_topology_report", args_schema=BaseCaseInput)
def get_network_topology_report(case_id: str) -> str:
    """
    Generates a high-level summary of the entire communication network, identifying 
    influential hubs, organizational facilitators, and isolated cells.
    """
    logger.info(f"Generating network topology report for case: {case_id}")
    try:
        data = graph_engine.get_full_network_data(case_id)
        if not data["nodes"]:
            return "Network data unavailable or currently being processed."
        
        # Identify top hubs by PageRank and bridges by Betweenness Centrality
        hubs = sorted(data["nodes"], key=lambda x: x["pagerank"], reverse=True)[:5]
        bridges = sorted(data["nodes"], key=lambda x: x["betweenness"], reverse=True)[:5]
        
        community_count = len(set(n["community"] for n in data["nodes"]))
            
        report = f"--- Forensic Case Topology Summary ---\n"
        report += f"Total Entities: {len(data['nodes'])}\n"
        report += f"Interaction Edges: {len(data['edges'])}\n"
        report += f"Identified Communication Cells: {community_count}\n\n"
        
        report += "Primary Influencers (Hubs):\n"
        for h in hubs:
            report += f"- {h['label']} (Influence Score: {round(h['pagerank'], 4)})\n"
            
        report += "\nStrategic Facilitators (Bridges):\n"
        for b in bridges:
            if b['betweenness'] > 0:
                report += f"- {b['label']} (Brokerage Score: {round(b['betweenness'], 4)})\n"
        
        return report
    except Exception as e:
        logger.error(f"Topology analysis failure: {e}")
        return f"Analysis Error: {str(e)}"

@tool("get_threat_assessment", args_schema=BaseCaseInput)
def get_threat_assessment(case_id: str) -> str:
    """
    Computes a multi-vector threat matrix to rank suspects based on behavioral 
    NLP risk and structural network influence.
    """
    logger.info(f"Executing composite threat assessment for case: {case_id}")
    try:
        rankings = poi_orchestrator.calculate_rankings(case_id)
        if not rankings:
            return "Insufficient evidence to compute a reliable threat matrix."
        
        top_suspects = rankings[:5]
        return f"High-Value Target Assessment (Top Suspects): {top_suspects}"
    except Exception as e:
        logger.error(f"Threat assessment tool failure: {e}")
        return "Error: Composite assessment engine failed."

@tool("detect_network_communities", args_schema=BaseCaseInput)
def detect_network_communities(case_id: str) -> str:
    """
    Identifies specific sub-groups or organizational factions within the network 
    based on high-frequency communication patterns.
    """
    logger.info(f"Executing community detection for case: {case_id}")
    try:
        communities = graph_engine.detect_communities(case_id)
        if not communities:
            return "No distinct communication cells identified in this case."
        
        result = "Identified Organizational Sub-Groups:\n"
        for comm in communities:
            result += f"- {comm['community_id']} (Members: {comm['size']}): {', '.join(comm['members'])}\n"
        return result
    except Exception as e:
        logger.error(f"Community detection tool failure: {e}")
        return "Error: Organizational cell detection engine failed."

# Centralized tool export for Agent Orchestration
forensic_tools = [
    search_message_content, 
    find_shared_media,
    analyze_image_content,
    analyze_network_connections, 
    get_network_topology_report,
    get_threat_assessment, 
    detect_network_communities
]
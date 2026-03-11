import logging
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from database.postgres_db import get_db
from database.neo4j_db import neo4j_conn
from analysis.poi import poi_orchestrator
from analysis.graph import graph_engine

logger = logging.getLogger("ForensicTools")

# --- Schemas for strictly typed LLM inputs ---

class SQLSearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    keywords: Optional[List[str]] = Field(default=[], description="Keywords to search for in messages (e.g., 'wallet', 'transfer').")
    target_people: Optional[List[str]] = Field(default=[], description="Specific individuals to search for as senders or receivers.")

class GraphSearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")
    target_people: List[str] = Field(..., description="The specific individuals whose network connections need to be analyzed.")

class POISearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")

class CommunitySearchInput(BaseModel):
    case_id: str = Field(..., description="The unique identifier for the active forensic case.")


# --- LangChain Tools ---

@tool("search_message_content", args_schema=SQLSearchInput)
def search_message_content(case_id: str, keywords: Optional[List[str]] = None, target_people: Optional[List[str]] = None) -> str:
    """
    Use this tool to search the SQL database for specific message content, communications involving specific people, or keywords.
    Always use this when the user asks "what did they say", "find messages about X", or "did they mention Y".
    """
    logger.info(f"Tool executed: search_message_content for {case_id}")
    query = "SELECT timestamp, sender, receiver, message FROM messages WHERE case_id = %s"
    params = [case_id]
    
    conditions = []
    if keywords:
        keyword_conditions = " OR ".join(["message ILIKE %s" for _ in keywords])
        conditions.append(f"({keyword_conditions})")
        params.extend([f"%{kw}%" for kw in keywords])
        
    if target_people:
        people_conditions = " OR ".join(["sender ILIKE %s OR receiver ILIKE %s" for _ in target_people])
        conditions.append(f"({people_conditions})")
        for person in target_people:
            params.extend([f"%{person}%", f"%{person}%"])
            
    if conditions:
        query += " AND " + " AND ".join(conditions)
        
    query += " ORDER BY timestamp ASC LIMIT 50"
    
    try:
        with get_db().get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                if not rows:
                    return "Database returned no relevant communications."
                
                context = "Database Search Results:\n"
                for row in rows:
                    context += f"[{row[0]}] {row[1]} -> {row[2]}: {row[3]}\n"
                return context
    except Exception as e:
        logger.error(f"SQL Tool failed: {e}")
        return f"Error retrieving database evidence: {e}"


@tool("analyze_network_connections", args_schema=GraphSearchInput)
def analyze_network_connections(case_id: str, target_people: List[str]) -> str:
    """
    Use this tool to analyze the communication network graph in Neo4j.
    Use this when the user asks "who is X connected to", "who did Y talk to", or "what is the relationship between X and Y".
    """
    logger.info(f"Tool executed: analyze_network_connections for {case_id}")
    if not target_people:
        return "You must provide at least one person's name to analyze their network."
        
    driver = neo4j_conn.get_driver()
    if not driver:
        return "Graph database is currently unavailable."
        
    results = []
    try:
        with driver.session() as session:
            for person in target_people:
                query = """
                MATCH (a:Person)-[r:COMMUNICATED_WITH]->(b:Person)
                WHERE a.case_id = $case_id AND a.name =~ $person
                RETURN a.name AS Source, b.name AS Target, r.weight AS Weight
                ORDER BY r.weight DESC LIMIT 10
                """
                # Using regex case-insensitive match for the person
                res = session.run(query, case_id=case_id, person=f"(?i).*{person}.*")
                for record in res:
                    results.append(f"{record['Source']} connected to {record['Target']} (Strength: {record['Weight']})")
                    
    except Exception as e:
        logger.error(f"Graph Tool failed: {e}")
        return "Error retrieving graph relational data."
        
    if not results:
        return f"No network connections found in the graph for {', '.join(target_people)}."
        
    return "Network Graph Analysis:\n" + "\n".join(results)


@tool("get_threat_assessment", args_schema=POISearchInput)
def get_threat_assessment(case_id: str) -> str:
    """
    Use this tool to get a high-level behavioral threat assessment and rank the top suspects in the case.
    Use this when the user asks "who are the main suspects", "give me a case summary", or "who is the most suspicious".
    """
    logger.info(f"Tool executed: get_threat_assessment for {case_id}")
    try:
        rankings = poi_orchestrator.calculate_rankings(case_id)
        if not rankings:
            return "No behavioral threat data could be calculated for this case."
        
        # Return the top 5 suspects as a string for the LLM to read
        top_suspects = rankings[:5]
        return f"Top Suspects Threat Matrix: {top_suspects}"
    except Exception as e:
        logger.error(f"POI Tool failed: {e}")
        return "Error retrieving threat assessment data."


@tool("detect_network_communities", args_schema=CommunitySearchInput)
def detect_network_communities(case_id: str) -> str:
    """
    Use this tool to identify isolated sub-groups, communication cells, or community clusters within the network.
    Always use this when the user asks "who belongs to the same cell", "find communication groups", or "what are the factions".
    """
    logger.info(f"Tool executed: detect_network_communities for {case_id}")
    try:
        communities = graph_engine.detect_communities(case_id)
        if not communities:
            return "No distinct communities or cells could be identified in the network."
        
        # Format for the LLM
        result = "Identified Communication Cells:\n"
        for comm in communities:
            result += f"- {comm['community_id']} (Size: {comm['size']}): {', '.join(comm['members'])}\n"
        return result
    except Exception as e:
        logger.error(f"Community Detection Tool failed: {e}")
        return "Error retrieving network communities."

# Export a list of all available tools to give to the LangChain Agent
forensic_tools = [
    search_message_content, 
    analyze_network_connections, 
    get_threat_assessment, 
    detect_network_communities
]
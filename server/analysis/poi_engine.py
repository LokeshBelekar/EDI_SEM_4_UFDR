# File: analysis/poi_engine.py
import logging
from typing import List, Dict, Any
from analysis.graph_engine import graph_engine
from analysis.nlp_engine import nlp_engine

logger = logging.getLogger("POIOrchestrator")

class POIOrchestrator:
    """
    Orchestrates the fusion of behavioral NLP metrics and structural graph 
    metrics to identify high-value targets within a forensic dataset.
    Fuses contextual intent detection with network centrality metrics to 
    identify key suspects without loading heavy local models.
    """

    # Weighted coefficients for the threat algorithm.
    COEFFICIENTS = {
        "nlp_risk": 40.0,
        "graph_betweenness": 35.0,
        "graph_degree": 15.0,
        "graph_closeness": 10.0
    }

    def __init__(self):
        logger.info("POI Orchestrator initialized with Weighted Threat Matrix (Cloud-Native).")

    def calculate_rankings(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Generates a unified threat ranking for entities in a specific case.
        """
        logger.info(f"Initiating multi-vector threat analysis for case: {case_id}")

        try:
            # Safely retrieve metrics from our new cloud-based engines
            graph_metrics = graph_engine.get_advanced_centrality(case_id) or {}
            behavioral_profiles = nlp_engine.analyze_case_evidence(case_id) or {}
        except Exception as e:
            logger.error(f"Critical failure retrieving base metrics for case {case_id}: {e}")
            return []

        all_entities = set(list(graph_metrics.keys()) + list(behavioral_profiles.keys()))
        
        if not all_entities:
            logger.warning(f"No entities found for threat analysis in case: {case_id}")
            return []
            
        poi_results = []

        for entity in all_entities:
            try:
                g_data = graph_metrics.get(entity, {"degree": 0.0, "betweenness": 0.0, "closeness": 0.0})
                n_data = behavioral_profiles.get(entity, {
                    "risk_score_sum": 0.0, 
                    "detected_behaviors": [], 
                    "total_messages_analyzed": 0
                })

                # Calculate Weighted Threat Score
                threat_score = (
                    (float(n_data.get("risk_score_sum", 0)) * self.COEFFICIENTS["nlp_risk"]) +
                    (float(g_data.get("betweenness", 0)) * 100 * self.COEFFICIENTS["graph_betweenness"]) +
                    (float(g_data.get("degree", 0)) * 100 * self.COEFFICIENTS["graph_degree"]) +
                    (float(g_data.get("closeness", 0)) * 100 * self.COEFFICIENTS["graph_closeness"])
                )

                poi_results.append({
                    "entity_name": entity,
                    "case_id": case_id,
                    "threat_score": round(threat_score, 2),
                    "risk_indicators": {
                        "network_influence": {
                            "brokerage_rank": round(float(g_data.get("betweenness", 0)), 4),
                            "connectivity_rank": round(float(g_data.get("degree", 0)), 4),
                            "spread_efficiency": round(float(g_data.get("closeness", 0)), 4)
                        },
                        "behavioral_analysis": {
                            "detected_intents": n_data.get("detected_behaviors", []),
                            "intent_confidence_sum": round(float(n_data.get("risk_score_sum", 0)), 4),
                            "message_volume": n_data.get("total_messages_analyzed", 0)
                        }
                    }
                })
            except Exception as e:
                logger.error(f"Error calculating threat score for entity '{entity}': {e}")
                continue 

        ranked_results = sorted(poi_results, key=lambda x: x["threat_score"], reverse=True)
        logger.info(f"Threat analysis finalized for {len(ranked_results)} entities.")
        return ranked_results

poi_orchestrator = POIOrchestrator()
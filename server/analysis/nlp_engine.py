import logging
import time
import requests
import os
from db.postgres import db_manager

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    Forensic NLP Engine utilizing Hugging Face Serverless Inference for intent detection.
    Features a persistence layer in PostgreSQL to cache analysis results and 
    accelerate subsequent investigative queries. 
    Memory-optimized for cloud deployment (Render/Railway).
    """
    def __init__(self, model_name="valhalla/distilbart-mnli-12-1"):
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.api_key = os.getenv("HF_API_KEY")
        
        logger.info(f"Initializing Forensic NLP Engine using Cloud Inference: {model_name}")
        
        if not self.api_key:
            logger.error("HF_API_KEY not found in environment variables. NLP analysis will fail.")

    def _query_api(self, payload):
        """Executes a request to Hugging Face with exponential backoff."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Exponential backoff parameters
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                result = response.json()
                
                # Handle model loading state (common in free tier)
                if isinstance(result, dict) and "estimated_time" in result:
                    wait_time = result.get("estimated_time", 10)
                    logger.info(f"HF Model is loading. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 200:
                    return result
                
                logger.warning(f"HF API returned status {response.status_code}: {result}")
            except Exception as e:
                logger.error(f"HF API Connection Error: {e}")
            
            # Wait 1s, 2s, 4s, 8s, 16s
            time.sleep(2 ** i)
            
        return None

    def _get_persistent_results(self, case_id: str):
        """Retrieves cached analysis results from the persistence layer."""
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT sender, risk_score_sum, detected_behaviors, message_count 
                        FROM nlp_analysis_results 
                        WHERE case_id = %s
                    """
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
                    if rows:
                        results = {}
                        for r in rows:
                            results[r[0]] = {
                                "risk_score_sum": r[1],
                                "detected_behaviors": r[2],
                                "total_messages_analyzed": r[3]
                            }
                        return results
        except Exception as e:
            logger.error(f"Error reading persistent NLP results: {e}")
        return None

    def _save_persistent_results(self, case_id: str, risk_profile: dict):
        """Caches analysis metrics to PostgreSQL for future retrieval."""
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    for sender, data in risk_profile.items():
                        query = """
                        INSERT INTO nlp_analysis_results (case_id, sender, risk_score_sum, detected_behaviors, message_count)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (case_id, sender) DO UPDATE SET
                            risk_score_sum = EXCLUDED.risk_score_sum,
                            detected_behaviors = EXCLUDED.detected_behaviors,
                            message_count = EXCLUDED.message_count,
                            last_analyzed = CURRENT_TIMESTAMP;
                        """
                        cursor.execute(query, (
                            case_id, 
                            sender, 
                            data["risk_score_sum"], 
                            data["detected_behaviors"], 
                            data["total_messages_analyzed"]
                        ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error writing persistent NLP results: {e}")

    def analyze_case_evidence(self, case_id: str):
        """
        Orchestrates evidence analysis via HF Cloud API. Checks cache first.
        """
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Loaded NLP analysis from cache for case: {case_id}")
            return cached_data

        risk_profile = {}
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "SELECT sender, message FROM messages WHERE case_id = %s AND message IS NOT NULL"
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Database error during evidence retrieval: {e}")
            return {}

        if not rows:
            return {}

        candidate_labels = [
            "financial coordination", 
            "logistical planning", 
            "suspicious behavior", 
            "evidence destruction"
        ]

        logger.info(f"Commencing cloud batch analysis for {len(rows)} messages in case: {case_id}")

        # Process messages through cloud API
        for sender, message in rows:
            if not message.strip(): continue
            
            if sender not in risk_profile:
                risk_profile[sender] = {
                    "total_messages_analyzed": 0, 
                    "risk_score_sum": 0.0, 
                    "detected_behaviors": set()
                }
            
            risk_profile[sender]["total_messages_analyzed"] += 1
            
            # Query HF Inference API
            payload = {
                "inputs": message,
                "parameters": {"candidate_labels": candidate_labels, "multi_label": True}
            }
            
            analysis = self._query_api(payload)
            if analysis and "labels" in analysis:
                for label, score in zip(analysis['labels'], analysis['scores']):
                    if score > 0.7:
                        risk_profile[sender]["risk_score_sum"] += score
                        risk_profile[sender]["detected_behaviors"].add(label)
            
            # Small sleep to prevent aggressive rate-limiting on free tier
            time.sleep(0.1)

        # Finalize structure for persistence
        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        self._save_persistent_results(case_id, risk_profile)
        return risk_profile

# Singleton engine instance
nlp_engine = NLPEngine()
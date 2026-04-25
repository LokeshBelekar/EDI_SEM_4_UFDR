import logging
import time
import requests
import os
from database.postgres_db import get_db

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    Cloud-Native NLP Engine using Hugging Face Serverless Inference.
    Features persistent PostgreSQL caching and robust JSON/HTML error handling.
    """
    def __init__(self, model_name="facebook/bart-large-mnli"):
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.api_key = os.getenv("HF_API_KEY")
        
        logger.info(f"Initializing Cloud NLP Engine using {model_name}")
        
        if not self.api_key:
            logger.error("HF_API_KEY not found. NLP analysis will fail.")
            
        try:
            # Ensure the cache tables are ready in Postgres
            get_db().initialize_tables()
        except Exception as e:
            logger.error(f"Failed to initialize NLP cache tables: {e}")

    def _query_api(self, payload):
        """Executes a request to Hugging Face with robust HTML/JSON error handling."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                
                # 1. Catch HTML/Server errors BEFORE trying to parse JSON
                if response.status_code != 200:
                    logger.warning(f"HF API returned status {response.status_code}: {response.text[:150]}")
                    
                    # If HF is just "warming up" the model, wait and retry
                    if "estimated_time" in response.text:
                        try:
                            wait_time = response.json().get("estimated_time", 15)
                        except:
                            wait_time = 15
                        logger.info(f"HF Model is waking up. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                        
                    # For other errors (500, 503), trigger exponential backoff
                    time.sleep(2 ** i)
                    continue
                    
                # 2. If 200 OK, it is safe to parse the JSON
                return response.json()
                
            except requests.exceptions.JSONDecodeError:
                logger.error("HF API returned non-JSON data (likely an HTML error page or timeout).")
            except Exception as e:
                logger.error(f"HF API Request Failed: {e}")
            
            # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            time.sleep(2 ** i)
            
        return None

    def _get_persistent_results(self, case_id: str):
        """Retrieves previously computed results from PostgreSQL."""
        db = get_db()
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "SELECT sender, risk_score_sum, detected_behaviors, message_count FROM nlp_analysis_results WHERE case_id = %s"
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
            logger.error(f"Persistent storage read error: {e}")
        return None

    def _save_persistent_results(self, case_id: str, risk_profile: dict):
        """Saves computation results to PostgreSQL for future instant access."""
        db = get_db()
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    for sender, data in risk_profile.items():
                        query = """
                        INSERT INTO nlp_analysis_results (case_id, sender, risk_score_sum, detected_behaviors, message_count)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (case_id, sender) DO UPDATE SET
                            risk_score_sum = EXCLUDED.risk_score_sum,
                            detected_behaviors = EXCLUDED.detected_behaviors,
                            message_count = EXCLUDED.message_count;
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
            logger.error(f"Persistent storage write error: {e}")

    def analyze_case_evidence(self, case_id: str):
        """
        Main entry point. Check DB -> If empty, run AI -> Save to DB.
        """
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Loaded NLP analysis from cache for case: {case_id}")
            return cached_data

        db = get_db()
        risk_profile = {}
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "SELECT sender, message FROM messages WHERE case_id = %s AND message IS NOT NULL"
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Database error during evidence retrieval: {e}")
            return {}

        if not rows: return {}

        candidate_labels = ["financial coordination", "logistical planning", "suspicious behavior", "evidence destruction"]
        logger.info(f"Commencing cloud batch analysis for {len(rows)} messages in case: {case_id}")

        for sender, message in rows:
            if not message.strip(): continue
            
            if sender not in risk_profile:
                risk_profile[sender] = {"total_messages_analyzed": 0, "risk_score_sum": 0.0, "detected_behaviors": set()}
            
            risk_profile[sender]["total_messages_analyzed"] += 1
            
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
            
            # Prevent aggressive rate-limiting on HF free tier
            time.sleep(0.1)

        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        self._save_persistent_results(case_id, risk_profile)
        return risk_profile

nlp_engine = NLPEngine()
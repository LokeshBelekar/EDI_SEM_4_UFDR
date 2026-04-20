# File: analysis/nlp_engine.py
import logging
import torch
from transformers import pipeline
from db.postgres import db_manager

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    Forensic NLP Engine utilizing zero-shot classification for intent detection.
    Features a persistence layer in PostgreSQL to cache analysis results and 
    accelerate subsequent investigative queries.
    """
    def __init__(self, model_name="valhalla/distilbart-mnli-12-1"):
        # Select optimal hardware acceleration
        self.device = 0 if torch.cuda.is_available() or torch.backends.mps.is_available() else -1
        
        logger.info(f"Initializing Forensic NLP Engine with model: {model_name}")
        
        try:
            self.classifier = pipeline(
                "zero-shot-classification", 
                model=model_name, 
                device=self.device
            )
            logger.info("NLP classification pipeline ready.")
        except Exception as e:
            logger.error(f"Failed to initialize NLP classification pipeline: {e}")
            self.classifier = None

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
        Orchestrates evidence analysis. Checks cache first; if unavailable, 
        executes inference on raw message logs and updates the cache.
        """
        # Attempt to load from cache to prevent redundant computation
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Loaded NLP analysis from cache for case: {case_id}")
            return cached_data

        if not self.classifier:
            logger.error("NLP classifier unavailable for inference.")
            return {}

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

        senders, messages = zip(*rows)
        candidate_labels = [
            "financial coordination", 
            "logistical planning", 
            "suspicious behavior", 
            "evidence destruction"
        ]

        logger.info(f"Commencing batch analysis for {len(messages)} messages in case: {case_id}")

        # Batch inference with standard thresholds
        results = self.classifier(list(messages), candidate_labels, multi_label=True, batch_size=8)

        for i, analysis in enumerate(results):
            sender = senders[i]
            if sender not in risk_profile:
                risk_profile[sender] = {
                    "total_messages_analyzed": 0, 
                    "risk_score_sum": 0.0, 
                    "detected_behaviors": set()
                }
            
            risk_profile[sender]["total_messages_analyzed"] += 1
            for label, score in zip(analysis['labels'], analysis['scores']):
                # Filter for high-confidence forensic indicators
                if score > 0.7:
                    risk_profile[sender]["risk_score_sum"] += score
                    risk_profile[sender]["detected_behaviors"].add(label)

        # Convert sets to lists for JSON serialization compatibility
        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        # Update cache with new findings
        self._save_persistent_results(case_id, risk_profile)
        return risk_profile

# Singleton engine instance
nlp_engine = NLPEngine()
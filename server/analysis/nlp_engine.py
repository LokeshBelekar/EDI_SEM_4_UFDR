import logging
import os
import torch
from transformers import pipeline
from dotenv import load_dotenv
from db.postgres import db_manager

# Force Python to load the .env file into the OS environment variables
load_dotenv()

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    True Forensic NLP Engine utilizing zero-shot classification (NLI) for intent detection.
    Configured explicitly for Hugging Face Spaces CPU-only environment.
    Features a persistence layer in PostgreSQL to cache heavy mathematical inference.
    """
    def __init__(self, model_name="valhalla/distilbart-mnli-12-1"):
        # CRITICAL FOR HUGGING FACE SPACES FREE TIER: 
        # Force CPU mode (device = -1). The free tier has 16GB RAM but NO GPU.
        self.device = -1
        
        logger.info(f"Initializing True NLP Classification Pipeline: {model_name} on CPU")
        
        try:
            self.classifier = pipeline(
                "zero-shot-classification", 
                model=model_name, 
                device=self.device
            )
            logger.info("NLP classification pipeline weights loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize NLP classification pipeline: {e}")
            self.classifier = None
            
        try:
            db_manager.initialize_tables()
        except Exception as e:
            logger.error(f"Failed to initialize NLP cache tables: {e}")

    def _get_persistent_results(self, case_id: str):
        """Retrieves cached analysis results from PostgreSQL."""
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "SELECT sender, risk_score_sum, detected_behaviors, message_count FROM nlp_analysis_results WHERE case_id = %s"
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
                    if rows:
                        results = {}
                        for r in rows:
                            results[r[0]] = {
                                "risk_score_sum": float(r[1]),
                                "detected_behaviors": r[2],
                                "total_messages_analyzed": r[3]
                            }
                        return results
        except Exception as e:
            logger.error(f"Error reading persistent NLP results: {e}")
        return None

    def _save_persistent_results(self, case_id: str, risk_profile: dict):
        """Caches mathematical inference results to PostgreSQL."""
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
            logger.error(f"Error writing persistent NLP results: {e}")

    def analyze_case_evidence(self, case_id: str):
        """
        Orchestrates evidence analysis using true Zero-Shot NLI. 
        Checks Postgres cache first to prevent redundant CPU computation.
        """
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Loaded True NLP analysis from cache for case: {case_id}")
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

        logger.info(f"Commencing True Zero-Shot analysis for {len(messages)} messages...")

        # Batch inference through the local Transformers pipeline
        # Batch size of 8 is optimized for CPU processing without freezing
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
                # Filter for high-confidence forensic indicators based on entailment probabilities
                if score > 0.7:
                    risk_profile[sender]["risk_score_sum"] += score
                    risk_profile[sender]["detected_behaviors"].add(label)

        # Convert sets to lists for DB storage
        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        # Update cache with new mathematical findings
        self._save_persistent_results(case_id, risk_profile)
        logger.info("True NLP analysis complete and cached to PostgreSQL.")
        return risk_profile

# Singleton engine instance
nlp_engine = NLPEngine()
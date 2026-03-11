import logging
import torch
import json
from transformers import pipeline
from database.postgres_db import get_db

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    Optimized NLP Engine using DistilBART for 3x speed increase.
    Implements persistent PostgreSQL caching to eliminate redundant processing.
    """
    def __init__(self, model_name="valhalla/distilbart-mnli-12-1"):
        # Auto-detect hardware
        self.device = 0 if torch.cuda.is_available() or torch.backends.mps.is_available() else -1
        
        logger.info(f"Initializing Optimized NLP Engine using {model_name}")
        
        try:
            self.classifier = pipeline(
                "zero-shot-classification", 
                model=model_name, 
                device=self.device
            )
            # Match the new Postgres database method name
            get_db().initialize_tables()
            logger.info("Forensic NLP model loaded and storage initialized.")
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.classifier = None

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
        Main entry point. Check DB -> If empty, run 3x faster AI -> Save to DB.
        """
        # 1. Check persistent storage first
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Instant retrieval from persistent storage for case: {case_id}")
            return cached_data

        # 2. If not found, run the optimized inference
        db = get_db()
        risk_profile = {}
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "SELECT sender, message FROM messages WHERE case_id = %s AND message IS NOT NULL"
                    cursor.execute(query, (case_id,))
                    rows = cursor.fetchall()
        except Exception:
            return {}

        if not rows: return {}
        senders, messages = zip(*rows)
        candidate_labels = ["financial coordination", "logistical planning", "suspicious behavior", "evidence destruction"]

        logger.info(f"First-time processing: Analyzing {len(messages)} messages for case: {case_id}")

        results = self.classifier(list(messages), candidate_labels, multi_label=True, batch_size=8)

        for i, analysis in enumerate(results):
            sender = senders[i]
            if sender not in risk_profile:
                risk_profile[sender] = {"total_messages_analyzed": 0, "risk_score_sum": 0.0, "detected_behaviors": set()}
            
            risk_profile[sender]["total_messages_analyzed"] += 1
            for label, score in zip(analysis['labels'], analysis['scores']):
                if score > 0.7:
                    risk_profile[sender]["risk_score_sum"] += score
                    risk_profile[sender]["detected_behaviors"].add(label)

        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        # 3. Save for the future
        self._save_persistent_results(case_id, risk_profile)
        return risk_profile

nlp_engine = NLPEngine()
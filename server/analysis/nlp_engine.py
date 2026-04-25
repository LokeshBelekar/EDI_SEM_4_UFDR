import logging
import time
import os
import json
import re
from dotenv import load_dotenv
from db.postgres import db_manager
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Force Python to load the .env file into the OS environment variables
load_dotenv()

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    """
    Cloud-Native NLP Engine using Groq's Llama-3 for high-speed intent classification.
    Bypasses Hugging Face completely for 100% reliability and zero local RAM usage.
    """
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = "llama-3.3-70b-versatile"
        
        logger.info("Initializing Forensic NLP Engine using Groq Inference...")
        
        if self.api_key:
            self.chat = ChatGroq(
                temperature=0.0,
                model_name=self.model_name,
                groq_api_key=self.api_key,
                max_retries=3
            )
        else:
            self.chat = None
            logger.error("GROQ_API_KEY not found. NLP analysis will fail.")
            
        try:
            # Ensure the cache tables are ready in Postgres
            db_manager.initialize_tables()
        except Exception as e:
            logger.error(f"Failed to initialize NLP cache tables: {e}")

    def _get_persistent_results(self, case_id: str):
        """Retrieves previously computed results from PostgreSQL."""
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
            logger.error(f"Persistent storage read error: {e}")
        return None

    def _save_persistent_results(self, case_id: str, risk_profile: dict):
        """Saves computation results to PostgreSQL for future instant access."""
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
            logger.error(f"Persistent storage write error: {e}")

    def analyze_case_evidence(self, case_id: str):
        """
        Main entry point. Uses Groq to batch-analyze messages for forensic intents.
        """
        cached_data = self._get_persistent_results(case_id)
        if cached_data:
            logger.info(f"Loaded NLP analysis from cache for case: {case_id}")
            return cached_data

        if not self.chat:
            logger.error("Groq client offline. Cannot perform NLP inference.")
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

        if not rows: return {}

        logger.info(f"Commencing Groq NLP Analysis for {len(rows)} messages...")

        # Group messages by sender to analyze behavior contextually
        sender_messages = {}
        for sender, message in rows:
            if not message.strip(): continue
            if sender not in sender_messages:
                sender_messages[sender] = []
            sender_messages[sender].append(message)

        system_prompt = (
            "You are an expert Forensic NLP classification system. "
            "Analyze the following batch of messages from a single suspect. "
            "Determine the presence of these four forensic intents: "
            "'financial coordination', 'logistical planning', 'suspicious behavior', 'evidence destruction'.\n"
            "Respond ONLY with a valid JSON object where keys are the exact intent names and values are a float between 0.0 and 1.0 representing your confidence. "
            "If an intent is not present, assign it 0.0. Do not include markdown blocks or any other text."
        )

        for sender, messages in sender_messages.items():
            if sender not in risk_profile:
                risk_profile[sender] = {"total_messages_analyzed": 0, "risk_score_sum": 0.0, "detected_behaviors": set()}
            
            # Process in batches of 40 messages to utilize Groq's large context window effectively
            chunks = [messages[i:i + 40] for i in range(0, len(messages), 40)]
            
            for chunk in chunks:
                risk_profile[sender]["total_messages_analyzed"] += len(chunk)
                messages_text = "\n".join([f"- {msg}" for msg in chunk])
                
                try:
                    response = self.chat.invoke([
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=messages_text)
                    ])
                    
                    # Safely extract JSON using regex in case the LLM wraps it in markdown
                    raw_text = response.content
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    
                    if json_match:
                        analysis = json.loads(json_match.group(0))
                        
                        for label, score in analysis.items():
                            try:
                                float_score = float(score)
                                if float_score > 0.7:
                                    risk_profile[sender]["risk_score_sum"] += float_score
                                    risk_profile[sender]["detected_behaviors"].add(label)
                            except ValueError:
                                continue
                except Exception as e:
                    logger.error(f"Groq NLP classification failed for {sender}: {e}")
                
                # Tiny sleep to ensure we don't hit Groq's Free Tier RPM limits
                time.sleep(1.5)

        # Convert sets to lists for DB storage
        for s in risk_profile:
            risk_profile[s]["detected_behaviors"] = list(risk_profile[s]["detected_behaviors"])

        self._save_persistent_results(case_id, risk_profile)
        logger.info("Groq NLP analysis complete and cached to PostgreSQL.")
        return risk_profile

nlp_engine = NLPEngine()
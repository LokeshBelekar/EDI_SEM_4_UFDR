import os
import logging
import pandas as pd
import psycopg2.extras

from database.postgres_db import get_db
from database.neo4j_db import neo4j_conn

# Configure professional logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IngestionEngine")

class DataIngestionEngine:
    """
    High-Performance Enterprise Data Ingestion Engine.
    Handles loading, cleaning, and dual-writing evidence to PostgreSQL and Neo4j.
    Automatically computes relationship 'weights' for advanced graph analytics.
    """
    def __init__(self, dataset_path="touse"):
        self.dataset_path = dataset_path
        self.db = get_db()
        self.neo_driver = neo4j_conn.get_driver()

    def robust_read(self, file_path):
        """Attempts multiple parsers to gracefully load evidence files."""
        try:
            df = pd.read_csv(file_path, dtype=str)
            return df.fillna("")
        except Exception:
            try:
                df = pd.read_excel(file_path, dtype=str)
                return df.fillna("")
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                return None

    def batch_insert_neo4j(self, query, batch_data):
        """Safely executes batched Cypher queries."""
        if not self.neo_driver:
            return
        try:
            with self.neo_driver.session() as session:
                session.run(query, batch=batch_data)
        except Exception as e:
            logger.error(f"Neo4j Batch Insert Error: {e}")

    def run(self):
        """Main orchestrator for scanning directories and routing data ingestion."""
        if not os.path.exists(self.dataset_path):
            logger.error(f"Dataset path '{self.dataset_path}' not found.")
            return

        for case_folder in os.listdir(self.dataset_path):
            case_path = os.path.join(self.dataset_path, case_folder)
            if not os.path.isdir(case_path): continue

            logger.info(f"📂 Processing case: {case_folder}")
            case_id = case_folder # The folder name strictly becomes the case ID

            for file in os.listdir(case_path):
                file_path = os.path.join(case_path, file)
                if os.path.isdir(file_path): continue

                df = self.robust_read(file_path)
                if df is None or df.empty: continue
                
                records = df.to_dict('records')
                file_lower = file.lower()

                # Process the file using isolated database connections
                try:
                    with self.db.get_connection() as conn:
                        with conn.cursor() as cursor:
                            if "messages" in file_lower:
                                self._process_messages(cursor, case_id, records)
                            elif "call_logs" in file_lower:
                                self._process_calls(cursor, case_id, records)
                            elif "contacts" in file_lower:
                                self._process_contacts(cursor, case_id, records)
                            elif "media_sharing" in file_lower:
                                self._process_media(cursor, case_id, records)
                            elif "timeline" in file_lower:
                                self._process_timeline(cursor, case_id, records)
                            
                            # Commit the transaction for this file
                            conn.commit()
                except Exception as e:
                    logger.error(f"❌ Error processing {file}: {e}")

        logger.info("✅ All Isolated UFDR evidence datasets ingested successfully!")

    # -------------------------------------------------------------------------
    # Specific Data Parsers
    # -------------------------------------------------------------------------

    def _process_messages(self, cursor, case_id, records):
        logger.info(f"  ➜ Loading Messages: {len(records)} rows")
        for r in records:
            r["case_id"] = case_id
            r["sender_uid"] = f"{case_id}_{r.get('sender', '')}"
            r["receiver_uid"] = f"{case_id}_{r.get('receiver', '')}"

        pg_data = [(case_id, str(r.get("sender", "")), str(r.get("receiver", "")), 
                    str(r.get("timestamp", "")), str(r.get("message", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO messages(case_id, sender, receiver, timestamp, message) VALUES %s", pg_data)
        
        # Optimized Cypher: Accumulates weight instead of duplicating edges
        self.batch_insert_neo4j("""
        UNWIND $batch AS msg
        MERGE (s:Person {uid: msg.sender_uid}) ON CREATE SET s.name = msg.sender, s.case_id = msg.case_id
        MERGE (r:Person {uid: msg.receiver_uid}) ON CREATE SET r.name = msg.receiver, r.case_id = msg.case_id
        MERGE (s)-[rel:COMMUNICATED_WITH]->(r)
        ON CREATE SET rel.weight = 1
        ON MATCH SET rel.weight = rel.weight + 1
        """, records)

    def _process_calls(self, cursor, case_id, records):
        logger.info(f"  ➜ Loading Calls: {len(records)} rows")
        for r in records:
            r["case_id"] = case_id
            r["caller_final"] = r.get("caller") or r.get("caller_name", "")
            r["receiver_final"] = r.get("receiver") or r.get("receiver_name", "")
            r["caller_uid"] = f"{case_id}_{r['caller_final']}"
            r["receiver_uid"] = f"{case_id}_{r['receiver_final']}"
            dur = r.get("call_duration_seconds", "0")
            r["duration_int"] = int(dur) if str(dur).isdigit() else 0

        pg_data = [(case_id, r["caller_final"], r["receiver_final"], 
                    str(r.get("timestamp", "")), r["duration_int"], str(r.get("call_type", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO calls(case_id, caller, receiver, timestamp, call_duration_seconds, call_type) VALUES %s", pg_data)
        
        # Weighted Cypher for calls (tracks volume AND total duration)
        self.batch_insert_neo4j("""
        UNWIND $batch AS call
        MERGE (c:Person {uid: call.caller_uid}) ON CREATE SET c.name = call.caller_final, c.case_id = call.case_id
        MERGE (r:Person {uid: call.receiver_uid}) ON CREATE SET r.name = call.receiver_final, r.case_id = call.case_id
        MERGE (c)-[rel:CALLED]->(r)
        ON CREATE SET rel.weight = 1, rel.total_duration = call.duration_int
        ON MATCH SET rel.weight = rel.weight + 1, rel.total_duration = rel.total_duration + call.duration_int
        """, records)

    def _process_contacts(self, cursor, case_id, records):
        logger.info(f"  ➜ Loading Contacts: {len(records)} rows")
        pg_data = [(case_id, str(r.get("name") or r.get("Name", "")), str(r.get("phone") or r.get("Phone", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO contacts(case_id, name, phone) VALUES %s", pg_data)

    def _process_media(self, cursor, case_id, records):
        logger.info(f"  ➜ Loading Media: {len(records)} rows")
        for r in records:
            r["case_id"] = case_id
            r["sender_final"] = r.get("sender") or r.get("sender_name", "")
            r["receiver_final"] = r.get("receiver") or r.get("receiver_name", "")
            r["sender_uid"] = f"{case_id}_{r['sender_final']}"
            r["receiver_uid"] = f"{case_id}_{r['receiver_final']}"
            r["file_path"] = r.get("image_file") or r.get("file_path", "")
            r["file_type"] = "image/png" if ".png" in r["file_path"].lower() else "image/jpeg"
        
        pg_data = [(case_id, r["sender_final"], r["receiver_final"], str(r.get("timestamp", "")), r["file_path"], r["file_type"]) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO media_sharing(case_id, sender, receiver, timestamp, file_path, file_type) VALUES %s", pg_data)
        
        self.batch_insert_neo4j("""
        UNWIND $batch AS media
        MERGE (s:Person {uid: media.sender_uid}) ON CREATE SET s.name = media.sender_final, s.case_id = media.case_id
        MERGE (r:Person {uid: media.receiver_uid}) ON CREATE SET r.name = media.receiver_final, r.case_id = media.case_id
        MERGE (s)-[rel:SHARED_MEDIA]->(r)
        ON CREATE SET rel.weight = 1
        ON MATCH SET rel.weight = rel.weight + 1
        """, records)

    def _process_timeline(self, cursor, case_id, records):
        logger.info(f"  ➜ Loading Timeline: {len(records)} rows")
        pg_data = [(case_id, str(r.get("timestamp", "")), str(r.get("event_type", "")), str(r.get("user", "")), str(r.get("details", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO timeline(case_id, timestamp, event_type, user_name, details) VALUES %s", pg_data)

if __name__ == "__main__":
    engine = DataIngestionEngine()
    engine.run()
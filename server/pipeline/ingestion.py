# File: pipeline/ingestion.py
import os
import logging
import pandas as pd
import psycopg2
import psycopg2.extras

from db.postgres import db_manager
from db.neo4j import neo4j_conn
from core.config import settings

# Professional logging configuration for the ETL pipeline
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IngestionEngine")

class DataIngestionEngine:
    """
    High-Performance Data Ingestion Engine for forensic evidence processing.
    Handles extraction, transformation, and dual-writing of evidence to PostgreSQL 
    and Neo4j. Supports binary media injection and relationship weight calculation.
    """
    def __init__(self, dataset_path=None):
        self.dataset_path = dataset_path or settings.DATASET_PATH
        self.db = db_manager
        self.neo_driver = neo4j_conn.get_driver()

    def robust_read(self, file_path: str) -> pd.DataFrame:
        """Attempts to parse forensic data files using multiple standard formats."""
        try:
            df = pd.read_csv(file_path, dtype=str)
            return df.fillna("")
        except Exception:
            try:
                df = pd.read_excel(file_path, dtype=str)
                return df.fillna("")
            except Exception as e:
                logger.warning(f"Parse failure for file {file_path}: {e}")
                return None

    def batch_insert_neo4j(self, query: str, batch_data: list):
        """Executes batched Cypher queries for high-throughput graph updates."""
        if not self.neo_driver:
            return
        try:
            with self.neo_driver.session() as session:
                session.run(query, batch=batch_data)
        except Exception as e:
            logger.error(f"Graph batch insertion failure: {e}")

    def _read_binary_file(self, case_id: str, file_path_or_name: str):
        """
        Locates and reads physical media files from the case directory as 
        raw binary data for secure database storage.
        """
        if not file_path_or_name:
            return "", None
            
        clean_path = str(file_path_or_name).strip(" '\"").replace('\\', '/')
        file_name = os.path.basename(clean_path)
        base_name_no_ext = os.path.splitext(file_name)[0].lower().strip()
        case_dir = os.path.join(self.dataset_path, case_id)
        
        available_images = []
        
        for root, _, files in os.walk(case_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    available_images.append(os.path.join(root, file))
                    
                if os.path.splitext(file)[0].lower().strip() == base_name_no_ext:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "rb") as f:
                            return file, f.read()
                    except Exception as e:
                        logger.warning(f"Binary read error for {full_path}: {e}")
                        return file, None
        
        if available_images:
            fallback_path = available_images[0]
            fallback_name = os.path.basename(fallback_path)
            logger.info(f"Primary image missing. Utilizing fallback evidence: {fallback_name}")
            try:
                with open(fallback_path, "rb") as f:
                    return fallback_name, f.read()
            except Exception:
                pass
        
        return file_name, None

    def run(self):
        """Orchestrates the ingestion sequence across all identified forensic cases."""
        if not os.path.exists(self.dataset_path):
            logger.error(f"Configured dataset path '{self.dataset_path}' is unreachable.")
            return

        for case_folder in os.listdir(self.dataset_path):
            case_path = os.path.join(self.dataset_path, case_folder)
            if not os.path.isdir(case_path): 
                continue

            logger.info(f"Commencing ingestion for case context: {case_folder}")
            case_id = case_folder

            for file in os.listdir(case_path):
                file_path = os.path.join(case_path, file)
                if os.path.isdir(file_path): 
                    continue

                df = self.robust_read(file_path)
                if df is None or df.empty: 
                    continue
                
                records = df.to_dict('records')
                file_lower = file.lower()

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
                            
                            conn.commit()
                except Exception as e:
                    logger.error(f"Transaction failure for file {file}: {e}")

        logger.info("Ingestion sequence finalized for all case datasets.")

    def _process_messages(self, cursor, case_id, records):
        logger.info(f"Processing message logs: {len(records)} entries")
        for r in records:
            r["case_id"] = case_id
            r["sender_uid"] = f"{case_id}_{r.get('sender', '')}"
            r["receiver_uid"] = f"{case_id}_{r.get('receiver', '')}"

        pg_data = [(case_id, str(r.get("sender", "")), str(r.get("receiver", "")), 
                    str(r.get("timestamp", "")), str(r.get("message", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO messages(case_id, sender, receiver, timestamp, message) VALUES %s", pg_data)
        
        self.batch_insert_neo4j("""
        UNWIND $batch AS msg
        MERGE (s:Person {uid: msg.sender_uid}) ON CREATE SET s.name = msg.sender, s.case_id = msg.case_id
        MERGE (r:Person {uid: msg.receiver_uid}) ON CREATE SET r.name = msg.receiver, r.case_id = msg.case_id
        MERGE (s)-[rel:COMMUNICATED_WITH]->(r)
        ON CREATE SET rel.weight = 1
        ON MATCH SET rel.weight = rel.weight + 1
        """, records)

    def _process_calls(self, cursor, case_id, records):
        logger.info(f"Processing call logs: {len(records)} entries")
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
        
        self.batch_insert_neo4j("""
        UNWIND $batch AS call
        MERGE (c:Person {uid: call.caller_uid}) ON CREATE SET c.name = call.caller_final, c.case_id = call.case_id
        MERGE (r:Person {uid: call.receiver_uid}) ON CREATE SET r.name = call.receiver_final, r.case_id = call.case_id
        MERGE (c)-[rel:CALLED]->(r)
        ON CREATE SET rel.weight = 1, rel.total_duration = call.duration_int
        ON MATCH SET rel.weight = rel.weight + 1, rel.total_duration = rel.total_duration + call.duration_int
        """, records)

    def _process_contacts(self, cursor, case_id, records):
        logger.info(f"Processing contact entries: {len(records)} entries")
        pg_data = [(case_id, str(r.get("name") or r.get("Name", "")), str(r.get("phone") or r.get("Phone", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO contacts(case_id, name, phone) VALUES %s", pg_data)

    def _process_media(self, cursor, case_id, records):
        logger.info(f"Processing media sharing records: {len(records)} entries")
        pg_data = []
        for r in records:
            r["case_id"] = case_id
            r["sender_final"] = r.get("sender") or r.get("sender_name", "")
            r["receiver_final"] = r.get("receiver") or r.get("receiver_name", "")
            r["sender_uid"] = f"{case_id}_{r['sender_final']}"
            r["receiver_uid"] = f"{case_id}_{r['receiver_final']}"
            r["file_path"] = r.get("image_file") or r.get("file_path", "")
            r["file_type"] = "image/png" if ".png" in r["file_path"].lower() else "image/jpeg"
            
            file_name, file_binary = self._read_binary_file(case_id, r["file_path"])
            binary_data = psycopg2.Binary(file_binary) if file_binary else None
            
            pg_data.append((
                case_id, r["sender_final"], r["receiver_final"], 
                str(r.get("timestamp", "")), r["file_path"], file_name, 
                r["file_type"], binary_data
            ))
            
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO media_sharing(case_id, sender, receiver, timestamp, file_path, file_name, file_type, file_data) VALUES %s", pg_data)
        
        self.batch_insert_neo4j("""
        UNWIND $batch AS media
        MERGE (s:Person {uid: media.sender_uid}) ON CREATE SET s.name = media.sender_final, s.case_id = media.case_id
        MERGE (r:Person {uid: media.receiver_uid}) ON CREATE SET r.name = media.receiver_final, r.case_id = media.case_id
        MERGE (s)-[rel:SHARED_MEDIA]->(r)
        ON CREATE SET rel.weight = 1
        ON MATCH SET rel.weight = rel.weight + 1
        """, records)

    def _process_timeline(self, cursor, case_id, records):
        logger.info(f"Processing timeline events: {len(records)} entries")
        pg_data = [(case_id, str(r.get("timestamp", "")), str(r.get("event_type", "")), str(r.get("user", "")), str(r.get("details", ""))) for r in records]
        psycopg2.extras.execute_values(cursor, 
            "INSERT INTO timeline(case_id, timestamp, event_type, user_name, details) VALUES %s", pg_data)

if __name__ == "__main__":
    engine = DataIngestionEngine()
    engine.run()
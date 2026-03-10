import os

from parsers.chat_parser import parse_chat_file
from parsers.call_parser import parse_call_file
from parsers.contact_parser import parse_contact_file
from parsers.device_parser import parse_device_file
from parsers.media_parser import parse_media_file

from database.postgres_client import get_connection
from database.neo4j_client import (
    create_message_relationship,
    create_call_relationship
)


def ingest_dataset(dataset_path):

    conn = get_connection()
    cursor = conn.cursor()

    for file in os.listdir(dataset_path):

        file_path = os.path.join(dataset_path, file)

        # -------------------------
        # MESSAGE INGESTION
        # -------------------------
        if file == "messages.json":

            print(f"Processing messages file: {file_path}")

            messages = parse_chat_file(file_path)

            for msg in messages:

                cursor.execute(
                    """
                    INSERT INTO messages(sender, receiver, content, timestamp, source_app)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        msg["sender"],
                        msg["receiver"],
                        msg["content"],
                        msg["timestamp"],
                        msg["source_app"]
                    )
                )

                create_message_relationship(
                    msg["sender"],
                    msg["receiver"],
                    msg["content"],
                    msg["timestamp"]
                )

        # -------------------------
        # CALL LOG INGESTION
        # -------------------------
        elif file == "calls.json":

            print(f"Processing calls file: {file_path}")

            calls = parse_call_file(file_path)

            for call in calls:

                cursor.execute(
                    """
                    INSERT INTO calls(caller, receiver, duration, timestamp)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (
                        call["caller"],
                        call["receiver"],
                        call["duration"],
                        call["timestamp"]
                    )
                )

                create_call_relationship(
                    call["caller"],
                    call["receiver"],
                    call["duration"],
                    call["timestamp"]
                )

        # -------------------------
        # CONTACT INGESTION
        # -------------------------
        elif file == "contacts.json":

            print(f"Processing contacts file: {file_path}")

            contacts = parse_contact_file(file_path)

            for contact in contacts:

                cursor.execute(
                    """
                    INSERT INTO contacts(name, phone_number, email)
                    VALUES (%s,%s,%s)
                    """,
                    (
                        contact["name"],
                        contact["phone_number"],
                        contact["email"]
                    )
                )

        # -------------------------
        # DEVICE INGESTION
        # -------------------------
        elif file == "devices.json":

            print(f"Processing devices file: {file_path}")

            devices = parse_device_file(file_path)

            for device in devices:

                cursor.execute(
                    """
                    INSERT INTO devices(device_id, device_model, os, owner)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (
                        device["device_id"],
                        device["device_model"],
                        device["os"],
                        device["owner"]
                    )
                )

        # -------------------------
        # MEDIA INGESTION
        # -------------------------
        elif file == "media.json":

            print(f"Processing media file: {file_path}")

            media_files = parse_media_file(file_path)

            for media in media_files:

                cursor.execute(
                    """
                    INSERT INTO media_files(file_name, file_type, timestamp, device_id)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (
                        media["file_name"],
                        media["file_type"],
                        media["timestamp"],
                        media["device_id"]
                    )
                )

    conn.commit()

    cursor.close()
    conn.close()

    print("Dataset ingestion completed successfully.")
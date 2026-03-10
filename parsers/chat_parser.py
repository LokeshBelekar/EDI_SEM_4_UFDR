import json

def parse_chat_file(file_path):

    with open(file_path, "r") as f:
        data = json.load(f)

    messages = []

    for msg in data:
        messages.append({
            "sender": msg["sender"],
            "receiver": msg["receiver"],
            "content": msg["message"],
            "timestamp": msg["timestamp"],
            "source_app": "WhatsApp"
        })

    return messages
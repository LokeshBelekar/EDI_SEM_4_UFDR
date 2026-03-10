import json

def parse_media_file(file_path):

    with open(file_path, "r") as f:
        data = json.load(f)

    media_files = []

    for media in data:
        media_files.append({
            "file_name": media["file_name"],
            "file_type": media["file_type"],
            "timestamp": media["timestamp"],
            "device_id": media["device_id"]
        })

    return media_files
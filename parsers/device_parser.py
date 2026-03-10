import json

def parse_device_file(file_path):

    with open(file_path, "r") as f:
        data = json.load(f)

    devices = []

    for device in data:
        devices.append({
            "device_id": device["device_id"],
            "device_model": device["device_model"],
            "os": device["os"],
            "owner": device["owner"]
        })

    return devices
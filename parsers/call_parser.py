import json

def parse_call_file(file_path):

    with open(file_path, "r") as f:
        data = json.load(f)

    calls = []

    for call in data:
        calls.append({
            "caller": call["caller"],
            "receiver": call["receiver"],
            "duration": call["duration"],
            "timestamp": call["timestamp"]
        })

    return calls
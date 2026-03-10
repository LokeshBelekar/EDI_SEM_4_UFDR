import json

def parse_contact_file(file_path):

    with open(file_path, "r") as f:
        data = json.load(f)

    contacts = []

    for contact in data:
        contacts.append({
            "name": contact["name"],
            "phone_number": contact["phone_number"],
            "email": contact.get("email")
        })

    return contacts
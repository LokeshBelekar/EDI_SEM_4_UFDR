from parsers.chat_parser import parse_chat_file
from parsers.call_parser import parse_call_file
from parsers.contact_parser import parse_contact_file
from parsers.device_parser import parse_device_file
from parsers.media_parser import parse_media_file


print("\nTesting Chat Parser\n")
messages = parse_chat_file("datasets/case_001/messages.json")
print(messages)


print("\nTesting Call Parser\n")
calls = parse_call_file("datasets/case_001/calls.json")
print(calls)


print("\nTesting Contact Parser\n")
contacts = parse_contact_file("datasets/case_001/contacts.json")
print(contacts)


print("\nTesting Device Parser\n")
devices = parse_device_file("datasets/case_001/devices.json")
print(devices)


print("\nTesting Media Parser\n")
media = parse_media_file("datasets/case_001/media.json")
print(media)
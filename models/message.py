class Message:
    def __init__(self, sender, receiver, content, timestamp, source_app):
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.timestamp = timestamp
        self.source_app = source_app
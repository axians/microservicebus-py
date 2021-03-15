

class QueueMessage:
    def __init__(self, source, destination, action, message):
        self.source = source
        self.destination = destination
        self.message = message,
        self.action = action

    def __repr__(self):
        return f"source:{self.source} destination:{self.destination} message:{self.message}"

TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

class Message:
    def __init__(self, sender, mess_type, message):
        self.sender = sender
        self.mess_type = mess_type
        self.message = message
    
    def getSender(self):
        return self.sender
    
    def getMessType(self):
        return self.mess_type

    def getMessage(self):
        return self.message

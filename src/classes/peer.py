
class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    def getIP(self):
        return self.ip
    
    def getPort(self):
        return self.port
import socket
import threading
import pickle
from src.classes.message import Message
from src.classes.neighbour import Neighbour

def send(ip, port, data):
    s = socket.socket()
    s.connect((ip, port))
    s.send(pickle.dumps(data))
    s.close()

if __name__ == "__main__":
    neighbours=[]
    neighbours.append(Neighbour('127.0.0.1', 12341))
    neighbours.append(Neighbour('127.0.0.1', 12378))
    neighbours.append(Neighbour('127.0.0.1', 12456))
    data = Message('0', '1', pickle.dumps(neighbours))
    ip='127.0.0.1'
    port = 8081
    t1 = threading.Thread(target=send, args=(ip, port, data))
    t1.start()
    t1.join()
    print('Done!')

import socket
import threading
import pickle
from src.classes.message import Message

def send(ip, port, data):
    s = socket.socket()
    s.connect((ip, port))
    s.send(pickle.dumps(data))
    s.close()

if __name__ == "__main__":
    data = Message('0', '1', 'fgdsfgdsfg')
    ip='127.0.0.1'
    port = 8081
    t1 = threading.Thread(target=send, args=(ip, port, data))
    t1.start()
    t1.join()
    print('Done!')

'''void listen_one(int listen_port,char const* net_interface);
		void async_accept();
		void open_listen_port();
		void close_connection();
		void on_incoming_connection();
		void add_neighbours();
		void process_query();
		void forward_query();
		void construct_response();
		void return_response();
		bool send_keep_alive();
		void add_peer();
		void merge_tables();
		void update_peer_table();'''

import socket
import threading
import pickle
from src.classes.message import Message

def bootstrap_recv(data):
    print(data.getSender())
    print(data.getMessType())
    print(data.getMessage())

def superpeer_recv(data):
    print(data.getSender())
    print(data.getMessType())
    print(data.getMessage())

def peer_recv(data):
    print(data.getSender())
    print(data.getMessType())
    print(data.getMessage())

def listener(port):
    s=socket.socket()
    s.bind(('', port))
    s.listen(5)     
    while True:
        c, addr = s.accept()
        print('Connection established with', addr)
        data=b''
        while True:
            t=c.recv(1024)
            data+=t
            if t==b'':
                break
        print('out')
        d_data = pickle.loads(data)
        if d_data.getSender() == '0':
            bootstrap_recv(d_data)
        elif d_data.getSender() == '1':
            superpeer_recv(d_data)
        else:
            peer_recv(d_data)
        #if sender == b'0': #bootsrap server
        #    bootstrap_recv(mess_type, data)
        c.close()

def send(ip, port, data):
    s = socket.socket()
    s.connect((ip, port))
    s.send(pickle.dumps(data))
    s.close()

def add_neighbours():
    data = Message('1', '1', 'fgdsfgdsfg')
    ip='127.0.0.1' #ip of bootstrap
    port=12300 #port for bootstrap
    t1 = threading.Thread(target=send, args=(ip, port, data))
    t1.start()
    t1.join()

if __name__ == "__main__":
    t1 = threading.Thread(target=listener, args=(8081,))
    t1.start()
    t1.join()
    print("Exiting!")
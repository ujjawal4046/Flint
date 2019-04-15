import socketserver
import socket
import threading
import struct 
import sys
import traceback
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1
MAX_SUPERPEER_ALLOCATION = 3
SUPERPEER_DATAFILE = 'superlist.txt'
class BootstrapManager:
    def __init__(self,ports,interface=''):
        self.m_interface = interface
        self.m_ports = ports
        self.m_superpeers = {}
        self.read_superpeers_from_file(SUPERPEER_DATAFILE)
    def read_superpeers_from_file(self,filename):
        with open(filename,'r') as f:
            for line in f:
                line = line.split(':')
                if len(line) < 3:
                    line.append('0')
                self.m_superpeers[(line[0],int(line[1]))] = int(line[2])
    def listen_on(self,ports,interface=''):
        self.m_ports = ports
        self.m_interface = interface
        self.open_listen_port()
    def open_listen_port(self):
        self.m_listen_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for port in self.m_ports:
            try:
                self.m_listen_socket.bind((self.m_interface,port))
                self.m_listen_socket.listen(5)
                print("[DEBUG] Binding on %s:%d"%(self.m_interface,port))
                break
            except (socket.error):
                pass
        self.accept_incoming_connections()
    def accept_incoming_connections(self):
        while True:
            client,address = self.m_listen_socket.accept()
            print('Came connection from',address)
            self.check_remote_type(client,address)
    def check_remote_type(self,client,address):
        size = 16
        while True:
            try:
                data = client.recv(size)
                print(data)
                assert len(data) >= 1,"[ERROR] Message is too short"
                node_type = struct.unpack('!b',data[0:1])[0]
                payload_len = struct.unpack('!i',data[1:5])[0]
                if node_type == 0:
                    self.write_superpeer_allocation(client)
                elif node_type == 1:
                    if payload_len > 0:
                        self.update_keep_alive(data,client)
                    else:
                        self.write_neighbour_allocation(client)
                else:
                    print(node_type)
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
                
    def write_neighbour_allocation(self,client):
        count = 0
        packet = struct.pack('!b',TYPE_BOOTSTRAP)
        payload = b''
    def write_superpeer_allocation(self,client):
        count = 0
        packet = struct.pack('!b',TYPE_BOOTSTRAP)
        payload = b''
        for ((ip,port),_) in sorted(self.m_superpeers.items(),key=lambda x:x[1]):
            ip_bytes = socket.inet_aton(ip)
            port_bytes = struct.pack("!H",port)
            payload += ip_bytes + port_bytes
            count += 1
            if count == MAX_SUPERPEER_ALLOCATION:
                break
        packet = packet + struct.pack('!i',len(payload)) + payload
        client.sendall(packet)
        client.shutdown(socket.SHUT_RDWR)
        client.close()
    def update_keep_alive(self,data,client):
        pass
        
if __name__ == '__main__':
    bm = BootstrapManager(range(6889,6890),'')
    bm.open_listen_port()

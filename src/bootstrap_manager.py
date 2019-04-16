import socketserver
import socket
import threading
import struct 
import sys
import traceback
import time

TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1
MAX_SUPERPEER_ALLOCATION = 3
SUPERPEER_DATAFILE = 'superlist.txt'
PERCENT_NEIGHBOUR = 0.2
KEEP_ALIVE_EXPIRE_SECONDS = 600

class SuperpeerEntry:
    def __init__(self,port,peer_count,keep_alive):
        self.port = port
        self.peer_count = peer_count
        self.keep_alive = keep_alive

class BootstrapManager:
    def __init__(self,ports,interface=''):
        self.m_interface = interface
        self.m_ports = ports
        #Entries of form (ip)->(SuperpeerEntry)
        self.m_superpeers = {}
        self.read_superpeers_from_file(SUPERPEER_DATAFILE)
    def read_superpeers_from_file(self,filename):
        with open(filename,'r') as f:
            for line in f:
                line = line.split(':')
                if len(line) < 3:
                    line.append('0')
                self.m_superpeers[line[0]] = SuperpeerEntry(int(line[1]),int(line[2]),time.time())
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
                        self.update_keep_alive(data[5:],client,address)
                    else:
                        self.write_neighbour_allocation(data[5:],client,address)
                else:
                    print(node_type)
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
                
    def write_neighbour_allocation(self,data,client,address):
        remote_listen_port = struct.unpack("!H",data)
        
        #If listening port changed than update it
        if address[0] in self.m_superpeers.keys():
            self.m_superpeers[address[0]] = SuperpeerEntry(remote_listen_port,0,time.time())
        
        #Allocate neighbours based on latest keep alive
        count = int(PERCENT_NEIGHBOUR * len(self.m_superpeers))
        packet = struct.pack('!b',TYPE_BOOTSTRAP)
        payload = b''
        for (ip,entry) in sorted(self.m_superpeers.items(),key=lambda x:x[1].keep_alive,reverse=True):
            if not count:
                break
            if ip != address[0]:
                count = count - 1
                ip_bytes = socket.inet_aton(ip)
                port_bytes = struct.pack("!H",entry.port)
                payload += ip_bytes + port_bytes
        
        packet = packet + struct.pack("!i",len(payload)) + payload
        client.sendall(packet)
        client.shutdown(socket.SHUT_RDWR)
        client.close()
    def write_superpeer_allocation(self,client):
        count = 0
        packet = struct.pack('!b',TYPE_BOOTSTRAP)
        payload = b''
        for (ip,entry) in sorted(self.m_superpeers.items(),key=lambda x:x[1].peer_count):
            ip_bytes = socket.inet_aton(ip)
            port_bytes = struct.pack("!H",entry.port)
            payload += ip_bytes + port_bytes
            count += 1
            if count == MAX_SUPERPEER_ALLOCATION:
                break
        packet = packet + struct.pack('!i',len(payload)) + payload
        client.sendall(packet)
        client.shutdown(socket.SHUT_RDWR)
        client.close()
    def update_keep_alive(self,data,client,address):
        assert address in self.m_superpeers.keys, "[ERROR] unidentifiable remote superpeer"
        peer_count = struct.unpack('!H',data)
        #Update peer count and latest keep-alive
        self.m_superpeers[address[0]].peer_count = peer_count
        self.m_superpeers[address[0]].keep_alive = time.time()

"""
Testing part 
"""    
if __name__ == '__main__':
    bm = BootstrapManager(range(6889,6890),'')
    bm.open_listen_port()

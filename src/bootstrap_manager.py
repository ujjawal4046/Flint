import socketserver
import socket
import threading
import struct 
import sys
import traceback
import time
import math
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
        self.m_lock = threading.Lock()
        #Entries of form (ip)->(SuperpeerEntry)
        self.m_superpeers = {}
        #self.read_superpeers_from_file(SUPERPEER_DATAFILE)
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
        #threading.Thread(target=self.accept_incoming_connections,args=()).start()
        self.accept_incoming_connections();
        bm.check_keep_alive()
    def accept_incoming_connections(self):
        while True:
            remote,address = self.m_listen_socket.accept()
            print('[DEBUG] Came connection from',address)
            self.m_lock = threading.Lock()
            threading.Thread(target=self.check_remote_type,args=(remote,address)).start()
    def check_remote_type(self,remote,address):
        size = 16
        while True:
            try:
                data = remote.recv(size)
                print('[DEBUG] remote data:',data)
                print('[DEBUG] lenght of data:',len(data))
                if not len(data):
                    remote.close()
                    return
                
                node_type = struct.unpack('!b',data[0:1])[0]
                payload_len = struct.unpack('!i',data[1:5])[0]
                if node_type == TYPE_PEER:
                    self.write_superpeer_allocation(remote)
                elif node_type == TYPE_SUPERPEER:
                    if address[0] in self.m_superpeers:
                        self.update_keep_alive(data[5:],remote,address)
                    else:
                        self.write_neighbour_allocation(data[5:],remote,address)
                else:
                    print(node_type)
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
                
    def write_neighbour_allocation(self,data,remote,address):
        remote_listen_port = struct.unpack("!H",data)[0]
        print("[DEBUG] Got a superpeer",address[0],remote_listen_port)
        self.m_superpeers[address[0]] = SuperpeerEntry(remote_listen_port,0,time.time())
        
        #Allocate neighbours based on latest keep alive
        count = math.ceil(PERCENT_NEIGHBOUR * len(self.m_superpeers))
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
        remote.sendall(packet)
        remote.shutdown(socket.SHUT_RDWR)
        remote.close()
    def write_superpeer_allocation(self,remote):
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
        remote.sendall(packet)
        remote.shutdown(socket.SHUT_RDWR)
        remote.close()
    def update_keep_alive(self,data,remote,address):
        assert address[0] in self.m_superpeers.keys(), "[ERROR] unidentifiable remote superpeer"
        peer_count = struct.unpack('!H',data)[0]
        #Update peer count and latest keep-alive
        self.m_superpeers[address[0]].peer_count = peer_count
        self.m_superpeers[address[0]].keep_alive = time.time()
        print("[DEBUG] %s"%(address[0]),time.time())
        remote.shutdown(socket.SHUT_RDWR)
        remote.close()
    def check_keep_alive(self):
        #Lock self.m_superpeers To do
        self.m_lock.acquire()
        current_time = time.time()
        for (ip,entry) in self.m_superpeers.items():
            if (current_time - entry.keep_alive) >= KEEP_ALIVE_EXPIRE_SECONDS:
                self.m_superpeers.pop(ip)
        self.m_lock.release()
        threading.Timer(3*KEEP_ALIVE_EXPIRE_SECONDS,self.check_keep_alive).start()
        
"""
Testing part 
"""    
if __name__ == '__main__':
    bm = BootstrapManager(range(6889,6890),'')
    bm.open_listen_port()

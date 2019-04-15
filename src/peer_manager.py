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
SHARED_DIRECTORY = '.'

M_ENTRIES_UPLOAD = 0
M_TABLE_COMPLETE = 1
M_QUERY_KEY = 2
M_QUERY_ID = 3
M_HANDSHAKE = 4

class PeerManager:
    def __init__(self,bootstrap_addr,ports):
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        for port in ports:
            try:
                self.m_bootstrap_socket.connect((bootstrap_addr,port))
                print('Connected on %s %d'%(bootstrap_addr,port))
                break
            except:
                pass
        self.m_superpeers = []
    
    def listen_on(self,ports,interface=""):
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
    def get_superpeers(self):
        packet = struct.pack('!b',TYPE_PEER)
        packet = packet + struct.pack('!i',0)
        try:
            self.m_bootstrap_socket.sendall(packet)
        except (socket.error):
            print("error")
        recv_packet = self.m_bootstrap_socket.recv(1024)
        remote_type = struct.unpack('!b',recv_packet[0:1])[0]
        payload_len = struct.unpack('!i',recv_packet[1:5])[0]
        assert remote_type ==  TYPE_BOOTSTRAP,'[ERROR] remote type is invalid'
        for idx in range(5,payload_len,6):
            ip_addr = socket.inet_ntoa(recv_packet[idx:idx+4])
            port = struct.unpack("!H",recv_packet[idx+4:idx+6])[0]
            self.m_superpeers.append((ip_addr,port))
        print('[DEBUG] ',self.m_superpeers)
    def handshake(self):
        packet = struct.pack("!b",TYPE_PEER)
        payload = struct.pack("")
    def close_bootstrap_connection(self):
        self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
        self.m_bootstrap_socket.close()
    def share_directory(self,pathname=SHARED_DIRECTORY):
        import os
        import hashlib
        contents = os.listdir(pathname)
        table = []
        for file in contents:
            if os.path.isfile(file):
                statinfo = os.stat(file)
                table.append((len(file),file,statinfo.st_size > 0,hashlib.md5(file.encode()).digest()))
                print('[DEBUG] ',table[-1])
        for ssock in self.m_superpeer_sockets:
            threading.Thread(target=self.send_tables,args=(ssock,table)).start()
    def establish_superpeer_connections(self):
        self.m_superpeer_sockets = []
        for remote_end in self.m_superpeers:
            try:
                ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
                ssock.connect(remote_end)
                self.m_superpeer_sockets.append(ssock)
            except Exception as e:
                print("[ERROR] Remote endpoint",remote_end)
                print(e)
                traceback.print_exc()
    def send_tables(self,remote_socket,table):
          packet = struct.pack("!b",TYPE_PEER)
          payload = struct.pack("!i",len(table))
          for (lname,name,is_down,hashid) in table:
              payload = payload + struct.pack("!i",lname) + bytes(name,'ascii') + struct.pack("!b",is_down) + hashid
          packet += struct.pack("!i",len(payload)) + payload
          remote_socket.sendall(packet)
    def gen_query(self,query):
          pass
if __name__ == '__main__':
    pm = PeerManager('',range(6889,6890))
    pm.get_superpeers()
    pm.handshake()
    pm.share_directory()
    
        

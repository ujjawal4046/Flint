import socket
import threading
import struct 
import sys
import traceback
import math
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

MAX_SUPERPEER_ALLOCATION = 3
SHARED_DIRECTORY = '.'

M_ENTRIES_UPLOAD = 0
M_KEEP_ALIVE = 1
M_QUERY_KEY = 2
M_QUERY_ID = 3
M_HANDSHAKE = 4
M_QUERY_KEY_RESP = 5
M_QUERY_ID_RESP = 6

BLOCK_SIZE = 256*1024 #size of block in bytes

class Query:
    QUERY_KEY = M_QUERY_KEY
    QUERY_ID = M_QUERY_ID
    def __init__(self,qtype,qdata):
        self.qstring = qdata
        self.qid = qtype
class QueryResponse:
    def __init__(self,reply_to,response = None):
        self.reply_to = reply_to
        if not response:
            self.response = set()
        else:
            self.response = set(response)
class PeerManager:
    def __init__(self,bootstrap_addr,port):
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_bootstrap_addr = bootstrap_addr
        self.m_bootstrap_port = port
        self.m_lock = threading.Lock()
        self.m_listen_ports = None
        self.m_listen_interface = None
        try:
                self.m_bootstrap_socket.connect((bootstrap_addr,port))
                print('Connected on %s %d'%(bootstrap_addr,port))
        except Exception as e:
                print(e)
                traceback.print_exc()
        self.m_superpeers = []
    
    def listen_on(self,listen_ports,interface=""):
        self.m_listen_ports = listen_ports
        self.m_listen_interface = interface
        self.open_listen_port()
        
    def open_listen_port(self):
        self.m_listen_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for port in self.m_listen_ports:
            try:
                self.m_listen_socket.bind((self.m_listen_interface,port))
                self.m_listen_socket.listen(5)
                print("[DEBUG] Binding on %s:%d"%(self.m_interface,port))
                break
            except (socket.error):
                pass
        #self.accept_incoming_connections()
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
        self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
        self.m_bootstrap_socket.close()
    def handshake(self):
        #handshake with superpeer sharing its port no 
        packet = struct.pack("!b",TYPE_PEER)
        payload = struct.pack("!b",M_HANDSHAKE) + struct.pack("!H",self.m_listen_socket.getsockname()[1])
        packet = packet + struct.pack("!i",len(payload)) + payload
        for remote_sock in self.m_superpeer_sockets:
            remote_sock.sendall(packet)
    def close_bootstrap_connection(self):
        self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
        self.m_bootstrap_socket.close()
    def share_directory(self,pathname=SHARED_DIRECTORY):
        import os
        contents = os.listdir(pathname)
        table = []
        for file in contents:
            if os.path.isfile(file):
                statinfo = os.stat(file)
                table.append((len(file),file,statinfo.st_size > 0,math.ceil(statinfo.st_size/BLOCK_SIZE)))
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
          payload = struct.pack("!b",M_ENTRIES_UPLOAD) + struct.pack("!i",len(table))
          for (lname,name,is_down,block_count) in table:
              payload = payload + struct.pack("!i",lname) + bytes(name,'ascii') + struct.pack("!b",is_down) + struct.pack("!i",block_count)
          packet += struct.pack("!i",len(payload)) + payload
          remote_socket.sendall(packet)
    def start_queries(self):
        while True:
            keyword = input(">[SEARCH]:")
            self.send_query(Query(Query.QUERY_KEY,keyword))
    def send_query(self,query):
          assert query.qid == M_QUERY_KEY or query.qid == M_QUERY_ID, "[ERROR] wrong type of query"
          packet = struct.pack("!b",TYPE_PEER)
          payload = struct.pack("!b",query.qid) + bytes(query.qstring,'ascii')
          packet = packet + struct.pack("!i",len(payload)) + payload
          for ssock in self.m_superpeer_sockets:
              try:
                  ssock.sendall(packet)
                  break
              except Exception as e:
                  print(e)
                  traceback.print_exc()
    
          
if __name__ == '__main__':
    pm = PeerManager('',6889)
    pm.get_superpeers()
    pm.listen_on(range(6889,6890),"")
    pm.establish_superpeer_connections()
    pm.handshake()
    pm.share_directory()
    pm.start_queries()
    
        

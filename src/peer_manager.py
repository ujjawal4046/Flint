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
SHARED_DIRECTORY = "/home/ujjawal/Downloads"

M_ENTRIES_UPLOAD = 0
M_KEEP_ALIVE = 1
M_QUERY_KEY = 2
M_QUERY_ID = 3
M_HANDSHAKE = 4
M_QUERY_KEY_RESP = 5
M_QUERY_ID_RESP = 6
M_QUERY_HANDSHAKE = 7
M_QUERY_BITMAP = 8
M_QUERY_PIECE_REQUEST = 9
M_QUERY_PIECE_RESPONSE = 10

BLOCK_SIZE = 256*1024 #size of block in bytes

MAX_PEERS = 10 

class Query:
    QUERY_KEY = M_QUERY_KEY
    QUERY_ID = M_QUERY_ID
    def __init__(self,qtype,qdata):
        self.qstring = qdata
        self.qid = qtype
class QueryResponse:
    def __init__(self,reply_to,response = None,neigh_count = None):
        self.reply_to = reply_to
        if not neigh_count:
            self.neigh_count = set()
        else:
            self.neigh_count = set(neigh_count)            
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
        self.m_query = None
        self.m_query_peer_set = {}
        self.m_query_interface_to_socket = {}
        self.m_query_peer_to_bitmap = {}
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
                print("[DEBUG] Binding on %s:%d"%(self.m_listen_interface,port))
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
        threading.Thread(target=self.accept_incoming_connections,args=()).start()
    def accept_incoming_connections(self):
        #Accept incoming connections
        while True:
            remote,address = self.m_listen_socket.accept()
            print('[DEBUG] came connection from ',address)
            self.check_remote_type(remote,address)
    def check_remote_type(self,remote,address):
        size = 1024*1024
        while True:
            try:
                data = remote.recv(size)
                if not len(data):
                    remote.close()
                return
                node_type = struct.unpack('!b',data[0:1])[0]
                payload_len = struct.unpack("!i",data[1:5])[0]
                print("[DEBUG] payload len",payload_len)
                if node_type == TYPE_PEER:
                    print("[DEBUG] Remote type was peer")
                    message_type = struct.unpack('!b',data[5:6])[0]
                    if message_type == M_QUERY_HANDSHAKE:
                        qstring = data[6:22]
                        self.send_query_bitmap(qstring, remote)
                    elif message_type == M_QUERY_BITMAP:
                        qstring = data[6:22]
                        if payload_len == 17: #empty bitmap
                            print("[DEBUG] Remote doesn't have file", remote)
                        else:
                            bitmap_len = struct.unpack("!i", data[22:26])[0]
                            bitmap = data[26:26+bitmap_len].decode("utf-8")
                            self.m_query_peer_to_bitmap[qstring][remote]=bitmap
                        self.m_query_peer_set.remove(remote)
                        if len(self.m_query_peer_set) == 0: #received from all
                            pass #TODO call rarest algo
                elif node_type == TYPE_SUPERPEER:
                    print("[DEBUG] Remote type was superpeer")
                    message_type = struct.unpack('!b',data[5:6])[0]
                    my_ip = socket.inet_ntoa(data[6:10])
                    response_len = struct.unpack("!i",data[10:14])[0]
                    pos = 14
                    query_choices_files = []
                    print("[DEBUG] ",message_type,my_ip,response_len)
                    if message_type == M_QUERY_KEY_RESP:
                        for idx in range(response_len):
                            name_len = struct.unpack("!H",data[pos:pos+2])[0]
                            pos += 2
                            file_name = str(data[pos:pos+name_len].decode('utf-8'))
                            print("[DEBUG] got filename for query",file_name)
                            query_choices_files.append(file_name)
                            pos += name_len
                        self.select_from_query_choices(query_choices_files)
                    elif message_type == M_QUERY_ID_RESP:
                        for idx in range(response_len):
                            hosting_ip = socket.inet_ntoa(data[pos:pos+4])
                            hosting_port = struct.unpack("!H",data[pos+4:pos+6])[0]
                            print("[DEBUG] got peer for query",hosting_ip,hosting_port)
                            pos += 6
                            if self.add_to_peer_set(qid, hosting_ip, hosting_port)==True:
                                self.send_query_handshake(qstring, hosting_ip, hosting_port) #TODO add qstring in message payload
                        self.m_query = None
                else:
                    pass
            except Exception as e:
                print(e)
                traceback.print_exc()
    def send_query_bitmap(self, qstring, remote):
        packet = struct.pack("!b",TYPE_PEER)
        payload = struct.pack("!b",M_QUERY_BITMAP) + qstring
        bitmap = self.find_bitmap(self, qstring)
        if bitmap != '': #file present
            payload+=struct.pack("!i", len(bitmap))+ bytes(bitmap,'utf-8')
        packet = packet + struct.pack("!i",len(payload)) + payload
        remote.sendall(packet)  #TODO shutdown socket?
    def send_query_handshake(self, qstring, hosting_ip, hosting_port):
        interface = (hosting_ip, hosting_port)
        packet = struct.pack("!b",TYPE_PEER)
        payload = struct.pack("!b",M_QUERY_HANDSHAKE) + qstring
        packet = packet + struct.pack("!i",len(payload)) + payload
        try:
            ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
            ssock.connect(interface)
            self.m_query_interface_to_socket[qstring][interface]=ssock
            self.m_superpeer_sockets.append(ssock)
        except Exception as e:
            print("[ERROR] Peer endpoint", interface)
            print(e)
            traceback.print_exc()
    def add_to_peer_set(self, qstring, hosting_ip, hosting_port):
        interface = (hosting_ip, hosting_port)
        if interface not in self.m_query_peer_set[qstring] and len(self.m_query_peer_set[qstring])<MAX_PEERS:
            self.m_query_peer_set[qstring].add(interface)
            return True
        return False
    def select_from_query_choices(self,query_choices):
        if len(query_choices) > 0:
            self.m_lock.acquire()
            print("[OUTPUT] Displaying choices for query: ",self.m_query)
            idx = 1
            for choice in query_choices:
                print("[OUTPUT] %d: %s"%(idx,choice))
                idx += 1
            try:
                sidx  = int(input(">[CHOICE]:"))
            except:
                sidx = 0
            if sidx > idx:
                sidx = 0
            import hashlib
            hash_choice = hashlib.md5(query_choices[sidx-1].encode('utf-8')).digest()
            self.m_lock.release()
            print("[DEBUG] querying for %s with hash"%(query_choices[sidx-1]),hash_choice)
            self.send_query(Query(Query.QUERY_ID,hash_choice))
        else:
            print("[OUTPUT] No result for query:",self.m_query)
            self.m_query = None
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
        print('[DEBUG] got superpeer',self.m_superpeers)
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
    def find_bitmap(self, qstring, pathname=SHARED_DIRECTORY):
        import os
        bitmap = ''
        contents = os.listdir(pathname)
        for file in contents:
            if hashlib.md5(file.encode()).digest() == qstring:
                abs_file = pathname + "/" + file 
                if os.path.isfile(abs_file):
                    blocks = math.ceil(os.stat(abs_file).st_size/BLOCK_SIZE)
                    for i in range (0, blocks):
                        bitmap+='1'
                elif os.path.isdir(abs_file): #if block naming is 1 indexed
                    blocks = os.listdir(pathname)
                    for block in blocks:
                        bitmap=bitmap.ljust(block-1, '0')
                        bitmap+='1'
        return bitmap
    def share_directory(self,pathname=SHARED_DIRECTORY):
        import os
        contents = os.listdir(pathname)
        table = []
        for file in contents:
            abs_file = pathname + "/" + file 
            if os.path.isfile(abs_file):
                statinfo = os.stat(abs_file)
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
              payload = payload + struct.pack("!H",lname) + bytes(name,'utf-8') + struct.pack("!b",is_down) + struct.pack("!i",block_count)
          packet += struct.pack("!i",len(payload)) + payload
          
          remote_socket.sendall(packet)
    def start_queries(self):
        while True:
            if self.m_query == None:
                keyword = input(">[SEARCH]:")
                if len(keyword) <= 3:
                    print("[DEBUG] Too short a query.")
                    continue
                else:
                    self.m_query = keyword
                    self.send_query(Query(Query.QUERY_KEY,keyword))
        
            
    def send_query(self,query):
          assert query.qid == M_QUERY_KEY or query.qid == M_QUERY_ID, "[ERROR] wrong type of query"
          packet = struct.pack("!b",TYPE_PEER)
          payload = struct.pack("!b",query.qid) 
          if query.qid == M_QUERY_KEY:
              payload += bytes(query.qstring,'utf-8')
          else:
              payload += query.qstring
              self.m_query_peer_set[query.qstring]=set()
              self.m_query_interface_to_socket[query.qstring]={}
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
    pm.listen_on(range(7312,7355),"")
    pm.establish_superpeer_connections()
    pm.handshake()
    pm.share_directory()
    pm.start_queries()
    
        

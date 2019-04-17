import socket
import threading
import struct 
import sys
import traceback
import hashlib
from peer_manager import Query,QueryResponse
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

TIME_BW_KEEP_ALIVE = 10

M_ENTRIES_UPLOAD = 0
M_KEEP_ALIVE = 1
M_QUERY_KEY = 2
M_QUERY_ID = 3
M_HANDSHAKE = 4
M_QUERY_KEY_RESP = 5
M_QUERY_ID_RESP = 6

BLOCK_SIZE = 256*1024 #size of block in bytes

class SuperpeerManager:
     def __init__(self,bootstrap_addr,port):
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_bootstrap_addr = bootstrap_addr
        self.m_bootstrap_port = port
        self.m_lock = threading.Lock()
        self.m_neighbours = []
        self.m_neighbour_sockets = []
        self.m_listen_ports = None
        self.m_listen_interface = None
        self.m_ip_list = {}
        self.m_file_ip = {}
        self.m_key_files = {}
        self.m_hash_name_map = {}
        self.m_peers = {}
        self.m_query_resp = {}
        try:
                self.m_bootstrap_socket.connect((bootstrap_addr,self.m_bootstrap_port))
                print('[DEBUG] Connected on %s %d'%(bootstrap_addr,self.m_bootstrap_port))
        except Exception as e:
                print(e)
                traceback.print_exc()
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
     def get_neighbours(self):
        self.m_lock.acquire()
        packet = struct.pack("!b",TYPE_SUPERPEER)
        #send listening port to bootstrap as part of handshake
        packet = packet + struct.pack("!i",2) + struct.pack("!H",self.m_listen_socket.getsockname()[1])
        try:
            self.m_bootstrap_socket.sendall(packet)
        except Exception as e:
            print(e)
            traceback.print_exc()
        recv_packet = self.m_bootstrap_socket.recv(1024)
        print("[DEBUG] neighbour recv packet",recv_packet)
        remote_type = struct.unpack('!b',recv_packet[0:1])[0]
        payload_len = struct.unpack('!i',recv_packet[1:5])[0]
        assert remote_type ==  TYPE_BOOTSTRAP,'[ERROR] remote type is invalid'
        for idx in range(5,payload_len,6):
            ip_addr = socket.inet_ntoa(recv_packet[idx:idx+4])
            port = struct.unpack("!H",recv_packet[idx+4:idx+6])[0]
            self.m_neighbours.append((ip_addr,port))
        print('[DEBUG] ',self.m_neighbours)
        self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
        self.m_bootstrap_socket.close()
        self.m_lock.release()
     def establish_neighbour_connections(self):
        for remote_end in self.m_neighbours:
            try:
                ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
                ssock.connect(remote_end)
                print("[DEBUG] connected to neighbour",remote_end)
                self.m_neighbour_sockets.append(ssock)
            except Exception as e:
                print("[ERROR] Remote endpoint",remote_end)
                print(e)
                traceback.print_exc()
     def neighbour_handshake(self):
        #handshake with superpeer sharing its port no 
        packet = struct.pack("!b",TYPE_SUPERPEER)
        payload = struct.pack("!b",M_HANDSHAKE) + struct.pack("!H",self.m_listen_socket.getsockname()[1])
        packet = packet + struct.pack("!i",len(payload)) + payload
        for remote_sock in self.m_neighbour_sockets:
            remote_sock.sendall(packet)
     def accept_incoming_connections(self):
        #Accept incoming connections
        while True:
            remote,address = self.m_listen_socket.accept()
            print('[DEBUG] came connection from ',address)
            self.check_remote_type(remote,address)
     def check_remote_type(self,remote,address):
         size = 1024
         while True:
             try:
                data = remote.recv(size)
                print("[DEBUG] ",data)
                if not len(data):
                    remote.close()
                    return
                while len(data) > 0:
                    node_type = struct.unpack('!b',data[0:1])[0]
                    payload_len = struct.unpack("!i",data[1:5])[0]
                    if node_type == TYPE_PEER:
                        message_type = struct.unpack('!b',data[5:6])[0]
                        peer_id = address[0]
                        if message_type == M_HANDSHAKE:
                             peer_listen_port = struct.unpack("!H",data[6:8])[0]
                             self.m_peers[peer_id] = peer_listen_port
                        elif message_type == M_ENTRIES_UPLOAD:
                             recv_table = []
                             recv_table_len = struct.unpack("!i",data[6:10])[0]
                             data_pos = 10
                             for idx in range(recv_table_len):
                                 file_name_len = struct.unpack("!i",data[data_pos:data_pos+4])[0]
                                 file_name = str(data[data_pos+4:data_pos+4+file_name_len].decode('ascii'))
                                 data_pos += 4+file_name_len
                                 is_down = (struct.unpack("!b",data[data_pos:data_pos+1])[0] == 1)
                                 block_count = struct.unpack("!i",data[data_pos+1:data_pos+5])
                                 data_pos += 5
                                 print("[DEBUG] recieved entry:",file_name_len,file_name,is_down,block_count)
                                 recv_table.append((file_name,is_down,block_count))
                             self.update_entries(peer_id,recv_table)
                        elif message_type == M_QUERY_KEY or M_QUERY_ID:
                            
                            qkey = str(data[6:payload_len+5].decode('ascii'))
                            
                            if message_type == M_QUERY_KEY:
                                query = Query(Query.QUERY_KEY,qkey)
                            else:
                                query = Query(Query.QUERY_ID,qkey)
                            if peer_id not in self.m_query_resp:
                                self.m_query_resp[peer_id] = QueryResponse(address[0])
                            self.query_key_local(peer_id,query)
                            self.query_key_forward(peer_id,query)
                        elif message_type == M_KEEP_ALIVE:
                            pass
                        else:
                            print("[ERROR] invalide message type from peer")
                    elif node_type == TYPE_SUPERPEER:
                        message_type = struct.unpack('!i',data[5:6])[0]
                        if message_type == M_QUERY_KEY:
                            peer_ip = socket.inet_ntoa(data[6:10])[0]
                            qkey = str(data[10:payload_len+5].decode('ascii'))
                            query = Query(Query.QUERY_KEY,qkey)
                            if peer_ip not in self.m_query_resp:
                                self.m_query_resp[peer_ip] = QueryResponse(address[0])
                            self.query_key_local(peer_id,query)
                            self.query_key_forward(peer_id,query)
                        elif message_type == M_QUERY_ID:
                            pass
                        elif message_type == M_QUERY_KEY_RESP:
                            pass
                        elif message_type == M_QUERY_ID_RESP:
                            pass
                        elif message_type == M_HANDSHAKE:
                             neighbour_listen_port = struct.unpack("!H",data[6:8])[0]
                             if (address[0],neighbour_listen_port) not in self.m_neighbours:
                                 self.m_neighbours.append((address[0],neighbour_listen_port))
                                 self.m_neighbour_sockets.append(remote)
                        else:
                            print("[ERROR] invalide message type from superpeer")
                    else:
                        pass
                    if len(data) > 5+payload_len:
                        data = data[5+payload_len:]
                    else:
                        break
             except Exception as e:
                print(e)
                traceback.print_exc()
     def query_key_local(self,peer_id,query):
         if query.qid == Query.QUERY_ID:
             if query.qstring in self.m_file_ip:
                 for host_peer_ip in self.m_file_ip[query.qstring]:
                     self.m_query_resp[peer_id].response.add((host_peer_ip,self.m_peers[host_peer_ip]))
         else:
             if query.qstring in self.m_key_files:
                 for file_id in self.m_key_files[query.qstring]:
                     self.m_query_resp[peer_id].response.add(self.m_hash_name_map[file_id])
     def query_key_forward(self,peer_id,query):
         print("[DEBUG]",query.qstring)
         query_from = self.m_query_resp[peer_id].reply_to
         packet = struct.pack("!b",TYPE_SUPERPEER)
         payload = struct.pack("!b",query.qid)
         payload += socket.inet_aton(peer_id)
         #If query with identifier also port in message
         if query.qid == Query.QUERY_ID:
                     payload += struct.pack("!H",self.m_peer[peer_id])
         payload += bytes(query.qstring,'ascii')
         packet = packet + struct.pack("!i",len(payload)) + payload
         for neig_sock in self.m_neighbour_sockets:
             if neig_sock.getpeername()[0] != query_from:
                try:
                    neig_sock.sendall(packet)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
     def send_keep_alive(self):
        packet = struct.pack("!b",TYPE_SUPERPEER)
        payload = struct.pack("!H",len(self.m_ip_list))
        packet = packet + struct.pack("!i",len(payload)) + payload
        try:
                self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.m_bootstrap_socket.connect((self.m_bootstrap_addr,self.m_bootstrap_port))
                print('[DEBUG] Connected to %s %d'%(self.m_bootstrap_addr,self.m_bootstrap_port))
                self.m_bootstrap_socket.sendall(packet)
                self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
                self.m_bootstrap_socket.close()
        except Exception as e:
                print(e)
                traceback.print_exc()
        threading.Timer(TIME_BW_KEEP_ALIVE,self.send_keep_alive).start()
        
     def update_entries(self,ip_addr,data):
        import re
        if ip_addr not in self.m_ip_list:
                self.m_ip_list[ip_addr]=[]
        for (f_name,f_isdown,f_blockcount) in data:
            f_hashval = hashlib.md5(f_name.encode()).digest()
            self.m_hash_name_map[f_hashval] = f_name
            self.m_ip_list[ip_addr].append((f_name,f_isdown,f_blockcount,f_hashval))
            if f_hashval not in self.m_file_ip:
                self.m_file_ip[f_hashval]=[]
            self.m_file_ip[f_hashval].append(ip_addr)
            token_list= re.split(r',\s*|\s|\.',f_name) # Split by commas and whitespace
            for token in token_list:
                if token not in self.m_key_files:
                    self.m_key_files[token]=[]
                self.m_key_files[token].append(f_hashval)

     def delete_peer_details(self,ip_addr):
        import re
        
        if ip_addr in self.m_peers:
            self.m_peers.pop(ip_addr)
            
        file_list= self.m_ip_list[ip_addr]
        
        if ip_addr in self.m_ip_list:
            self.m_ip_list.pop(ip_addr)
            
        for (f_name,_,_,hash_val) in file_list :
            self.m_file_ip[hash_val].remove(ip_addr)
            if not len(self.m_file_ip[hash_val]):
                self.m_file_ip.pop(hash_val)
            token_list = token_list= re.split(r',\s*|\s|\.',f_name)
            for t in token_list:
                if t in self.m_key_files:
                    self.m_key_files[t].remove(hash_val)
                    if not len(self.m_key_files[t]):
                        self.m_key_files.pop(t)
                        
if __name__ == '__main__':
    sm = SuperpeerManager('',6889)
    interface = ""
    if len(sys.argv) > 1:
        interface = sys.argv[1]
    sm.listen_on(interface,range(7312,7322))
    sm.get_neighbours()
    sm.send_keep_alive()
    sm.establish_neighbour_connections()
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
        self.m_neighbour_sockets = {}
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
        
     def get_neighbours(self):
        
        packet = struct.pack("!b",TYPE_SUPERPEER)
        #send listening port to bootstrap as part of handshake
        packet = packet + struct.pack("!i",2) + struct.pack("!H",self.m_listen_socket.getsockname()[1])
        try:
            self.m_bootstrap_socket.sendall(packet)
        except Exception as e:
            print(e)
            traceback.print_exc()
        recv_packet = self.m_bootstrap_socket.recv(1024)
        if not len(recv_packet):
            print("[ERROR] bootstrap not connecting. Exiting now..")
            self.m_listen_socket.close()
            sys.exit()
        print("[DEBUG] neighbour recv packet",recv_packet)
        remote_type = struct.unpack('!b',recv_packet[0:1])[0]
        payload_len = struct.unpack('!i',recv_packet[1:5])[0]
        assert remote_type ==  TYPE_BOOTSTRAP,'[ERROR] remote type is invalid'
        for idx in range(5,payload_len,6):
            ip_addr = socket.inet_ntoa(recv_packet[idx:idx+4])
            port = struct.unpack("!H",recv_packet[idx+4:idx+6])[0]
            self.m_neighbour_sockets[(ip_addr,port)] = None
        print('[DEBUG] ',self.m_neighbour_sockets)
        self.m_bootstrap_socket.shutdown(socket.SHUT_RDWR)
        self.m_bootstrap_socket.close()
        threading.Thread(target=self.accept_incoming_connections,args=()).start()
     def establish_neighbour_connections(self):
        for remote_end in self.m_neighbour_sockets.keys():
            try:
                ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
                ssock.connect(remote_end)
                print("[DEBUG] connected to neighbour",remote_end)
                threading.Thread(target=self.neighbour_handshake,args=(ssock,remote_end)).start()
                self.m_neighbour_sockets[remote_end] = ssock
            except Exception as e:
                print("[ERROR] Remote endpoint",remote_end)
                print(e)
                traceback.print_exc()
     def neighbour_handshake(self,remote_sock,remote_end):
        #handshake with superpeer sharing its port no 
        packet = struct.pack("!b",TYPE_SUPERPEER)
        payload = struct.pack("!b",M_HANDSHAKE) + struct.pack("!H",self.m_listen_socket.getsockname()[1])
        packet = packet + struct.pack("!i",len(payload)) + payload
        remote_sock.sendall(packet)
        self.check_remote_type(self,remote_sock,remote_end)
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
                while len(data) > 0:
                    node_type = struct.unpack('!b',data[0:1])[0]
                    payload_len = struct.unpack("!i",data[1:5])[0]
                    if node_type == TYPE_PEER:
                        print("[DEBUG] Remote type was peer")
                        message_type = struct.unpack('!b',data[5:6])[0]
                        peer_id = address[0]
                        if message_type == M_HANDSHAKE:
                             print("[DEBUG] Handshake message")
                             peer_listen_port = struct.unpack("!H",data[6:8])[0]
                             self.m_peers[peer_id] = peer_listen_port
                             print("[DEBUG] Added peer",peer_id,peer_listen_port)
                        elif message_type == M_ENTRIES_UPLOAD:
                             print("[DEBUG] Entries upload message")
                             recv_table = []
                             recv_table_len = struct.unpack("!i",data[6:10])[0]
                             data_pos = 10
                             for idx in range(recv_table_len):
                                 file_name_len = struct.unpack("!H",data[data_pos:data_pos+2])[0]
                                 file_name = str(data[data_pos+2:data_pos+2+file_name_len].decode('utf-8'))
                                 data_pos += 2+file_name_len
                                 is_down = (struct.unpack("!b",data[data_pos:data_pos+1])[0] == 1)
                                 block_count = struct.unpack("!i",data[data_pos+1:data_pos+5])
                                 data_pos += 5
                                 print("[DEBUG] recieved entry:",file_name_len,file_name,is_down,block_count)
                                 recv_table.append((file_name,is_down,block_count))
                             self.update_entries(peer_id,recv_table)
                        elif message_type == M_QUERY_KEY or M_QUERY_ID:
                            if peer_id not in self.m_query_resp:
                                self.m_query_resp[peer_id] = QueryResponse(address[0])
                            
                            if message_type == M_QUERY_KEY:
                                qkey = str(data[6:payload_len+5].decode('utf-8'))
                                print("[DEBUG] Key Query type message")
                                query = Query(Query.QUERY_KEY,qkey)
                                self.query_key_local(peer_id,query)
                                self.query_key_forward(peer_id,None,query)
                            else:
                                qkey = data[6:payload_len+5]
                                print("[DEBUG] Hash Query type message")
                                query = Query(Query.QUERY_ID,qkey)
                                self.query_key_local(peer_id,query)
                                self.query_key_forward(peer_id,self.m_peers[peer_id],query)
                            
                        elif message_type == M_KEEP_ALIVE:
                            pass
                        else:
                            print("[ERROR] invalide message type from peer")
                    elif node_type == TYPE_SUPERPEER:
                        print("[DEBUG] Remote type was superpeer")
                        message_type = struct.unpack('!i',data[5:6])[0]
                        peer_ip = socket.inet_ntoa(data[6:10])[0]
                        if message_type == M_QUERY_KEY or message_type == M_QUERY_ID:  
                            if message_type == M_QUERY_KEY:
                                print("[DEBUG] Key Query type message")
                                qkey = str(data[10:payload_len+5].decode('utf-8'))
                                query = Query(Query.QUERY_KEY,qkey)
                                peer_port = None
                            else:
                                 print("[DEBUG] Hash Query type message")
                                 peer_port = struct.unpack("!H",data[10:12])[0]
                                 qhash = str(data[12:payload_len+5]).decode('utf-8')
                                 query = Query(Query.QUERY_ID,qhash)
                            if peer_ip not in self.m_query_resp:
                                self.m_query_resp[peer_ip] = QueryResponse(address[0],None,set(address))
                                self.query_key_local(peer_id,query)
                                self.query_key_forward(peer_id,peer_port,query)
                            else:
                                #ALREADY SEEN QUERY negative response
                                packet = struct.pack("!b",TYPE_SUPERPEER)
                                payload = struct.pack("!b",M_QUERY_KEY_RESP)
                                payload += socket.inet_aton(peer_ip)
                                payload += socket.pack("!i",0)
                                packet = packet + struct.pack("!i",len(payload)) + payload
                                remote.sendall(packet)
                                if address[0] in [addr[0] for addr in self.m_neighbour_sockets.keys()]:
                                    self.m_query_resp[peer_ip].neigh_count.add(address)
                        elif message_type == M_QUERY_KEY_RESP:
                            peer_ip = socket.inet_ntoa(data[6:10])[0]
                            file_name_count = struct.unpack("!i",data[10:14])[0]
                            pos = 14
                            if address[0] in [addr[0] for addr in self.m_neighbour_sockets.keys()]:
                                    self.m_query_resp[peer_ip].neigh_count.add(address)
                            for idx in range(file_name_count):
                                name_len = struct.unpack("!H",data[pos:pos+2])[0]
                                pos += 2
                                file_name = str(data[pos:pos+name_len])
                                self.m_query_resp[peer_ip].response.add(file_name)
                                pos += name_len
                            ##Recived response from everyone send back to originator
                            if len(self.m_query_resp[peer_ip].neigh_count) == len(self.m_neighbour_sockets):
                                self.query_key_reply(peer_ip,message_type)
                        elif message_type == M_HANDSHAKE:
                             neighbour_listen_port = struct.unpack("!H",data[6:8])[0]
                             if (address[0],neighbour_listen_port) not in self.m_neighbour_socket:
                                 self.m_neighbour_sockets[(address[0],neighbour_listen_port)] = remote
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
     def query_key_reply(self,peer_id,qtype):
         reply_ip = self.m_query_resp[peer_id].reply_to
         response_set = self.m_query_resp[peer_id].response
         self.m_query_resp.pop(peer_id)
         rsock = None
         if peer_id == reply_ip:
             try:
                 
                 rsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                 print("[DEBUG] connected to peer",(reply_ip,self.m_peers[reply_ip]))
                 rsock.connect((reply_ip,self.m_peers[reply_ip]))
                 print("[DEBUG] connected to peer",(reply_ip,self.m_peers[reply_ip]))
             except Exception as e:
                 print(e)
                 traceback.print_exc()
         else:
             for (ip,port) in self.m_neighbour_sockets.keys():
                 if ip == reply_ip:
                     rsock = self.m_neighbour_sockets[(ip,port)]
         packet = struct.pack("!b",TYPE_SUPERPEER)
         if qtype == M_QUERY_ID_RESP:
             print("[DEBUG] query hash response create")
             payload = struct.pack("!b",M_QUERY_ID_RESP)
         else:
             print("[DEBUG] query key response create")
             payload = struct.pack("!b",M_QUERY_KEY_RESP)
         payload += socket.inet_aton(peer_id)
         payload += struct.pack("!i",len(response_set))
         if qtype == M_QUERY_KEY_RESP:
             for file_name in response_set:
                 payload += struct.pack("!H",len(file_name))
                 payload += bytes(file_name,'utf-8')
                 print("[DEBUG] ",file_name)
         else:
            for (ip,port) in response_set:
                payload += socket.inet_aton(ip)
                payload += struct.pack("!H",port)
         packet += struct.pack("!i",len(payload)) + payload
         print("[DEBUG] sent packet: ",packet)
         rsock.sendall(packet)
     def query_key_local(self,peer_id,query):
         if query.qid == Query.QUERY_ID:
             print("[DEBUG] local searching for key")
             if query.qstring in self.m_file_ip:
                 for host_peer_ip in self.m_file_ip[query.qstring]:
                     self.m_query_resp[peer_id].response.add((host_peer_ip,self.m_peers[host_peer_ip]))
         else:
             print("[DEBUG] local searching for hash")
             if query.qstring in self.m_key_files:
                 for file_id in self.m_key_files[query.qstring]:
                     self.m_query_resp[peer_id].response.add(self.m_hash_name_map[file_id])
             print("[DEBUG] Local response set:",self.m_query_resp[peer_id].response)
     def query_key_forward(self,peer_id,peer_port,query):
         print("[DEBUG]",query.qstring)
         query_from = self.m_query_resp[peer_id].reply_to
         if len(self.m_neighbour_sockets) > 0:
             packet = struct.pack("!b",TYPE_SUPERPEER)
             payload = struct.pack("!b",query.qid)
             payload += socket.inet_aton(peer_id)
             #If query with identifier also port in message
             if query.qid == Query.QUERY_ID:
                         payload += struct.pack("!H",peer_port)
             payload += bytes(query.qstring,'utf-8')
             packet = packet + struct.pack("!i",len(payload)) + payload
             for (_,neig_sock) in self.m_neighbour_sockets.items():
                 if neig_sock.getpeername()[0] != query_from:
                    try:
                        neig_sock.sendall(packet)
                    except Exception as e:
                        print(e)
                        traceback.print_exc()
         if len(self.m_query_resp[peer_id].neigh_count) == len(self.m_neighbour_sockets) or query.qid == Query.QUERY_ID:
             if query.qid == Query.QUERY_ID:
                 resp_type = M_QUERY_ID_RESP
             else:
                 resp_type = M_QUERY_KEY_RESP
             self.query_key_reply(peer_id,resp_type)
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
    interface = ""
    if len(sys.argv) > 1:
        interface = sys.argv[1]
    sm = SuperpeerManager(interface,6889)
    sm.listen_on(range(7312,7322),"")
    sm.get_neighbours()
    sm.send_keep_alive()
    sm.establish_neighbour_connections()
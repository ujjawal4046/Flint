import socket
import threading
import struct 
import sys
import traceback
import math
import hashlib
import random
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

MAX_SUPERPEER_ALLOCATION = 3


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

BLOCK_SIZE = 1024*1024 #size of block in bytes

MAX_PEERS = 10 

#Block is present or not
BLOCK_REQUEST = 2
BLOCK_HAVE = 1
BLOCK_NOT = 0

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
    
    def __init__(self,shared_dir,bootstrap_addr,port):
        self.SHARED_DIRECTORY = shared_dir
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_bootstrap_addr = bootstrap_addr
        self.m_bootstrap_port = port
        self.m_lock = threading.Lock()
        self.m_listen_ports = None
        self.m_listen_interface = None
        self.m_query = None
        self.m_query_peer_to_socket = {}
        self.m_query_peer_to_bitmap = {}
        self.m_query_peer_to_piece_request = {}
        self.m_query_filename = {}
        self.m_query_pieces = {}
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
        print("[DEBUG] entering check remote type")
        size = 1024*1024
        while True:
            try:
                data = remote.recv(size)
                if not len(data):
                    print('[DEBUG] dropping empty packet')
                    remote.close()
                    print("[DEBUG] returning from check remote type")
                    return
                node_type = struct.unpack('!b',data[0:1])[0]
                payload_len = struct.unpack("!i",data[1:5])[0]
                to_be_recvd = payload_len - len(data) + 5
                while to_be_recvd>0:
                	x = remote.recv(to_be_recvd)
                	to_be_recvd-=len(x)
                	data+=x
                print("[DEBUG] payload len, data len",payload_len, len(data))
                if node_type == TYPE_PEER:
                    print("[DEBUG] Remote type was peer")
                    message_type = struct.unpack('!b',data[5:6])[0]
                    if message_type == M_QUERY_HANDSHAKE:
                        print("[DEBUG] Message for peer handshake")
                        qstring = data[6:22]
                        self.send_query_bitmap(qstring, remote)
                    elif message_type == M_QUERY_BITMAP:
                        print("[DEBUG] Message for peer bitmap")
                        qstring = data[6:22]
                        if payload_len == 17: #empty bitmap
                            print("[DEBUG] Remote doesn't have file", remote)
                        else:
                            bitmap_len = struct.unpack("!i", data[22:26])[0]
                            bitmap = data[26:26+bitmap_len].decode("utf-8")
                            
                            self.m_query_peer_to_bitmap[qstring][address]=bitmap
                            my_bitmap = self.find_bitmap(qstring)
                            print("[DEBUG] my bitmap,", my_bitmap)
                            import os
                            if self.m_query_filename[qstring] not in os.listdir(self.SHARED_DIRECTORY):
                                file_dir = os.path.join(self.SHARED_DIRECTORY,self.m_query_filename[qstring])
                                os.mkdir(file_dir)
                                file = open(os.path.join(file_dir,"metadata.txt"), "w") 
                                file.write("%d"%(bitmap_len))
                                file.close() 
                            if qstring not in self.m_query_pieces.keys():
                                if my_bitmap == '':
                                    self.m_query_pieces[qstring] = [BLOCK_NOT]*bitmap_len
                                else:
                                    self.m_query_pieces[qstring] = []
                                    for i in my_bitmap:
                                        if i == '0':
                                            self.m_query_pieces[qstring].append(BLOCK_NOT)
                                        else:
                                            self.m_query_pieces[qstring].append(BLOCK_HAVE)
                            self.rarest_algo(qstring,remote)
                            print("[DEBUG] returning from check remote type")
                            return
                        #TODO add rarest first
                    elif message_type == M_QUERY_PIECE_REQUEST:
                        print("[DEBUG] Message for piece request")
                        qstring = data[6:22]
                        block_no = struct.unpack("!i",data[22:26])[0]
                        block_data = self.get_block(block_no,qstring)
                        packet = struct.pack("!b",TYPE_PEER)
                        payload = struct.pack("!b",M_QUERY_PIECE_RESPONSE)
                        payload += qstring
                        payload += struct.pack("!i",block_no)
                        payload += block_data
                        packet = packet + struct.pack("!i",len(payload)) + payload 
                        remote.sendall(packet)
                    elif message_type == M_QUERY_PIECE_RESPONSE:
                        print("[DEBUG] Message for piece response")
                        qstring = data[6:22]
                        if qstring not in self.m_query_pieces.keys():
                            continue
                        block_no = struct.unpack("!i",data[22:26])[0]
                        block_data = data[26:5+payload_len]
                        print("[DEBUG] Got piece %d from"%(block_no),address)
                        self.m_lock.acquire()
                        import os
                        self.m_query_pieces[qstring][block_no] = BLOCK_HAVE
                        file_dir = os.path.join(self.SHARED_DIRECTORY,self.m_query_filename[qstring])
                        file = open(os.path.join(file_dir,"%d"%(block_no)), "wb") 
                        file.write(block_data)
                        file.close()
                        self.m_lock.release()
                        self.rarest_algo(qstring,remote)
                        print("[DEBUG] returning from check remote type")
                        return
                        
                    else:
                        print("[DEUBG] Unknown message type",message_type)
                elif node_type == TYPE_SUPERPEER:
                    print("[DEBUG] Remote type was superpeer")
                    message_type = struct.unpack('!b',data[5:6])[0]
                    my_ip = socket.inet_ntoa(data[6:10])
                    query_choices_files = []
                    print("[DEBUG] ",message_type,my_ip)
                    if message_type == M_QUERY_KEY_RESP:
                        response_len = struct.unpack("!i",data[10:14])[0]
                        pos = 14
                        for idx in range(response_len):
                            name_len = struct.unpack("!H",data[pos:pos+2])[0]
                            pos += 2
                            file_name = str(data[pos:pos+name_len].decode('utf-8'))
                            print("[DEBUG] got filename for query",file_name)
                            query_choices_files.append(file_name)
                            pos += name_len
                        self.select_from_query_choices(query_choices_files)
                        self.m_query = None
                    elif message_type == M_QUERY_ID_RESP:
                        qstring = data[10:26]
                        response_len = struct.unpack("!i",data[26:30])[0]
                        pos = 30
                        for idx in range(response_len):
                            hosting_ip = socket.inet_ntoa(data[pos:pos+4])
                            hosting_port = struct.unpack("!H",data[pos+4:pos+6])[0]
                            print("[DEBUG] got peer for query",hosting_ip,hosting_port)
                            pos += 6
                            if (hosting_ip, hosting_port) not in self.m_query_peer_to_socket[qstring] and len(self.m_query_peer_to_socket[qstring])<MAX_PEERS: #TODO add qstring in payload
                                threading.Thread(target=self.send_query_handshake,args=(qstring,hosting_ip, hosting_port)).start()
                else:
                    pass
            except Exception as e:
                print(e)
                traceback.print_exc()
    def get_block(self,block_no,file_hash):
        import os
        for filename in os.listdir(self.SHARED_DIRECTORY):
            hash_choice = hashlib.md5(filename.encode('utf-8')).digest()
            abs_path = os.path.join(self.SHARED_DIRECTORY,filename)
            if(hash_choice==file_hash):
                if os.path.isfile(abs_path):
                    fo=open(abs_path,"rb")
                    offset=block_no*BLOCK_SIZE
                    fo.seek(offset)
                    block_data=fo.read(BLOCK_SIZE)
                    return block_data
                else:
                    file_path=os.path.join(abs_path,str(block_no))
                    fo=open(file_path,"rb")
                    block_data=fo.read()
                    return block_data


    def rarest_algo(self, qstring,my_sock):
        self.m_lock.acquire()
        print("[DEBUG] entering rarest algo")
        bitmap_length=len(self.m_query_pieces[qstring])
        pno_occur=[]
        for i in range(bitmap_length):
            pno_occur.append((i,0))
        for k, v in self.m_query_peer_to_bitmap[qstring].items():
            for i in range(bitmap_length):
                if v[i] == '1':
                    pno_occur[i]=(pno_occur[i][0],pno_occur[i][1]+1)
        for (block_no,count) in sorted(pno_occur,key=lambda x:x[1]):
            if self.m_query_pieces[qstring][block_no] == BLOCK_NOT:
                shuffle_list = list(self.m_query_peer_to_bitmap[qstring].items())
                random.shuffle(shuffle_list)
                for address,bitmap in shuffle_list:
                    if bitmap[block_no] == '1':
                        ssock = self.m_query_peer_to_socket[qstring][address]
                    else:
                        continue
                    print("[DEBUG] Requesting piece %d from"%(block_no),address)
                    packet = struct.pack("!b",TYPE_PEER)
                    payload = struct.pack("!b",M_QUERY_PIECE_REQUEST)
                    payload += qstring
                    payload += struct.pack("!i",block_no)
                    packet = packet + struct.pack("!i",len(payload)) + payload
                    ssock.sendall(packet)
                    self.m_query_pieces[qstring][block_no] = BLOCK_REQUEST
                    if ssock == my_sock:
                        self.m_lock.release()
                        self.check_remote_type(ssock,address)
                        if qstring not in self.m_query_pieces.keys():
                            print("[DEBUG] returning from rarest algo")
                            return
                    break
        complete = True
        if qstring not in self.m_query_pieces.keys():
            print("[DEBUG] returning from rarest algo")
            return
        for check_block in self.m_query_pieces[qstring]:
            if check_block == BLOCK_HAVE:
                complete = complete and True
            else:
                complete = complete and False
        import os
        import shutil
        if complete:
            file_dir = os.path.join(self.SHARED_DIRECTORY,self.m_query_filename[qstring])
            file_fd = open(file_dir+"__MERGE","wb")
            file_old_name = file_fd.name
            file_new_name = file_dir
            print("[DEBUG] Opened file for writing",file_fd.name)
            for block_no in range(len(self.m_query_pieces[qstring])):
                try:
                    block_fd = open(os.path.join(file_dir,"%d"%(block_no)),"rb")
                    file_fd.write(block_fd.read())
                    block_fd.close()
                except Exception as e:

                    print(e)
                    traceback.print_exc()
            #os.rmdir(file_dir)      
            shutil.rmtree(file_dir, ignore_errors=True)
            file_fd.close()
            
            os.rename(file_old_name,file_new_name)
            self.m_query_pieces.pop(qstring)
            self.m_query_peer_to_socket.pop(qstring)
            self.m_query_peer_to_bitmap.pop(qstring)
            self.m_query_peer_to_piece_request.pop(qstring)
        my_sock.shutdown(socket.SHUT_RDWR)
        my_sock.close()
        self.m_lock.release()
        print("[DEBUG] returning from rarest algo")

    def send_query_bitmap(self, qstring, remote):
        packet = struct.pack("!b",TYPE_PEER)
        payload = struct.pack("!b",M_QUERY_BITMAP) + qstring
        bitmap = self.find_bitmap(qstring)
        print('[DEBUG] bitmap', bitmap)
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
            self.m_query_peer_to_socket[qstring][interface]=ssock
            ssock.sendall(packet)
            self.check_remote_type(ssock,interface)
            print("[DEBUG] returning from send query handshake")
            #ssock.recv(1024*1024)
            #threading.Thread(target=self.listen_on_socket,args=(ssock,interface)).start()
        except Exception as e:
            print("[ERROR] Peer endpoint", interface)
            print(e)
            traceback.print_exc()
    def listen_on_socket(self, remote, address):
        while True:
            self.check_remote_type(remote,address)
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
            self.m_query_filename[hash_choice] = query_choices[sidx-1]
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
    def find_bitmap(self, qstring):
	    pathname = self.SHARED_DIRECTORY
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
	            elif os.path.isdir(abs_file): #if block naming is 0 indexed
	                with open(abs_file+"/metadata.txt",'r') as f:
	                    for line in f:
	                        if len(line) > 0:
	                            total_blocks=int(line.strip(), 10) 
	                        else:
	                            print("[ERROR] meta data not present")
	                    for i in range (0, total_blocks):
	                        bitmap+='0'
	                blocks = os.listdir(abs_file)
	                for block in blocks:
	                    print(block)
	                    if block == 'metadata.txt':
	                        continue
	                    bitmap=bitmap[:int(block, 10)]+'1'+bitmap[int(block, 10)+1:]
	                    print(bitmap)
	    return bitmap

    def share_directory(self):
        pathname = self.SHARED_DIRECTORY
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
              self.m_query_peer_to_socket[query.qstring]={}
              self.m_query_peer_to_bitmap[query.qstring]={}
              self.m_query_peer_to_piece_request[query.qstring]={}
          packet = packet + struct.pack("!i",len(payload)) + payload
          for ssock in self.m_superpeer_sockets:
              try:
                  ssock.sendall(packet)
                  break
              except Exception as e:
                  print(e)
                  traceback.print_exc()
    
          
if __name__ == '__main__':
    import os
    shared_directory = os.getcwd()
    bootstrap_ip = ""
    if len(sys.argv) > 1:
        bootstrap_ip = sys.argv[1]
        if len(sys.argv) > 2:
                    shared_directory = sys.argv[2]
    pm = PeerManager(shared_directory,bootstrap_ip,6889)
    
    pm.get_superpeers()
    pm.listen_on(range(7312,7355),"")
    pm.establish_superpeer_connections()
    pm.handshake()
    pm.share_directory()
    pm.start_queries()
    '''testing
    import hashlib
    qstring = hashlib.md5('new_file.txt'.encode()).digest()
    pm.m_query_peer_to_socket[qstring]={}
    pm.m_query_peer_to_bitmap[qstring]={}
    pm.send_query_handshake(qstring, '127.0.0.1', 7313)'''
    
        

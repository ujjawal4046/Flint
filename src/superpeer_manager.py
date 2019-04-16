import socket
import threading
import struct 
import sys
import traceback
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

M_ENTRIES_UPLOAD = 0
M_TABLE_COMPLETE = 1
M_QUERY_KEY = 2
M_QUERY_ID = 3
M_HANDSHAKE = 4

M_KEY = 0
M_ID = 1

class SuperpeerManager:
    files = {} #list of files for key type query
    peers = {} #list of peers for id type query
    recv_neighbours={}
    m_superpeer_sockets=[]
     def __init__(self,bootstrap_addr,ports):
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        for port in ports:
            try:
                self.m_bootstrap_socket.connect((bootstrap_addr,port))
                print('Connected on %s %d'%(bootstrap_addr,port))
                break
            except:
                pass
        self.m_neighbours = []
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
        remote_type = struct.unpack('!b',recv_packet[0:1])[0]
        payload_len = struct.unpack('!i',recv_packet[1:5])[0]
        assert remote_type ==  TYPE_BOOTSTRAP,'[ERROR] remote type is invalid'
        for idx in range(5,payload_len,6):
            ip_addr = socket.inet_ntoa(recv_packet[idx:idx+4])
            port = struct.unpack("!H",recv_packet[idx+4:idx+6])[0]
            self.m_neighbours.append((ip_addr,port))
        print('[DEBUG] ',self.m_neighbours)
     def establish_neighour_connections(self):
        self.m_neighbour_sockets = []
        for remote_end in self.m_neighbours:
            try:
                ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
                ssock.connect(remote_end)
                self.m_superpeer_sockets.append(ssock)
            except Exception as e:
                print("[ERROR] Remote endpoint",remote_end)
                print(e)
                traceback.print_exc()
     def accept_incoming_connections(self):
        #Accept incoming connections
        while True:
            client,address = self.m_listen_socket.accept()
            print('Connection came from',address)
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
                if node_type == TYPE_PEER:
                    message_type = struct.unpack('!i', data[5:6])[0]
                    peer_id = address #IP of the peer requesting will be the query ID
                    if message_type == M_QUERY_KEY:
                        key = struct.unpack('!b', data[6:payload_len])[0]
                        self.key_search(peer_id, key)
                        self.key_request(peer_id, key) 
                elif node_type == TYPE_SUPERPEER:
                    message_type = struct.unpack('!i', data[5:6])[0]
                    peer_id = struct.unpack('!i', data[6:7])[0]
                    recv_neighbours[peer_id][address]=1
                    if message_type == M_KEY:
                        s=7
                        while s<payload_len:
                            if address not in self.files:
                                self.files[peer_id]=[]
                            file_len=struct.unpack('!i', data[s:s+1])[0]
                            self.files[peer_id].append(struct.unpack('!b', data[s+1:s+1+file_len]))
                            s=s+1+file_len
                        all_recv = True
                        for k, v in recv_neighbours:
                            for k1, v1 in v:
                                if v1 == 0:
                                    all_recv=False
                        parent_superpeer=False
                        if all_recv == True:
                            #check if this superpeer is contains the peer
                            for peer in m_ip_list:
                                if peer[0] == peer_id[0]:
                                    parent_superpeer=True
                            if parent_superpeer == True:
                                self.key_response_peer(peer_id) #respond to peer
                            else:
                                self.key_response(peer_id)  #TODO: respond to parent superpeer
                    elif message_type == M_ID:
                        s=7
                        while s<payload_len:
                            if address not in self.peers:
                                self.peers[peer_id]=[]
                            self.peers[peer_id].append(struct.unpack(data[s:s+sys.getsizeof(address)]))
                            s=s+sys.getsizeof(address)
                        all_recv = True
                        for k, v in recv_neighbours:
                            for k1, v1 in v:
                                if v1 == 0:
                                    all_recv=False
                        if all_recv == True:
                            pass #TODO: handle responses similar to key responses
                break
            except Exception as e:
                print(e)
                traceback.print_exc()
    def key_search(self, peer_id, key): #searches the key in self
        for file in self.m_key_files[key]:
            self.files[peer_id].append(file)
    def key_request(self, peer_id, key): #sends neighbours request for key type search
        packet = struct.pack("!b",TYPE_SUPERPEER)
        message_type=M_KEY
        payload=struct.pack('!i', message_type)+struct.pack('!b', peer_id)+struct.pack('!b', key)
        payload_len=len(payload.encode('utf-8'))
        packet = packet + struct.pack("!i",payload_len) + payload
        for soc in self.m_superpeer_sockets:
            try:
                soc.sendall(packet)
            except Exception as e:
                print(e)
                traceback.print_exc()
    def key_response_peer(self, peer_id): #after receiving response from all neibours, sends data to peer
        packet = struct.pack("!b",TYPE_SUPERPEER)
        payload = struct.pack("!i",len(files)) #TODO: create packet
        #for (lname,name,is_down,hashid) in table:
        #    payload = payload + struct.pack("!i",lname) + bytes(name,'ascii') + struct.pack("!b",is_down) + hashid
        try:
            ssock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            ssock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
            ssock.connect(peer_id)
            ssock.sendall(packet)
        except Exception as e:
            print("[ERROR] Remote endpoint",peer_id)
            print(e)
            traceback.print_exc()
        
if __name__ == '__main__':
    sm = SuperpeerManager('',range(6889,6890))
    sm.get_neighbours()
    sm.open_listen_port()
    sm.establish_neighour_connections()
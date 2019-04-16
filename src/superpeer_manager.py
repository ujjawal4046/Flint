import socket
import threading
import struct 
import sys
import traceback
TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1

class SuperpeerManager:
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
        packet = packet + struct.pack("!i",2) + struct.pack("!H",self.m_liste_socket.getsockname()[1])
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
        pass
if __name__ == '__main__':
    sm = SuperpeerManager('',range(6889,6890))
    sm.get_neighbours()
    sm.open_listen_port()
    sm.establish_neighour_connections()
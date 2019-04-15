import socketserver
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

    def get_neighbours(self):
        packet = struct.pack("!b",TYPE_SUPERPEER)
        packet = packet + struct.pack("!i",0)
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

if __name__ == '__main__':
    sm = SuperpeerManager('',range(6889,6890))
    sm.get_neighbours()
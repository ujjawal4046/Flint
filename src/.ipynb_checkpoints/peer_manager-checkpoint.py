import socketserver
import socket
import threading
import struct 
import sys

TYPE_BOOTSTRAP = 2
TYPE_PEER = 0
TYPE_SUPERPEER = 1
class PeerManager:
    def __init__(self,bootstrap_addr,port):
        self.m_bootstrap_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.m_bootstrap_socket.connect((bootstrap_addr,port))
    def get_superpeers(self):
        packet = struct.pack('!b',0)
        packet = packet + struct.pack('!i',0)
        self.m_bootstrap_socket.sendall(packet)
        
        recv_packet = self.m_bootstrap_socket.recv(1024)
        remote_type = struct.unpack('!b',recv_packet[0])[0]
        payload_len = struct.unpack('!i',recv_packet[1:5])[0]
        
        assert remote_type ==  TYPE_BOOTSTRAP,'[ERROR] remote type is invalid'
        
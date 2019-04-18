import math
import hashlib

SHARED_DIRECTORY = "/home/sibby/Documents/shared"
BLOCK_SIZE = 256*1024 #size of block in bytes

def find_bitmap(qstring, pathname=SHARED_DIRECTORY):
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
                blocks = os.listdir(abs_file)
                for block in blocks:
                    if block == 'metadata.txt':
                        continue
                    bitmap=bitmap.ljust(int(block, 10)-1, '0')
                    bitmap+='1'
                total_blocks=0
                with open(abs_file+"/metadata.txt",'r') as f:
                    for line in f:
                        if len(line) > 0:
                            total_blocks=int(line.strip(), 10) 
                        else:
                            print("[ERROR] meta data not present")
                for i in range(len(bitmap), total_blocks):
                    bitmap+='0'
    return bitmap
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
if __name__ == '__main__':
    print(find_bitmap(hashlib.md5('new_file.txt'.encode()).digest()))
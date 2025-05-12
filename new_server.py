import socket
import threading
import struct
from colors import colors
import time

servers = {}
clients = {}
listening_port = None


def create_sock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock

def encode_client_dict():
    return ("\0".join(f"{key}" for key in clients.keys())).encode()
def print_servers_dict():
    global servers
    colors.printC("orange", "\nConnected server list: ")
    [colors.printC("orange", f"\t{item}") for item in servers.items()]


def print_clients_dict(nameOnly=False):
    global clients
    colors.printC("orange", "\nConnected clients list: ")
    if not len(clients):
        colors.printC("orange", f"\t**Empty**")
    elif nameOnly:
        [colors.printC("orange", f"\t{item[0]}") for item in clients.items()]
    else:
        [colors.printC("orange", f"\t{item}") for item in clients.items()]


def decode_to_portIp_list(encoded):
    return [(ip, int(port)) for ip, port in (address.split(':') for address in encoded.decode().split('\0'))]


def encode_servers_dict():
    return ("\0".join(f"{ip}:{port}" for ip, port in servers.keys())).encode()


def wait_for_accept(sock):
    while True:
        conn, client_address = sock.accept()
        print("Server/client is listening on port", listening_port)
        threading.Thread(target=receive_message, args=(conn,)).start()


def add_client(sock, mLen):
    name = sock.recv(mLen).decode()
    clients[name] = sock
    colors.printC("orange", f"\nAdded client '{name}'", False)
    print_clients_dict(True)


def get_client_message_details(sock, length):
    sender = sock.recv(length).decode()
    header = sock.recv(6)
    mType, mSubType, mLen, mSubLen = struct.unpack('>bb hh', header)
    receiver = sock.recv(mSubLen).decode()
    message = sock.recv(mLen).decode()
    print(f"Message received to server {listening_port} --> Sender: {sender}, Receiver: {receiver}, message: {message}")
    return sender, receiver, message


def transfer_messge_to_client(receiver, peers, message):
    if receiver in clients:
        packet = struct.pack('>bb hh', 3, 0, len(peers), len(message))
        colors.printC("green", f"The client '{receiver}' is in my clients list")
        send_data_to_socket(clients[receiver], packet, peers, message)
    else:
        colors.printC("red", f"The client '{receiver}' is not in my clients list")


def get_message_from_broadcast_to_client(sock, mLen, mSubLen):
    peers = sock.recv(mLen)
    sender = peers.decode().split('\0')[0]
    receiver = peers.decode().split('\0')[1]
    message = sock.recv(mSubLen)
    transfer_messge_to_client(receiver, peers, message)


def get_message_from_client(sock, mSubLen):
    sender, receiver, message = get_client_message_details(sock, mSubLen)
    peers = sender.encode() + b'\0' + receiver.encode()
    colors.printC("lightgrey", f"Encoded peers: ", False)
    colors.printC("cyan", f"{peers}")
    if receiver not in clients:
        colors.printC("red", f"The client '{receiver}' is not in my clients list")
        for serverSock in servers:
            packet = struct.pack('>bb hh', 3, 3, len(peers), len(message))
            send_data_to_socket(servers[serverSock], packet, peers, message.encode())
    transfer_messge_to_client(receiver, peers, message.encode())


def get_echo_for_rtt(sock, mLen):
    colors.printC("lightblue", f"{sock.recv(mLen).decode()}")
    time.sleep(0.1)
    packet = struct.pack('>bb hh', 1, 3, 0, 0)
    send_data_to_socket(sock, packet, str(listening_port).encode())


def send_connected_clients(sock):
    encode_clients = encode_client_dict()
    packet = struct.pack('>bb hh', 1, 1, len(encode_clients), 0)
    send_data_to_socket(sock,packet, encode_clients)


def receive_message(sock):
    while True:
        try:
            header = sock.recv(6)
        except:
            colors.printC("red", "connection closed! dead socket")
            break

        mType, mSubType, mLen, mSubLen = struct.unpack('>bb hh', header)
        ##################### 0 0 0 #####################
        if mType == 0:
            if mSubType == 0:
                print("\nIn type 0 sub 0")
                connect_to_a_parallel_socket(sock, False)
            elif mSubType == 1:
                send_connected_clients(sock)
            elif mSubType == 2:
                print("\nIn type 0 sub 2")
                connect_to_a_parallel_socket(sock, True)
            elif mSubType == 3:  # Request for RTT
                print("\nIn type 0 sub 3")
                get_echo_for_rtt(sock, mLen)
            elif mSubType == 4:
                print("\nIn type 0 sub 4")
                send_servers_information(sock)
        ##################### 1 1 1 #####################
        elif mType == 1:
            if mSubType == 0:
                print("\nIn type 1 sub 0")
                get_information_on_servers(sock, mLen)
            elif mSubType == 1:
                print("\nIn type 1 sub 1")
                get_information_on_clients(sock, mLen)
            elif mSubType == 2:
                print("\nIn type 1 sub 2")
        ##################### 2 2 2 #####################
        elif mType == 2:
            if mSubType == 0:
                print("\nIn type 2 sub 0")
            elif mSubType == 1:
                print("\nIn type 2 sub 1")
                # if mLen > 0:
                add_client(sock, mLen)
            elif mSubType == 2:
                print("\nIn type 2 sub 2")
                close_client_socket(sock, mLen)
                break

        ##################### 3 3 3 #####################
        elif mType == 3:
            if mSubType == 0:
                print("s\nIn type 3 sub 0")
                get_message_from_client(sock, mSubLen)
            elif mSubType == 1:
                pass
            elif mSubType == 3:
                print("\nIn type 3 sub 3")
                get_message_from_broadcast_to_client(sock, mLen, mSubLen)


def close_client_socket(sock, mLen):
    client = sock.recv(mLen).decode()
    colors.printC("lightred", f"'{client}' want to close connection")
    packet = struct.pack('>bb hh', 2, 1, 0, 0)
    send_data_to_socket(sock, packet, str(listening_port).encode())
    # send_data_to_socket(clients[client], )
    del clients[client]
    colors.printC("orange", f"\nRemoved client '{client}'", False)
    print_clients_dict(True)
def connect_to_a_parallel_socket(connSocket, fromList):
    connected_server = connSocket.recv(4).decode()
    sock = create_sock()
    sock.connect(('127.0.0.1', int(connected_server)))
    print("\nConnected socket", sock.getpeername())
    if not fromList:
        send_servers_information(sock)
        # print("is not From List")
    # else:
    # print("is From List")  # to remove later
    servers[sock.getpeername()] = sock
    print_servers_dict()


def send_servers_information(sock):
    colors.printC("lightgrey", f"\nEncoded server dict: ", False)
    colors.printC("cyan", f"{encode_servers_dict()}")
    encodedServerDict = encode_servers_dict()
    serverDictLen = len(encodedServerDict)
    if serverDictLen > 0:
        # print("\nin len bigger 0")
        packet = struct.pack('>bb hh', 1, 0, serverDictLen, 0)
        send_data_to_socket(sock, packet, encodedServerDict)
    else:
        pass
        # print("\nnot in len bigger 0")
        # packet = struct.pack('>bb hh', 1, 2, 0, 0)
        # send_data_to_socket(sock, packet)


def get_information_on_clients(sock, mLen):
    pass


def get_information_on_servers(sock, mLen):
    # print("\nin get infor")
    message = sock.recv(mLen)
    if mLen > 0:
        # print("\nin get info, len in bigger than 0")
        serverList = decode_to_portIp_list(message)
        print("server lis got from server", serverList)
        connect_to_servers_in_list(serverList)
    else:
        print("no other connection")


def connect_to_servers_in_list(serverList):
    print("in connection   ", serverList)
    for addr in serverList:
        sock = create_sock()
        sock.connect(addr)
        packet1 = struct.pack('>bb hh', 2, 0, 0, 0)
        packet2 = struct.pack('>bb hh', 0, 2, 0, 0)
        send_data_to_socket(sock, packet1, packet2, str(listening_port).encode())
        print("conected to ", sock.getpeername())
        servers[addr] = sock
        print_servers_dict()


def bind_to_server():
    global listening_port
    ports = [3000, 3001, 3002, 3003, 3004]
    # ports = [3000, 3001, 3002]
    choice = ports[int(input("Choose port from 0 to 4: "))]
    listening_port = choice
    sock1 = create_sock()
    sock1.bind(('0.0.0.0', choice))
    sock1.listen(1)
    colors.printC("lightgreen", f"Server bind successfully to {choice}")
    connect_to_servers(ports, choice, sock1)


def send_data_to_socket(sock, *datas):
    [sock.send(data) for data in datas]


def connect_to_servers(ports, choice, sock):
    for p in ports:
        if p != choice:
            sock2 = create_sock()
            try:
                sock2.connect(('127.0.0.1', p))
                servers[sock2.getpeername()] = sock2
                print_servers_dict()
                colors.printC("lightgreen", f"successful connection to {p}")
                packet1 = struct.pack('>bb hh', 2, 0, 0, 0)
                packet2 = struct.pack('>bb hh', 0, 0, 0, 0)
                send_data_to_socket(sock2, packet1, packet2, str(choice).encode())
                break
            except ConnectionRefusedError:
                colors.printC("lightred", f"Connection failed to port: {p}")
    threading.Thread(target=wait_for_accept, args=(sock,)).start()


def main():
    bind_to_server()


if __name__ == '__main__':
    main()


# if want to run the program. paste it to another py file and add import if needed

# class colors:
#     reset = '\033[0m'
#     bold = '\033[01m'
#     disable = '\033[02m'
#     underline = '\033[04m'
#     reverse = '\033[07m'
#     strikethrough = '\033[09m'
#     invisible = '\033[08m'
#
#     class fg:
#         black = '\033[30m'
#         red = '\033[31m'
#         green = '\033[32m'
#         orange = '\033[33m'
#         blue = '\033[34m'
#         purple = '\033[35m'
#         cyan = '\033[36m'
#         lightgrey = '\033[37m'
#         darkgrey = '\033[90m'
#         lightred = '\033[91m'
#         lightgreen = '\033[92m'
#         yellow = '\033[93m'
#         lightblue = '\033[94m'
#         pink = '\033[95m'
#         lightcyan = '\033[96m'
#
#     class bg:
#         black = '\033[40m'
#         red = '\033[41m'
#         green = '\033[42m'
#         orange = '\033[43m'
#         blue = '\033[44m'
#         purple = '\033[45m'
#         cyan = '\033[46m'
#         lightgrey = '\033[47m'
#
#     @staticmethod
#     def printC(color, text, newline=True):
#         if newline:
#             print(eval(f"colors.fg.{color}") + text + colors.reset)
#         else:
#             print(eval(f"colors.fg.{color}") + text + colors.reset, end="")

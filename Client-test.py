import socket
import threading
import struct
import time
from colors import colors

userName = ''
serversRTT = {}
servers = {}
start_time = 0
end_time = 0
connectedServer = 0



def print_clients(sock,mLen):
    clients = sock.recv(mLen).decode()
    c = ", ".join(clients.split('\0'))
    colors.printC("orange", f"Connected clients: {c}")

def create_sock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


def send_data_to_socket(sock, *datas):
    [sock.send(data) for data in datas]

def print_rtt_dict():
    colors.printC("lightblue", f'RTT list:')
    [colors.printC("lightblue", f'\t{item[0][1]}: {item[1]}') for item in sorted(serversRTT.items())]


def decode_to_portIp_list(encoded):
    return [(ip, int(port)) for ip, port in (address.split(':') for address in encoded.decode().split('\0'))]


def send_RTT(sock):
    global start_time
    reset_times()
    echo = f"Echo from '{userName}'"
    packet = struct.pack('>bb hh', 0, 3, len(echo.encode()),0)
    send_data_to_socket(sock, packet, echo.encode())
    start_time = time.time()


def get_rtt_and_update(sock):
    global end_time
    end_time = time.time()
    elapse = end_time - start_time
    server = ("127.0.0.1", int(sock.recv(4).decode()))
    serversRTT[server] = elapse
    # colors.printC("lightblue", f'\nRTT list: {serversRTT}')


def reset_times():
    global start_time
    global end_time
    start_time = end_time = 0


def get_message(sock):
    while True:
        try:
            header = sock.recv(6)
        except:
            colors.printC("red", "connection closed! dead socket")
            break

        mType, mSubType, mLen, mSubLen = struct.unpack('>bb hh', header)
        if mType == 1:
            if mSubType == 0:
                print("\nIn type 1 sub 0")
                get_information_on_servers(sock, mLen)
            elif mSubType == 1:
                print("\nIn type 1 sub 1")
                print_clients(sock, mLen)
            elif mSubType == 2:
                print("\nIn type 1 sub 2")
            elif mSubType == 3:
                print("\nIn type 1 sub 3")
                get_rtt_and_update(sock)
                colors.printC("lightblue", f"{sock.getpeername()[1]}: {serversRTT[sock.getpeername()]}")
        elif mType == 2:
            if mSubType == 1:
                print("\nIn type 2 sub 1")
                close_socket(sock)
                break
        elif mType == 3:
            if mSubType == 0:
                print("\nIn type 3 sub 0")
                decode_message(sock, mLen, mSubLen)


def close_socket(sock):
    server = ('127.0.0.1', int(sock.recv(4).decode()))
    colors.printC("lightred", f"The server {server[1]} disconnecting")
    sock.close()


def decode_message(sock, mLen, mSubLen):
    sender_name = sock.recv(mLen).decode().split('\0')[0]
    message = sock.recv(mSubLen).decode()
    colors.printC("cyan", f"Message from {sender_name}: ", False)
    colors.printC("lightgreen", f"{message}")


def send_message(sock):
    # colors.printC("lightgrey", f"\nEnter 'rtt' or message in the format: ", False)
    # colors.printC("orange", f"< to who >: < message >")
    while True:
        message = input()
        if message == "rtt":
            send_RTT(sock)
        elif message == "clients":
            packet1 = struct.pack('>bb hh', 0, 1, 0, 0)
            send_data_to_socket(sock, packet1)


        elif message == "refresh":
            # send_RTT(sock) #todo fix how to change current rtt befor refreshing
            packet1 = struct.pack('>bb hh', 0, 4, 0, 0)
            send_data_to_socket(sock, packet1)
        elif ": " in message and not message.startswith(": "):
            post = message.split(": ")
            message = post[1].encode()
            name = post[0].encode()
            packet1 = struct.pack('>bb hh', 3, 0, 0, len(userName))
            packet2 = struct.pack('>bb hh', 3, 0, len(message), len(name))
            send_data_to_socket(sock, packet1, userName.encode(), packet2, name, message)
        else:
            colors.printC("red", f"Syntax error!")
            colors.printC("lightgrey", f"Enter 'rtt' or message in the format: ", False)
            colors.printC("orange", f"< to who >: < message >")


def get_information_on_servers(sock, mLen):
    message = sock.recv(mLen)
    if mLen == 0:
        colors.printC("red", "no other connection")
    else:
        serverList = decode_to_portIp_list(message)
        connect_to_servers_in_list(serverList)


def connect_to_servers_in_list(serverList):
    global connectedServer, servers
    # print("List of active servers", serverList)
    for index, addr in enumerate(serverList):
        sock = create_sock()
        sock.connect(addr)
        packet1 = struct.pack('>bb hh', 2, 1, len(userName), 0)
        send_data_to_socket(sock, packet1, userName.encode())
        colors.printC("lightgreen", f"{userName} is connected to {sock.getpeername()}")
        servers[addr] = sock

        send_RTT(sock)
        header = sock.recv(6)
        mType, mSubType, mLen, mSubLen = struct.unpack('>bb hh', header)
        get_rtt_and_update(sock)

        compare_rtt_and_switch_server(sock)
    print_rtt_dict()
    threading.Thread(target=send_message, args=[servers[connectedServer]]).start()


def compare_rtt_and_switch_server(sock):
    global connectedServer, servers, serversRTT
    if serversRTT[connectedServer] > serversRTT[sock.getpeername()]:
        threading.Thread(target=get_message, args=[servers[sock.getpeername()]]).start()
        colors.printC("green", f"Switched to {sock.getpeername()}")
        packet = struct.pack('>bb hh', 2, 2, len(userName), 0)
        send_data_to_socket(servers[connectedServer], packet, userName.encode())  # send request to close
        connectedServer = sock.getpeername()  # change to the new port

    else:
        threading.Thread(target=get_message, args=[sock]).start()
        colors.printC("green", f"stayed {connectedServer}")
        packet = struct.pack('>bb hh', 2, 2, len(userName), 0)
        send_data_to_socket(sock, packet, userName.encode())  # send request to close



def ask_for_server_list(sock):
    pass


def connect_to_server():
    global userName, servers, connectedServer
    userName = input("Enter your name: ")
    ports = [3000, 3001, 3002, 3003, 3004]
    text = "Choose server port to connect:\n0 - 3000\n1 - 3001\n2 - 3002\n3 - 3003\n4 - 3004\n"
    choice = ports[int(input(text))]
    sock = create_sock()
    try:
        sock.connect(('127.0.0.1', choice))
        connectedServer = sock.getpeername()
        packet1 = struct.pack('>bb hh', 2, 1, len(userName), 0)
        send_data_to_socket(sock, packet1, userName.encode())
        servers[('127.0.0.1', choice)] = sock
        send_RTT(sock)
        colors.printC("lightgreen", f"{userName} is connected to {sock.getpeername()}")

        packet2 = struct.pack('>bb hh', 0, 4, len(userName), 0)
        send_data_to_socket(sock, packet2)
    except ConnectionRefusedError:
        colors.printC("red", f"Connection failed to port: {connectedServer}")
    threading.Thread(target=get_message, args=[sock]).start()


def main():
    connect_to_server()


if __name__ == '__main__':
    main()

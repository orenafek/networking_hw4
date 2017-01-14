import socket
import select
import sys
import queue

HOST = '10.0.0.1'
HOST_SERV1 = '192.168.0.101'
HOST_SERV2 = '192.168.0.102'
HOST_SERV3 = '192.168.0.103'
HOST_SERVERS = [HOST_SERV1, HOST_SERV2, HOST_SERV3]
PORT_SERVERS = 80
PORT_CLIENTS = 80

NO_OF_CLIENTS = 100  # TODO: Change to ???

S1_INDEX = 0
REQUEST_SIZE = 4096  # TODO: Change to 9 chars
RESPONSE_SIZE = 4096  # TODO: Change to ???


class Server(object):
    def __init__(self, ip, port, name):
        self._name = name
        self.ip = ip
        self.port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.ip, self.port))
        # self._socket.setblocking(0)  # non blocking
        self.clients = queue.Queue()

    def close_socket(self):
        self._socket.close()

    def handle_client(self, client_socket):
        self.clients.put_nowait(client_socket)
        request = client_socket.recv(REQUEST_SIZE)
        if request:
            print('{0}: New Request Arrived: {1}'.format(self._name, request))
            self._socket.sendall(request)

        else:
            print('Request (s:{0},c:{1}) is empty :('.format(self._name, client_socket.getpeername()))

    def get_first_client(self):
        return self.clients.get_nowait()

    def socket(self):
        return self._socket

    def return_to_client(self):
        client = self.clients.get_nowait()
        response = self._socket.recv(RESPONSE_SIZE)
        if not response:
            print('Response is empty :(')
            return

        client.sendall(response)


def connect_to_servers():
    return Server(HOST_SERV1, PORT_SERVERS, 's1'), \
           Server(HOST_SERV2, PORT_SERVERS, 's2'), \
           Server(HOST_SERV3, PORT_SERVERS, 's3')


def create_client_socket():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.bind((HOST, PORT_CLIENTS))
    client.listen(NO_OF_CLIENTS)
    return client


def run_proxy(s1, s2, s3, client_socket):
    inputs = [client_socket, s1.socket(), s2.socket(), s3.socket()]
    servers = [s1, s2, s3]
    while 1:
        readable, _, _ = select.select(inputs, [], [])
        for s in readable:
            if s is client_socket:  # new client
                print('New Connection Arrived!')
                connection, client_address = s.accept()
                # connection.setblocking(0)
                inputs.append(connection)  # return to select

            elif s is s1.socket():
                s1.return_to_client()

            elif s is s2.socket():
                s2.return_to_client()

            elif s is s3.socket():
                s3.return_to_client()

            else:  # from old client
                s1.handle_client(s)

    for server in servers:
        server.close_socket()

    client_socket.close()


def main():
    (s1, s2, s3) = connect_to_servers()
    client_socket = create_client_socket()
    run_proxy(s1, s2, s3, client_socket)


if __name__ == '__main__':
    main()


def backup(s, message_queues, outputs, writable, next_msg):
    data = s.recv(1024)  # TODO: maybe decrease size...
    if data:
        message_queues[S1_INDEX].put(data)
        if s not in outputs:
            outputs.append(s)

    for s in writable:
        try:
            pass
        except queue.Empty:
            # No messages waiting so stop checking for writability.
            outputs.remove(s)
        else:
            s.send(next_msg)

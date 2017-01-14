import socket
import select

HOST = '10.0.0.1'
HOST_SERV1 = '192.168.0.101'
HOST_SERV2 = '192.168.0.102'
HOST_SERV3 = '192.168.0.103'
HOST_SERVERS = [HOST_SERV1, HOST_SERV2, HOST_SERV3]
PORT_SERVERS = 80
PORT_CLIENTS = 80

NO_OF_CLIENTS = 100
REQUEST_SIZE = 4096
RESPONSE_SIZE = 4096


class Server(object):
    def __init__(self, ip, port, name):
        self._name = name
        self._id = int(name[1])
        self.ip = ip
        self.port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.ip, self.port))
        self.clients = []

    def close_socket(self):
        self._socket.close()

    def handle_client(self, client_socket, request):
        self.clients.append(client_socket)
        self._socket.sendall(request)

    def get_first_client(self):
        client = self.clients[0]
        self.clients = self.clients[1:]
        return client
        # return self.clients.get_nowait()

    def socket(self):
        return self._socket

    def return_to_client(self):
        client = self.get_first_client()
        response = self._socket.recv(RESPONSE_SIZE)
        if not response:
            return

        client.sendall(response)
        return client, response

    def id(self):
        return self._id

    def name(self):
        return self._name


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
    policy = Policy(servers)
    while 1:
        readable, _, _ = select.select(inputs, [], [])
        for s in readable:
            if s is client_socket:  # new client
                connection, client_address = s.accept()
                inputs.append(connection)  # return to select

            elif s == s1.socket():
                client, response = s1.return_to_client()
                inputs.remove(client)
                policy.server_done(s1, response)

            elif s == s2.socket():
                client, response = s2.return_to_client()
                inputs.remove(client)
                policy.server_done(s2, response)

            elif s == s3.socket():
                client, response = s3.return_to_client()
                inputs.remove(client)
                policy.server_done(s3, response)

            else:  # from old client
                request = s.recv(REQUEST_SIZE)
                if request:
                    server = policy.next(request)
                    server.handle_client(s, request)

    for server in servers:
        server.close_socket()

    client_socket.close()


class Policy(object):
    def __init__(self, servers):
        self._servers = [None, servers[0], servers[1], servers[2]]
        self._current_video_picture = 1
        self._work = [0, 0, 0, 0]
        self._max_diff = 4

    def req_type(self, request):
        return chr(request[0])

    def req_quantity(self, request):
        return int(request[1])

    def next(self, request):
        if self.req_type(request) == 'M':
            if self._work[3] > self._work[1] + self._work[2] + self._max_diff + \
                    self.real_time(self._servers[1], request):
                return self.next_video_picture(request)

            else:
                return self.next_music(request)

        else:
            if self._work[1] + self._work[2] > self._work[3] + self._max_diff + \
                    self.real_time(self._servers[3], request):
                return self.next_music(request)

            return self.next_video_picture(request)

    def server_done(self, server, response):
        self._work[server.id()] -= self.real_time(server, response)

    def next_video_picture(self, request):
        server = self._servers[self._current_video_picture]
        self._current_video_picture = 3 - self._current_video_picture
        self._work[server.id()] += self.real_time(server, request)
        return server

    def next_music(self, request):
        self._work[3] += self.real_time(self._servers[3], request)
        return self._servers[3]

    def real_time(self, server, message):
        req_type = self.req_type(message)
        req_quantity = self.req_quantity(message)
        if req_type == 'M':
            if server.id() == 1 or server.id() == 2:
                return req_quantity * 2

            else:
                return req_quantity

        if req_type == 'V':
            if server.id() == 3:
                return req_quantity * 3

            else:
                return req_quantity

        if req_type == 'P':
            if server.id() == 3:
                return req_quantity * 2

            else:
                return req_quantity


def main():
    (s1, s2, s3) = connect_to_servers()
    client_socket = create_client_socket()
    run_proxy(s1, s2, s3, client_socket)


if __name__ == '__main__':
    main()

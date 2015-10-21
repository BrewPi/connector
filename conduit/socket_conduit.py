import socket
from conduit import base

__author__ = 'mat'


class SocketConduit(base.Conduit):

    def __init__(self, sock):
        """
        :param sock: the client socket that represents the connection
        :type sock: socket
        """
        assert sock
        self.sock = sock
        self.read = sock.makefile('r')
        self.write = sock.makefile('w')

    def output(self):
        return self.write

    def input(self):
        return self.read


def client_socket_connector_factory(socket_opts, *args, **kwargs):
    """
    Factory that produces a client socket connector.
    :param socket_opts: options for constructing the socket
    :type socket_opts: tuple
    :param args: args passed to the socket connection
    :param kwargs: kwargs passed to the socket connection
    :return: a callable that creates new connections to via a client socket
    :rtype: callable
    """
    def open_socket_connector():
        sock = socket(*socket_opts)
        sock.setblocking(True)
        sock.connect(*args, **kwargs)
        return SocketConduit(sock)

    return open_socket_connector


def server_socket_connector_factory(socket_opts, *args, **kwargs):
    """
    Factory that produces a socket connector.
    :param socket_opts: options for constructing the socket
    :type socket_opts: tuple
    :param args: args passed to the socket connection
    :param kwargs: kwargs passed to the socket connection
    :return: a callable that creates new connections to via a client socket
    :rtype: callable
    """

    def open_socket_connector(*args, **kwargs):
        sock = socket(*socket_opts)
        sock.setblocking(True)
        sock.bind(*args, **kwargs)
        return SocketConduit(sock)

    return open_socket_connector(*args, **kwargs)

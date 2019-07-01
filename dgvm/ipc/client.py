# coding: utf-8
__author__ = 'salvia'

import socket
import time
import sys
import os
from .command import Command, Commands
from .protocol import BaseIPCProtocol

def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

class IPCCLientException(Exception):
    pass


def retry_on_refuse(f, retries, *args, **kwargs):
    """
    Wrapper function which retries a connection in case of ECONNREFUSED.
    :param f: wrapped function
    :param args: f args
    :param kwargs: f kwargs
    :return:
    """
    i = 0
    while True:
        try:
            i += 1
            f(*args, **kwargs)
            break
        except (OSError, socket.error) as e:
            if (e.args[0] != socket.errno.ECONNREFUSED and e.args[0] != socket.errno.EINVAL) or i > retries:
                raise
            else:
                time.sleep(0.001)


class Caller(object):
    """
    Caller is a functor which calls foreign functions on the IPC server.
    Instances of Caller are returned when one makes an attribute call on an BaseIPCClient.
    Caller holds a client reference and the name of the function requests. Upon invocation,
    Caller will serialize the function name along with any arguments and keyword arguments,
    send to the server, and await a response.
    """

    def __init__(self, client, function):
        self.client = client
        self.function = function

    def __call__(self, *args, **kwargs):

        self.client.protocol.send_message(self.client.sock, Command.FunctionCall(self.function, args, kwargs))
        result = self.client.protocol.recover_message(self.client.sock)

        return result.execute_as_client(self)


class BaseIPCClient(object):
    """
    A client to an IPC server.
    The client connects on inialization and raises IPCCLientException if the socket does not exist.
    This client is highly dynamic, since it overrides '__getattr__'. Any methods called on an
    BaseIPCClient instance will be serialized and called on the server, with the notable exception
    of the object methods and 'disconnect' which disconnects the client and 'shutdown' which
    shuts down the server (harakiri request).
    """

    protocol = BaseIPCProtocol

    def __init__(self, address=('127.0.0.1', 8998), retries=10):
        """
        Initializes a client and connect to the server, throught the given address.
        :param address: The UNIX socket path
        :return:
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        retry_on_refuse(self.sock.connect, retries, address)
        self._address = address
        self.connected = True

    def disconnect(self):
        """
        Disconnects from the server and sends a goodbye message sugnaling the server that
        this client no longer exists.
        :return:
        """
        self.connected = False
        self.protocol.send_message(self.sock, Command.Goodbye())
        data = self.protocol.recover_message(self.sock)
        self.sock.close()
        self.sock = None
        if not isinstance(data, Command) or data.command != Commands.ACK:
            raise ValueError('Server did not understood disconnection. you may be in an awry state.')

    def shutdown(self):
        """
        Requests the server to shutdown itself (harakiri request).
        :return:
        """
        self.connected = False
        self.protocol.send_message(self.sock, Command.Shutdown())
        data = self.protocol.recover_message(self.sock)
        self.sock.close()
        self.sock = None
        from server import BaseIPCServer
        pid = data.info['message']
        BaseIPCServer._processes[pid].join()
        pass

    def __getattr__(self, item):
        """
        Overriding of the get attribute operations in case an attribute is not found.
        Any method (with exception of the above defined and the object methods)
        called on an instance of BaseIPCProtocol will be serialized and send thought the socket
        as a function call request.
        :param item:
        :return:
        """
        return Caller(self, item)

    def __del__(self):
        if self.connected:
            self.disconnect()

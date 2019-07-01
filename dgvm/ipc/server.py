# coding: utf-8
__author__ = 'salvia'

from queue import Empty
from socketserver import TCPServer, StreamRequestHandler, ThreadingMixIn
from _socket import SHUT_RDWR
import socket
from functools import partial
from socket import error
from multiprocessing import Process, Value, Queue
import sys
import select
import errno
from threading import Thread
import threading
import traceback
import os

from dgvm.ipc.client import retry_on_refuse
from .protocol import BaseIPCProtocol
from .command import Command, Goodbye, Commands
import time

platform = sys.platform


class IPCAvailable(object):
    def __init__(self, ipc_server):
        self.server = ipc_server

    def __call__(self, func):

        self.server.register_functor(func)

        def wrapped(*args):
            result = func(*args)
            return result

        return wrapped


def f_startup(instance):
    instance.startup(should_fork=False)


class TCPIPCServer(object):
    daemon_threads = True
    request_queue_size = 128
    allow_reuse_address = True

    def __init__(self, ipc_server):
        self.shutdown_queue = ipc_server.shutdown_queue
        self.ipc_server = ipc_server
        self.timeout = 1
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(ipc_server.address)
        self.server_address = self.socket.getsockname()
        self.socket.listen(self.request_queue_size)
        self.handler_sockets = {}
        if platform == 'win32':
            self.pid = threading.current_thread().ident
        else:
            self.pid = os.getpid()

    def harakiri(self):
        """
        Shuts down the server from the server process itself.
        """
        self.shutdown_queue.put('SHUTDOWN')

    def shutdown(self):
        """
        Shuts down the server.
        """
        self.shutdown_queue.put('SHUTDOWN')

        try:
            self.socket.shutdown(SHUT_RDWR)
        except error:
            pass

        try:
            self.socket.close()
        except error:
            pass

    def serve_forever_(self):

        # TODO: Current threading implementation should be swapped by an event loop with async/await.

        while True:

            ppid = os.getppid()

            if ppid == 1:
                print('I Became orphaned! I cant live like this!')
                os._exit(1)

            try:
                sd = self.shutdown_queue.get(True, .001)
                if sd == 'SHUTDOWN':
                    break
            except Empty:
                pass

            fd_sets = _eintr_retry(select.select, [self.socket], [], [], self.timeout)
            if not fd_sets[0]:
                continue
                # nothing to read, try again

            try:
                request_socket, client_address = self.socket.accept()
            except socket.error:
                break

            self.handler_sockets[id(request_socket)] = request_socket

            t = Thread(target=self.handle, args=(request_socket,))
            t.daemon = True
            t.start()

        for _, sock in self.handler_sockets.items():
            sock.close()

        self.socket.close()
        if platform != 'win32':
            os._exit(0)

    def handle(self, request_socket):
        sv = self.ipc_server
        send = partial(sv.protocol.send_message, request_socket)
        while True:
            data = sv.protocol.recover_message(request_socket)

            if data is None:
                break

            if isinstance(data, Command):
                try:
                    result = data.execute_as_server(self)

                    if isinstance(result, Command):
                        send(result)

                    if data.command == Commands.FN_CALL and not isinstance(result, Command):
                        send(Command.Raise('Awry Function Call', data.info))


                except Goodbye:
                    send(Command.Ack(self.pid))
                    break
            else:
                print('Server received unknown object: %s' % (data,))

        # close connection and remove socket from handlers
        request_socket.close()
        self.handler_sockets[id(request_socket)] = request_socket

    def fn_call(self, fname, args, kwargs):
        sv = self.ipc_server

        if fname in sv._quiver:
            try:
                # good path. Funtion exists and returns an object.
                result = sv._quiver[fname](*args, **kwargs)
                return Command.FunctionCallResponse(result)
            except Exception as e:
                # function execution throws exception
                return Command.Traceback(traceback.format_exc(), str(e))
        else:
            # no such funtion
            return Command.Raise('No Such Function', fname)


class BaseIPCServer(object):
    """
    Threaded inter-process communication server. This server itself WON'T run in the process
    which initializes this class, it will run in a separate child process, so the initializer
    process (the one that instantiates this class) may do non related work.
    The child process opened, which is the server itself, will open a new thread for every client connected
    to it, and close the thread as soon as the client disconnects.

    To inherit from this, the following properties are noteworthy:
    :class attribute handler: The requisition handler class, defaults to BaseIPCHandler
     which is adequate for most scenarios.
    :class attribute protocol: The class in charge of serializing, deserializing, sending and
     retrieving information to and from the socket, defaults to BaseIPCProtocol which uses pickling.
    """

    protocol = BaseIPCProtocol
    _quiver = {}
    _processes = {}

    def __init__(self, address=('127.0.0.1', 8998)):
        """
        Initializes the server.
        :param address: (str) The unix socket file path
        :param start: (bool) Flag indicating if the server should startup rightaway.
        """
        self.address = address
        self.process = None
        self._started = False
        self.tcp_server = None
        self.ignited = Value('i', 0)
        self.shutdown_queue = Queue()

    @classmethod
    def register_functor(cls, functor, name=None):
        """
        Makes an functor available to client requests.
        If name is provided, the client will the functor through this else,
        functor.__name__ is used.
        Note: if you're registering a lambda expression make sure to pass the name argument, as lambdas are anonymous.
        :param functor: The functor to be registered.
        :param name: (optional) name which will be available to client calls.
        """
        cls._quiver[functor.__name__ if not name else name] = functor

    def wait_for_startup(self):
        a = time.time()
        while True:
            if time.time() - a > 2:
                raise IOError('IPC server failed to launch')
            with self.ignited.get_lock():
                if self.ignited.value == 1:
                    return
            time.sleep(0.001)

    def startup(self, should_fork=True):

        if should_fork:
            # win32 does not fork so memory is not copied. This is not an ideal solution but works for an MVP.
            if platform == 'win32':
                self.process = Thread(target=f_startup, args=(self,))
            else:
                self.process = Process(target=f_startup, args=(self,))

            self.process.daemon = True
            self.process.start()
            self.wait_for_startup()
            if platform == 'win32':
                BaseIPCServer._processes[self.process.ident] = self.process
            else:
                BaseIPCServer._processes[self.process.pid] = self.process
        else:
            if self._started:
                return
            self.tcp_server = TCPIPCServer(self)
            with self.ignited.get_lock():
                self.ignited.value = 1
            self._started = True
            self.tcp_server.serve_forever_()

    def shutdown(self):
        # from client import BaseIPCClient
        # c = BaseIPCClient(address=self.address)
        # c.shutdown()
        # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # retry_on_refuse(sock.connect, 10, self.address)
        self.shutdown_queue.put('SHUTDOWN')
        BaseIPCServer._processes[self.process.pid].join()

    def __enter__(self):
        self.startup()
        return self

    # for use in context managers
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# This function is present on cpython but not pypy stdlib. I've added it here for pypy compatibility.
def _eintr_retry(func, *args):
    """restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise

import unittest

import time

from dgvm.ipc.client import BaseIPCClient
from dgvm.ipc.server import BaseIPCServer


class IPCTests(unittest.TestCase):

    def test_ipc(self):
        # simple square function
        def square(x):
            return x ** 2

        def pid():
            import os
            os.getpid()

        sv = BaseIPCServer()
        sv.register_functor(square, 'square')

        sv.register_functor(pid, 'pid')

        with sv:
            client = BaseIPCClient()
            assert client.square(2) == 4
            assert client.square(3) == 9
            assert client.square(4) == 16

            client.disconnect()
            pass

        pass

    def test_performance(self):
        # simple square function
        def echo(x):
            return x ** 2

        def pid():
            import os
            os.getpid()

        sv = BaseIPCServer()
        sv.register_functor(echo, 'echo')

        with sv:

            la = time.time()
            for i in range(1000):
                echo(i)
            lb = time.time()
            print('Local took:', lb - la)

            client = BaseIPCClient()

            ra = time.time()
            for i in range(1000):
                client.echo(i)
            rb = time.time()
            print('remote took:', rb - ra)

            client.disconnect()
            pass
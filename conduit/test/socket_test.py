__author__ = 'mat'

import unittest


class ClientSocketTestCase(unittest.TestCase):
    """ functional test for the socket connectors. Creates both a server factory and a client factory, and verifies that
        data sent from one is received by the other, and that closing the socket from either end is gracefully handled."""
    pass

if __name__ == '__main__':
    unittest.main()

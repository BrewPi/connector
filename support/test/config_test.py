from support.test.config import test_config

__author__ = 'mat'

import unittest


class MyTestCase(unittest.TestCase):
    def test_something(self):
        config = test_config(self)


if __name__ == '__main__':
    unittest.main()

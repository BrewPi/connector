import unittest
from hamcrest import assert_that, equal_to
import sys
from conduit.process_conduit import ProcessConduit

# todo - these tests will need to be made OS-agnostic
from test.config import apply_module

echo_command = None
more_command = None

apply_module(sys.modules[__name__])


class ProcessConduitUnitTest(unittest.TestCase):

    def __init__(self, arg):
        super().__init__(arg)
        self.p = None

    def tearDown(self):
        if self.p is not None:
            self.p.close()

    @unittest.skipUnless(echo_command, "echo command not defined")
    def test_canCreateProcessConduitAndTerminate(self):
        self.p = ProcessConduit(echo_command)
        assert_that(self.p.open, equal_to(True))
        self.p.close()
        assert_that(self.p.open, equal_to(False))

    @unittest.skipUnless(echo_command, "echo command not defined")
    def test_canCreateProcessConduitAndReadOutputThenTerminate(self):
        p = ProcessConduit(echo_command, "123")
        lines = p.input.readline()
        self.assertEqual(lines, b"123\r\n")

    @unittest.skipUnless(more_command, "more command not defined")
    def test_canCreateProcessConduitAndSendInputOutputThenTerminate(self):
        # will read from stdin and pipe to stdout
        p = ProcessConduit(more_command)
        p.output.write(b"hello\r\n")
        p.output.flush()
        lines = p.input.readline()
        self.assertEqual(lines, b"hello\r\n")


if __name__ == '__main__':
    unittest.main()

import unittest
import time
from hamcrest import assert_that, equal_to
from conduit.process import ProcessConduit


# todo - these tests will need to be made OS-agnostic

echo_command = "cmd.exe /c echo"
more_command = "cmd.exe /c more"

class ProcessConduitUnitTest(unittest.TestCase):

    def __init__(self, arg):
        super().__init__(arg)
        self.p = None

    def tearDown(self):
        if self.p is not None:
            self.p.close()

    def test_canCreateProcessConduitAndTerminate(self):
        self.p = ProcessConduit(echo_command)
        assert_that(self.p.open, equal_to(True))
        self.p.close()
        assert_that(self.p.open, equal_to(False))

    def test_canCreateProcessConduitAndReadOutputThenTerminate(self):
        p = ProcessConduit(echo_command, "123")
        lines = p.input.readline()
        self.assertEqual(lines, b"123\r\n")

    def test_canCreateProcessConduitAndSendInputOutputThenTerminate(self):
        p = ProcessConduit(more_command)  # will read from stdin and pipe to stdout
        p.output.write(b"hello\r\n")
        p.output.flush()
        lines = p.input.readline()
        self.assertEqual(lines, b"hello\r\n")



if __name__ == '__main__':
    unittest.main()

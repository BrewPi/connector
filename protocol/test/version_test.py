import unittest
from hamcrest import assert_that, calling, raises
from protocol.version import VersionParser

# noinspection PyPep8Naming


class VersionTestCase(unittest.TestCase):

    def assertVersionEqual(self, v, major, minor, rev, versionString):
        self.assertEqual(major, v.major)
        self.assertEqual(minor, v.minor)
        self.assertEqual(rev, v.revision)
        self.assertEqual(versionString, v.version)

    def assertEmptyVersion(self, v):
        self.assertVersionEqual(v, 0, 0, 0, None)

    def newVersion(self):
        return VersionParser()

    def test_instantiatedVersionIsEmpty(self):
        v = self.newVersion()
        self.assertEmptyVersion(v)

    def test_parseSmptyStringIsEmptyVersion(self):
        v = self.newVersion()
        v.parse("")
        self.assertEmptyVersion(v)

    def test_parseNoStringIsEmptyVersion(self):
        v = self.newVersion()
        s = None
        v.parse(s)
        self.assertEmptyVersion(v)

    def test_canParseStringVersion(self):
        v = self.newVersion()
        v.parse("0.1.0")
        self.assertVersionEqual(v, 0, 1, 0, "0.1.0")

    def test_canParseJsonVersion(self):
        v = self.newVersion()
        v.parse('{"v":"0.1.0"}')
        self.assertVersionEqual(v, 0, 1, 0, "0.1.0")

    def test_canParseJsonSimulatorEnabled(self):
        v = self.newVersion()
        v.parse('{"y":1}')
        self.assertEqual(v.simulator, True)

    def test_canParseJsonSimulatorDisabled(self):
        v = self.newVersion()
        v.parse('{"y":0}')
        self.assertEqual(v.simulator, False)

    def test_canParseShieldRevC(self):
        v = self.newVersion()
        v.parse('{"s":2}')
        self.assertEqual(v.shield, VersionParser.shield_revC)

    def test_canParseBoardLeonardo(self):
        v = self.newVersion()
        v.parse('{"b":"l"}')
        self.assertEqual(v.board, VersionParser.board_leonardo)

    def test_canParseBoardStandard(self):
        v = self.newVersion()
        v.parse('{"b":"s"}')
        self.assertEqual(v.board, VersionParser.board_standard)

    def test_canParseAll(self):
        v = VersionParser('{"v":"1.2.3", "b":"l", "y":0, "s":2 }')
        self.assertVersionEqual(v, 1, 2, 3, "1.2.3")
        self.assertEqual(v.board, VersionParser.board_leonardo)
        self.assertEqual(v.simulator, False)
        self.assertEqual(v.shield, VersionParser.shield_revC)

    def test_malformed_input_raises_value_error(self):
        v = VersionParser()
        assert_that(calling(v.parse).with_args('{v:}'), raises(ValueError))


if __name__ == '__main__':
    unittest.main()

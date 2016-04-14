
import simplejson as json

class VersionParser:
    """ Parses and stores the version and other compile-time details reported by the Arduino """
    version = "v"
    build = "n"
    simulator = "y"
    board = "b"
    shield = "s"
    log = "l"

    shield_revA = "revA"
    shield_revC = "revC"

    shields = {1: shield_revA, 2: shield_revC}

    board_leonardo = "leonardo"
    board_standard = "standard"
    board_mega = "mega"

    boards = {'l': board_leonardo, 's': board_standard, 'm': board_mega}

    def __init__(self, s=None):
        self.major = 0
        self.minor = 0
        self.revision = 0
        self.version = None
        self.build = 0
        self.simulator = False
        self.board = None
        self.shield = None
        self.log = 0
        self.parse(s)

    def parse(self, s):
        if s is None or len(s) == 0:
            pass
        else:
            s = s.strip()
            if s[0] == '{':
                self.parse_json_version(s)
            else:
                self.parse_string_version(s)

    def parse_json_version(self, s):
        j = json.loads(s)
        if VersionParser.version in j:
            self.parse_string_version(j[VersionParser.version])
        if VersionParser.simulator in j:
            self.simulator = j[VersionParser.simulator] == 1
        if VersionParser.board in j:
            self.board = VersionParser.boards.get(j[VersionParser.board])
        if VersionParser.shield in j:
            self.shield = VersionParser.shields.get(j[VersionParser.shield])
        if VersionParser.log in j:
            self.log = j[VersionParser.log]
        if VersionParser.build in j:
            self.build = j[VersionParser.build]

    def parse_string_version(self, s):
        s = s.strip()
        parts = [int(x) for x in s.split('.')]
        parts += [0] * (3 - len(parts))  # pad to 3
        self.major, self.minor, self.revision = parts[0], parts[1], parts[2]
        self.version = s

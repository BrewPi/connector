import simplejson

from brewpi.datalog.beerlog import v021_columns, v010_columns

__author__ = 'mat'

import unittest
from datetime import datetime, timedelta
from hamcrest import *
from brewpi.datalog.beerlog_json import sort_and_filter_log_files, parse_datetime, BeerlogJson, BeerlogJsonRepo
import io
import fs.memoryfs


single_log_entry = "{'c':[{'v':'Date(2013,10,18,15,41,31)'},null,null,null,null,{'v':20.7},null,null,{'v':'0'}]}"


class JsonDecodeTestCase(unittest.TestCase):

    def test_regular_date(self):
        p = parse_datetime('Date(2013,11,18,15,41,31)')
        expected = datetime(2013, 12, 18, 15, 41, 31)
        assert_that(p, equal_to(expected))

    def test_month_zero(self):
        """
        the javascript notation uses 0-based months.
        """
        p = parse_datetime('Date(2013,0,1,0,0,0)')
        expected = datetime(2013, 1, 1, 0, 0, 0)
        assert_that(p, equal_to(expected))

    def test_invalid_format(self):
        self.assertRaises(
            ValueError, lambda: parse_datetime('date(2013,1,1,0,0,0)'))
        self.assertRaises(
            ValueError, lambda: parse_datetime('Dat(2013,1,1,0,0,0)'))

    def test_out_of_range(self):
        self.assertRaises(ValueError, lambda: parse_datetime(
            'Date(2013,12,1,0,0,0)'))
        self.assertRaises(ValueError, lambda: parse_datetime(
            'Date(2013,-1,1,0,0,0)'))
        self.assertRaises(ValueError, lambda: parse_datetime(
            'Date(2013,-1,1,24,0,0)'))


class LogFileListingTestCase(unittest.TestCase):

    def test_files_filtered_and_sorted(self):
        name = 'a'
        ext = '.b'
        files = [
            'a.txt',  # filtered out  - wrong extension
            'a-01-01.b',
            'b.b',   # filtered out  - wrong prefix
            'a-01-02-10.b',
            'a-01-02.b',
            'a-01-02-1.b',
            'a-01-02-2.b',
            'a',     # corner case - no extension
            'a.',    # corner case - empty extension
            '.b',    # corner case - no base name
            'a.b'   # comes first in list
        ]
        result = sort_and_filter_log_files(files, name, ext)
        assert_that(result, equal_to([
            'a.b',
            'a-01-01.b',
            'a-01-02.b',
            'a-01-02-1.b',
            'a-01-02-2.b',
            'a-01-02-10.b'
        ]))


def rows_for_log(file):
    log = BeerlogJson(file)
    return [x for x in log.rows()]


class BeerlogJsonTest(unittest.TestCase):
    pass

    def test_invalid_json_prints_file(self):
        file = lambda: io.StringIO('{abc')     # broken json
        assert_that(calling(rows_for_log).with_args(file),
                    raises(ImportError, pattern='error decoding ".*"$'))


t = datetime.now()
t -= timedelta(microseconds=t.microsecond)          # second precision
# old format with just 5 columns
d1_old = [t, 20, 10, "beer me", 5, 1, None]
d1_old_row = [t, 20, 10, "beer me", 5, 1, None,
              None, None]  # two additional elements
d1 = [t, 20, 10, "beer me", 5, 1, None, 0, 3.5]


def tovalue(v):
    """
    >>> tovalue(None) is None
    True
    >>> tovalue("abc")
    {'v': 'abc'}
    """
    return None if v is None else {"v": v}


def json_date_str(now):
    return "Date({y},{M},{d},{h},{m},{s})".format(
        y=now.year, M=(now.month - 1), d=now.day, h=now.hour, m=now.minute, s=now.second)


def dataseries_from_row(row):
    """ converts from a raw row type to the gviz json encoding """
    values = [tovalue(json_date_str(row[0]))]
    for r in row[1:]:
        values.append(tovalue(r))
    result = {"c":  values}
    return result


def build_json_file(colnames, data):
    """ creates a string representing a json file containing the data items"""
    d = {}
    # make uppercase - comparison should be case insensitive
    d['cols'] = [{'id': str(c).upper()} for c in colnames]
    d['rows'] = [dataseries_from_row(x) for x in data]
    return simplejson.dumps(d)


class BeerlogJsonRepoTest(unittest.TestCase):

    def test_enumerate_directories_as_series_names(self):
        root = fs.memoryfs.MemoryFS()
        # not really needed just be sure we can work with subpaths
        temp = root.makeopendir("temp")
        names = ["Hogwash Hefe", "Bog Fish Head", "Foaming at the mouth"]
        for n in names:
            temp.makedir(n)

        repo = BeerlogJsonRepo(temp)
        assert_that(sorted(repo.names()), equal_to(sorted(names)))

    def test_timeseries_from_jsonfiles_in_folder(self):
        """ given a "brew" directory with a single file of the format <name>-<numbers>.json containing a single entry,
            when the time series is read
            then one row is returned. the row matches the one in the file.
        """
        root = fs.memoryfs.MemoryFS()
        # not really needed just be sure we can work with subpaths
        brew = root.makeopendir("brew")
        file1 = brew.setcontents(
            "brew-01.json", build_json_file(v021_columns, [d1]))
        repo = BeerlogJsonRepo(root)
        ts = repo.fetch("brew")

        rows = [r for r in ts.rows()]
        assert_that(len(rows), is_(1), "one row timeseries expected")
        assert_that(rows[0], is_(equal_to(d1)))

    def test_timeseries_from_old_format_jsonfiles_in_folder(self):
        """ given a "brew" directory with a single file of the format <name>-<numbers>.json containing a single entry,
            when the time series is read
            then one row is returned. the row matches the one in the file.
        """
        root = fs.memoryfs.MemoryFS()
        # not really needed just be sure we can work with subpaths
        brew = root.makeopendir("brew")
        file1 = brew.setcontents(
            "brew-01.json", build_json_file(v010_columns, [d1_old]))
        repo = BeerlogJsonRepo(root)
        ts = repo.fetch("brew")

        rows = [r for r in ts.rows()]
        assert_that(len(rows), is_(1), "one row timeseries expected")
        assert_that(rows[0], is_(equal_to(
            d1_old_row)), "old format is extended with 2 additional columns, filled with None")


if __name__ == '__main__':
    unittest.main()

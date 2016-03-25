from fs.wrapfs.subfs import SubFS

__author__ = 'mat'

from datetime import datetime
from brewpi.datalog.beerlog import TimeSeries, TimeSeriesRepo, CompositeTimeSeries, select_columns, ts_columns
import simplejson as json
from fs.base import FS


class BeerlogJsonRepo(TimeSeriesRepo):

    @staticmethod
    def is_valid_name(name) -> bool:
        """
        >>> BeerlogJsonRepo.is_valid_name('.')
        False
        >>> BeerlogJsonRepo.is_valid_name('..')
        False
        >>> BeerlogJsonRepo.is_valid_name('frog wort brew 123')
        True
        """
        return name not in ('.', '..')

    def __init__(self, dir: FS):
        self.dir = dir

    def names(self) -> list:
        """ the names are the subdirectories under the repo directory """
        #names = [f for f in os.listdir(self.dir) if os.path.isdir(os.path.join(self.dir, f)) and self.is_valid_name(f)]
        names = [f for f in self.dir.listdir(
            '/', dirs_only=True) if self.is_valid_name(f)]
        return names

    def create(self, name):
        raise NotImplementedError()

    def fetch(self, name):
        basedir = self.dir.opendir(name)
        files = log_files(basedir)
        return CompositeTimeSeries(name, [BeerlogJson(delay_open(basedir, f)) for f in files])


def delay_open(fs: FS, name: str):
    def do_open():
        return fs.open(name)
    return do_open


def parse_colspec(data):
    """ fetches the column spec from the json file and extracts the ids of the columns
    >>> parse_colspec( {'blah':"abc", 'cols': [ {'id':"abc"},{'id':"def"} ] })
    ['abc', 'def']
    """
    return [x['id'] for x in data['cols']]


class BeerlogJson(TimeSeries):
    """
    Encapsulates reading beer log data from a single json file.
        :param file a file like object to read from
    """

    def __init__(self, file: callable):
        self.file_callable = file

    def __str__(self):
        with self.file_callable() as f:
            return '%s on file %s' % (self.__class__, f)

    def rows(self):
        i = 0
        try:
            with self.file_callable() as f:
                data = json.load(f)
            colspec = parse_colspec(data)
            rows = brewpi_log_rows(data)
            for r in rows:
                yield select_columns(r, colspec, ts_columns)
        except Exception as e:
            raise ImportError('error decoding "%s"' %
                              self.file_callable) from e

    def append(self, data: iter):
        raise NotImplementedError


def extract_value(value) -> (any):
    """
    Extracts a value. The value is either None or value of attribute 'v'.
    >>> extract_value(None) is None
    True
    >>> extract_value({'v':123})
    123
    """
    return None if value is None else value['v']


def brewpi_log_rows(log):
    """
    generates log data rows from a brewpi log. each entry is a list containing the raw values, or None.
    The order of the values is
    time: a datetime - in local time (without DST info)
    beerTemp: a number
    beerSet: a number
    beerAnn: a string
    fridgeTemp: a number
    fridgeSet: a number
    fridgeAnn: a string
    roomTemp: a number
    state: a number

    >>> [ x for x in brewpi_log_rows({'rows':[]})]
    []

    >>> [x for x in brewpi_log_rows( {'rows':[{'c':[  {'v':'Date(2000,1,2,3,4,5)'}, None, {'v':123}]}]})]
    [[datetime.datetime(2000, 2, 2, 3, 4, 5), None, 123]]
    """
    rows = log['rows']
    # todo - handle older format without roomTemp or state
    for row in rows:
        c = row['c']
        dt = parse_datetime(extract_value(c[0]))
        # the time is in local time (but without any DST info) - convert to UTF
        # we could look for jumps backwards or forwards within the same file to
        # determine a DST change
        data = [dt]
        data.extend([extract_value(x) for x in c[1:]])
        yield data


def parse_datetime(s) -> datetime:
    """
    Parses the brewpi json log datetime format. Note that months are 0-based (wtf?)
    :param s: the time to parse
    :type s: string
    :return: the parsed datetime
    :rtype: datetime.datetime

    >>> parse_datetime('Date(2013,11,18,15,41,31)')
    datetime.datetime(2013, 12, 18, 15, 41, 31)
    """
    # this doesn't work - won't accept month 0
    # d = datetime.strptime(s, 'Date(%Y,%m,%d,%H,%M,%S)')
    if s.startswith('Date(') and s.endswith(')'):
        # remove Date(), pull out comm-separated values
        values = [int(x) for x in s[5:-1].split(',')]
        # increment 0-based month value
        values[1] += 1
        return datetime(*values)

    raise ValueError('invalid date format: %s ' % (s))


def log_files(dir: SubFS) -> list:
    """
    Given a directory, produces a list of json files in ascending chronological order.
    :param dir:
    :type dir:
    :return:
    :rtype:
    """
    name = dir.sub_dir[1:]      # remove /
    ext = '.json'
    files = [f for f in dir.listdir() if dir.isfile(f)]
    return sort_and_filter_log_files(files, name, ext)


def sort_and_filter_log_files(files, name, ext):
    """
    The key method to sort and filter logfiles from a list containing possibly other files.

    :param files:   The files to sort
    :type files:    list(str)
    :param name:    the common prefix for log files - files not having this prefix are ignored
    :type name:     str
    :param ext:     the extension for log files - files not having this extension are ignored
    :type ext:      str
    :return:        a new list of files, sorted and filtered
    :rtype:         list(str)
    """
    file_filter = log_file_filter_factory(name, ext)
    files = [f for f in files if file_filter(f)]
    sort_log_files(files, name, ext)
    return files


def sort_log_files(files: list, name: str, ext: str):
    """ sorts logfiles into the correct processing order.
    :param files:   the filenames to sort
    :param name:    the name of the log (common prefix for all files)
    :param ext:     the extension of the files
    :return: files (sorted)
    >>> sort_log_files(['a-2012-01-2.json', 'a-2012-01-1.json', 'a-2012-01-2-10.json', 'a-2012-01-2-1.json', 'a-2012-01-2-2.json'], 'a', '.json')
    ['a-2012-01-1.json', 'a-2012-01-2.json', 'a-2012-01-2-1.json', 'a-2012-01-2-2.json', 'a-2012-01-2-10.json']
    """
    files.sort(key=log_file_key_factory(name, ext))
    return files


def strip_int_list(prefix, suffix, s) -> tuple:
    """
    strips off the prefix and suffix, and treats the remainder as a tuple of hyphen-delimited integers.
    >>> strip_int_list('abc', '.def', 'abc-10-11-12.def')
    (10, 11, 12)
    >>> strip_int_list('abc-', '.def', 'abc-10-11-12.def')
    (10, 11, 12)
    >>> strip_int_list('abc', '.def', 'abc.def')
    ()
    >>> strip_int_list('abc', '.def', 'abc-xyz.def')
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: 'xyz'
    """
    if not s.startswith(prefix) or not s.endswith(suffix):
        raise ValueError()
    if len(s) == len(prefix) + len(suffix):   # filename is exactly prefix + suffix
        return tuple()
    if not prefix.endswith('-'):
        prefix += '-'
    s = s[len(prefix):-len(suffix)]
    values = [int(x) for x in s.split('-')]
    return tuple(values)


def log_file_key_factory(prefix: str, suffix: str):
    """
    strips off the prefix and suffix, and treats the remainder as a tuple of hyphen-delimited integers.
    >>> log_file_key_factory('abc', '.def')('abc-1-2-3.def')
    (1, 2, 3)
    """
    def key(s: str):
        return strip_int_list(prefix, suffix, s)
    return key


def log_file_filter_factory(prefix: str, ext: str) -> callable(bool):
    """
    Filters files not matching the given prefix and extension
    >>> log_file_filter_factory('abc','def')('abc.def')
    True
    >>> log_file_filter_factory('abc','.def')('abc.def')
    True
    >>> log_file_filter_factory('abc.','def')('abc.def')
    False
    >>> log_file_filter_factory('ABC','def')('abc.def')
    False
    >>> log_file_filter_factory('abc','def')('abc123.def')
    True
    >>> log_file_filter_factory('abc','def')('abc123.456.def')
    True
    """
    if not ext.startswith('.'):
        ext = '.' + ext

    def filter(file: str):
        return file.startswith(prefix) and file.endswith(ext) and len(ext) + len(prefix) <= len(file)

    return filter

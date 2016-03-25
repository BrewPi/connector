from abc import abstractmethod
from datetime import datetime

__author__ = 'mat'


class TimeSeriesRepo:
    """
    A repository of beerlogs
    """
    @abstractmethod
    def names(self) -> list:
        """
        Retrieves a list of all known time series in the repo.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch(self, name):
        """
        :param name: retrieves a TimeSeries instance for the named time series.
        """
        raise NotImplementedError

    @abstractmethod
    def create(self, name):
        """
        creates a new empty time series. if a time series already exists with the same name, it is returned.
        """
        raise NotImplementedError


class TimeSeries:
    """
    A time series that directly corresponds to the brewpi 0.x data format.
    This provides an ADT for storing brewpi 0.x time series data.
    All times are recorded in milliseconds since the epoch UTC.
    """

    def range(self) -> (datetime, datetime):
        """
        :return: the start and end range for this time series. If the series is empty returns None.
        :rtype: tuple or None
        """
        r = [x for x in self.rows()]
        return None if not r else (min(x[0] for x in r), max(x[0] for x in r))

    @abstractmethod
    def rows(self):
        """
        returns an iterator to iterate over all the rows. If the series is empty returns an empty iterator.
        :return:
        :rtype:
        """
        raise NotImplementedError

    @abstractmethod
    def append(self, row: list):
        """
        inserts data into the time series. the time must be greater than the previously inserted time or a ValueError is raised.
        """
        raise NotImplementedError

    def append_bulk(self, rows: list):
        """
        Appends multiple rows on one operation. Subclasses are encouraged to override this method to make the insert more efficient.
        """
        for r in rows:
            self.append(r)

    @staticmethod
    def validate(data: list):
        """
        >>> TimeSeries.validate([datetime.now()])
        True

        >>> TimeSeries.validate([123,456]) # doctest:+ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: item in column 0 should be datetime: [123, 456]
        """
        if not isinstance(data[0], datetime):
            raise ValueError('item in column 0 should be datetime: %s' % data)
        return True


class CompositeTimeSeries(TimeSeries):
    """
    Joins several time series together
    """

    def __init__(self, name, serieses: list):
        """
        :param serieses:    multiple series (gollum)

        >>> l = [None]; c = CompositeTimeSeries("abc", l)
        >>> c.name
        'abc'
        >>> c.serieses is l
        True
        """
        self.serieses = serieses
        self.name = name

    def rows(self):
        last_time = None
        last_series = None
        row_count = 0
        for s in self.serieses:     # each series
            for i, r in enumerate(s.rows()):      # each row
                t = r[0]
                row_count += 1
                if last_time is None or last_time <= t:
                    last_time = t
                    last_series = s
                else:
                    raise ValueError('series %s: time is not ascending at row %d: '
                                     'previous time was %s from TimeSeries %s, next time is row %d:%s from TimeSeries %s'
                                     % (self.name, row_count, last_time, last_series, i, t, s))
                yield r

    def append(self, data: iter):
        self.serieses[-1].append(data)


class ListTimeSeries(TimeSeries):
    """ a simple time series implementation based on a list of rows
    """

    def __init__(self, data: list):
        self.data = data

    def rows(self):
        return self.data

    def append(self, data: iter):
        super.validate(data)
        self.data.append(data)

    def range(self) -> (datetime, datetime):
        """
        >>> ListTimeSeries([[1], [3], [20]]).range()
        (1, 20)
        >>> ListTimeSeries([]).range() is None
        True
        """
        return super().range()


def select_columns(data, columns, columns_wanted):
    """ selects from the list only those columns mentioned in cols_wanted, and returns them in the same order.
    Column names are case insensitive.
    >>> select_columns([1,2], ['a', 'B'], ['b'])
    [2]
    >>> select_columns([1,2,3], ['a','b','c'], ['B','A','D'])
    [2, 1, None]
    >>> select_columns([1], [1], [])
    []
    >>> select_columns([], ['a'], [])
    Traceback (most recent call last):
    ...
    ValueError: data and column lists not the same length: 0!=1
    """
    if len(data) != len(columns):
        raise ValueError("data and column lists not the same length: %d!=%d" % (
            len(data), len(columns)))
    d = {str(k).lower(): v for k, v in zip(columns, data)}
    return [d.get(k.lower(), None) for k in columns_wanted]


v010_columns = 'time beerTemp beerSet beerAnn fridgeTemp fridgeSet fridgeAnn'.split()
v021_columns = 'time beerTemp beerSet beerAnn fridgeTemp fridgeSet fridgeAnn state roomTemp'.split()

# the standard model
ts_columns = v021_columns

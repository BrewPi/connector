from brewpi.datalog.beerlog import ts_columns

import influxdb as influxdb
from datetime import datetime
from brewpi.datalog.beerlog import TimeSeriesRepo, TimeSeries, select_columns
from brewpi.datalog.time import uts_datetime_to_millis


class InfluxDBTimeSeriesRepo:
    pass


class InfluxDBTimeSeries(TimeSeries):

    def __init__(self, repo: InfluxDBTimeSeriesRepo, name: str, cols: list):
        """
        Creates a local representation for a time series.
        :param repo:    the time series repo this is part of
        :param name:    the name of this series. Unique in the database.
        :param cols:    a list of column names for points in this series

        >>> ts = InfluxDBTimeSeries('db', 'abc', ['time', 'c1', 'c2'])
        >>> ts.repo
        'db'
        >>> ts.name
        'abc'
        >>> ts.cols
        ['time', 'c1', 'c2']
        >>> ts.select_cols
        'c1,c2'

        >>> ts = InfluxDBTimeSeries('db', 'abc', ['c1', 'c2'])
        Traceback (most recent call last):
        ...
        ValueError: first column must be 'time'
        """
        if not cols or cols[0] != 'time':
            raise ValueError("first column must be 'time'")
        self.repo = repo
        self.name = name
        self.cols = cols
        self.select_cols = ','.join(cols[1:])

    def range(self) -> (datetime, datetime):
        return time_of(self.first_datapoint()), time_of(self.latest_datapoint())

    def _query_to_rows(self, qr):
        """ Converts a query result to rows
        """
        columns = qr['columns']
        datapoints = self._datapoints(qr)
        for dp in datapoints:
            dp = select_columns(dp, columns, self.cols)
            row = datapoint_to_row(dp)
            yield row

    def rows(self):
        qr = self._query(
            "select %(select_cols)s from %(name)s where time < now()+24h order asc")
        yield from self._query_to_rows(qr[0])

    def _create_bulk_request(self, bulkdata: list)->dict:
        """ Converts a list of rows into a json request containing multiple datapoints.
        >>> d = InfluxDBTimeSeries(None,"abc", ['time','col1','col2']). \
            _create_bulk_request([ [datetime(1970,1,2,0,0,0), 1, 2] ])
        >>> list(sorted(d.items()))       # ensure order doesn't change
        [('columns', ['time', 'col1', 'col2']), ('name', 'abc'), ('points', [[86400000, 1, 2]])]
        """
        bulk_request = self._build_json_request()
        for data in bulkdata:
            if datetime.utcnow() < data[0]:
                raise ValueError("cannot insert a time in the future")
            dp = self._row_to_datapoint(data)
            self._append_datapoint(bulk_request, dp)
        return bulk_request

    def _row_to_datapoint(self, data):
        """ converts the row to a single request format. (Converting the datetime to millis since epoch)
        >>> InfluxDBTimeSeries(None,"", ["time"])._row_to_datapoint([datetime(1970,1,2,0,0,0), 1, 2])
        [86400000, 1, 2]
        """
        time_millis = uts_datetime_to_millis(data[0])
        values = [time_millis]
        values.extend(data[1:])
        return values

    def append(self, data: list):
        self.append_bulk([data])

    def append_bulk(self, bulkdata: list):
        bulk_request = self._create_bulk_request(bulkdata)
        self.repo.insert(bulk_request)

    def latest_datapoint(self):
        """fetches the time of the latest datapoint"""
        return self.as_row(self._query('select time from %(name)s limit 1'))

    def first_datapoint(self):
        """fetches the time of the first datapoint"""
        return self.as_row(self._query('select time from %(name)s order asc limit 1'))

    def as_row(self, qr):
        """extracts the first row from the query result"""
        return self.extract_row(qr, 0)

    def extract_row(self, qr, index):
        datapoint = self._datapoints(qr)[index]
        return datapoint_to_row(datapoint)

    def _build_json_request(self):
        """
        >>> list(sorted(InfluxDBTimeSeries(None,"abc",["time",'def'])._build_json_request().items()))
        [('columns', ['time', 'def']), ('name', 'abc'), ('points', [])]
        """
        return {'name': self.name, 'columns': self.cols, 'points': []}

    def _datapoints(self, json):
        return json['points']

    def _append_datapoint(self, request, datapoint):
        """ appends a new datapoint to the request.

        >>> ts = InfluxDBTimeSeries(None,'abc',['time'])
        >>> ts._append_datapoint( {'points': [[1]] } , [2])
        {'points': [[1], [2]]}
        """
        self._datapoints(request).append(datapoint)
        return request

    def _prepare_query(self, q):
        """ substitutes the series name in the query.
        >>> InfluxDBTimeSeries(None,'bar',['time'])._prepare_query('foo %(name)s quux')
        'foo bar quux'
        >>> InfluxDBTimeSeries(None,'bar',['time', 'orange'])._prepare_query('foo %(select_cols)s %(name)s quux')
        'foo orange bar quux'
        """
        return q % self.__dict__  # noqa: H501

    def _query(self, q):
        qy = self._prepare_query(q)
        return self.repo.query(qy)


class InfluxDBTimeSeriesRepo(TimeSeriesRepo):
    """ Provides a TimeSeriesRepo implemented using the influxdb database engine.
        see http://influxdb.org
    """

    def __init__(self, host, port, user, pwd, dbname):
        self.db = influxdb.InfluxDBClient(host, port, user, pwd, dbname)

    def fetch(self, name) -> InfluxDBTimeSeries:
        """
        :param name: retrieves a TimeSeries instance for the named time series.
        """
        name = sanitize(name)
        return InfluxDBTimeSeries(self, name, ts_columns)

    def create(self, name) -> InfluxDBTimeSeries:
        return self.fetch(name)

    def names(self) -> list:
        """
         Retrieves a list of all known time series in the database.
        :return:
        """
        # todo use - select * from /.*/ limit 1
        return []

    def query(self, q):
        return self.db.query(q, 'm', chunked=False)

    def insert(self, request):
        self.db.write_points_with_precision([request], 'm')

    def delete(self, name):
        self.db.delete_points(name)


def datapoint_to_row(datapoint: list):
    """  Converts a datapoint retrieved from the database to a row, as expected by TimeSeries callers.
    >>> datapoint_to_row([86400000, 'abc', 'def'])
    [datetime.datetime(1970, 1, 2, 0, 0), 'abc', 'def']
    """
    datapoint[0] = time_of(datapoint)
    return datapoint


def sanitize(name: str):
    """
    >>> sanitize('abc')
    'abc'
    >>> sanitize('abc def')
    'abc_def'
    >>> sanitize('abc_def')
    'abc_def'
    >>> sanitize(' -()$')
    '_____'
    """
    return name.translate(str.maketrans(' -()$', '_____'))


def time_of(datapoint):
    """
    extracts a datetime from a datapoint returned by the server
    :param datapoint:
    :type datapoint:
    :return:
    :rtype:

    >>> time_of([86400000])
    datetime.datetime(1970, 1, 2, 0, 0)
    """
    return datetime.utcfromtimestamp(datapoint[0] / 1000)

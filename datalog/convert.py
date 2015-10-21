__author__ = 'mat'

"""
Eventually this will simply convert from one log format to another using providers. For now, it's hard-coded to use
the json log format as input and the influxdb as output.
"""

brewpi_test_influxdb_config = (
    'sandbox.influxdb.org', 9061, 'brewpi', 'fermentor', 'brewpi_test')

import simplejson as json
from datalog.beerlog_json import brewpi_log_rows, BeerlogJsonRepo
from datalog.influxdb.db import InfluxDBTimeSeriesRepo
from os.path import abspath
import sys
from fs.opener import fsopendir
import itertools


def import_stream(db, name, stream):
    """
    imports a stream to the database.

    :param stream:  the stream to import
    :type stream:
    """
    ts = db.timeSeries(name)
    log = json.load(stream)
    for data in brewpi_log_rows(log):
        ts.insert_row(data)


def stats(repo, name):
    series = repo.fetch(name)
    print('series "%s"\n' % name)
    print('range %s\n' % (series.range(),))
    print('datapoints %s\n' % len(list(series.rows())))
    pass


def chunker(iterable, size):
    """
    >>> [x for x in chunker([1,2,3,4,5,6,7], 3)]
    [[1, 2, 3], [4, 5, 6], [7]]
    """
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))


def main():
    if (len(sys.argv)) > 0:
        dst = InfluxDBTimeSeriesRepo(*brewpi_test_influxdb_config)
        dir = fsopendir(abspath(sys.argv[1]))
        src = BeerlogJsonRepo(dir)

        for name in sorted(src.names()):
            print('converting %s ...' % name)
            src_ts = src.fetch(name)
            dst_ts = dst.fetch(name)

            for i, row in enumerate(chunker(src_ts.rows(), 500)):
                dst_ts.append_bulk(row)
                if (i > 10):
                    break

            print('converting %s complete. Inserted %d rows into series %s. ' %
                  (name, i, dst_ts.name))

if __name__ == '__main__':
    main()

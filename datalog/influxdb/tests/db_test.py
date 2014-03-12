import os
from unittest.mock import MagicMock, Mock

__author__ = 'mat'

import unittest

from datalog.influxdb.db import *
from datetime import timedelta
from hamcrest import assert_that, is_, equal_to, has_length
import time
import datalog.convert

runInfluxDbTest = os.environ.get('TEST_INFLUXDB')

test_repo = InfluxDBTimeSeriesRepo(*datalog.convert.brewpi_test_influxdb_config)

t = datetime.utcnow()
t = t-timedelta(hours=5, microseconds=t.microsecond)    # second precision,
t2 = t - timedelta(seconds=1)                   # t1 < t2
t1 = t2 - timedelta(seconds=1)
d1 = [t1, 20, 30, "beer is good", 2, 3, "fridge is floating", 4, 23.2]
d2 = [t2, 20, 30, None, None, 3, None, 4, 23.2]

@unittest.skipUnless(runInfluxDbTest, "influx db tests disabled (check username/password)")
class InfluxDBTimeSeriesRepoTest(unittest.TestCase):
    """ a simple smoke test to verify the code. More involved tests will be done at the functional test level. """

    def list_rows(self, ts):
        rows = [x for x in ts.rows()]
        return rows

    def test_build_empty_series(self):
        ts = self.create_series()
        rows = self.list_rows(ts)
        assert_that(rows, is_(equal_to([])), "newly created series should have no rows")

    def test_append_query_single_row(self):
        """ create a new series, insert a single row and verify it appears in the returned rows. """
        ts = self.create_series()
        ts.append(d1)
        rows = self.list_rows(ts)
        assert_that(rows, is_(equal_to([d1])), "rows should contain one item")

    def test_append_query_mulitiple_row(self):
        """ create a new series, insert a single row and verify it appears in the returned rows. """
        ts = self.create_series()
        ts.append(d1)
        ts.append(d2)
        rows = self.list_rows(ts)
        assert_that(len(rows), is_(equal_to(2)), "inserted 2 rows")
        assert_that(rows[0], is_(equal_to(d1)), "first row should be like d1")
        assert_that(rows[1], is_(equal_to(d2)), "second row should be like d2")

    def test_append_bulk(self):
        ts = self.create_series()
        # mock the insert method so we can see that the bulk insert is done with one query
        m = Mock(wraps=ts.repo)
        ts.repo = m
        insert = [d1,d2]
        ts.append_bulk(insert)
        assert_that(m.insert.mock_calls, has_length(1), "expeecting insert to be called just one")
        # verify the result just to be sure
        rows = self.list_rows(ts)
        assert_that(rows, is_(equal_to(insert)), "rows should match inserted rows")


    def create_series(self):
        # test_repo.delete("test_series") # delete is not implemented by the service
        name = "test_series_%d" % int(round(time.time() * 1000))
        return test_repo.create(name)



if __name__ == '__main__':
    unittest.main()

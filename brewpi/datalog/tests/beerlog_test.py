from unittest.mock import Mock, call

import unittest
from brewpi.datalog.beerlog import ListTimeSeries, CompositeTimeSeries, TimeSeries
from hamcrest import equal_to, is_, assert_that, calling, raises, none
from datetime import datetime, timedelta


class CompositeTimeSeriesTest(unittest.TestCase):

    def test_all_empty(self):
        """ given a composite of 2 empty series, when the rows are fetched, then the composite is empty """
        s1 = ListTimeSeries([])
        s2 = ListTimeSeries([])
        c = CompositeTimeSeries("abc", [s1, s2])
        rows = [r for r in c.rows()]
        assert_that(rows, is_(equal_to([])))

    def test_items_in_order(self):
        """ given a composite of two 1-item series, when the rows are fetched, then the composite returns
            the item from the first series followed by the second. """
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        s1 = ListTimeSeries([[t1, 123]])
        s2 = ListTimeSeries([[t2, 456]])
        c = CompositeTimeSeries("abc", [s1, s2])
        rows = [r for r in c.rows()]
        assert_that(rows, is_(equal_to([
            [t1, 123], [t2, 456]
        ])))

    def test_items_out_of_order_raises_ValueError(self):
        """ given two series made into a composite, when the series produce non-increasing time then
        a ValueError is thrown"""
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        s1 = ListTimeSeries([[t2, 123]])
        s2 = ListTimeSeries([[t1, 456]])
        c = CompositeTimeSeries("abc", [s1, s2])
        rows = c.rows()
        assert_that(next(rows), is_(
            equal_to([t2, 123])), 'first row should be returned')
        assert_that(calling(lambda: next(rows)), raises(ValueError),
                    'second row has an earlier time so should raise ValueError')


class TimeSeriesTest(unittest.TestCase):

    def test_empty_range_returns_none(self):
        ts = TimeSeries()
        ts.rows = Mock(return_value=[])
        assert_that(ts.range(), is_(none()))

    def test_append_raises_NotImplementedError(self):
        ts = TimeSeries()
        assert_that(calling(lambda: ts.append(
            [1])), raises(NotImplementedError))

    def test_append_bulk_calls_append(self):
        # given
        ts = TimeSeries()
        ts.append = Mock()      # override append method, which would throw NotImplementedError
        # when
        ts.append_bulk([[x] for x in range(0, 3)])
        # then
        expected_calls = [call([x]) for x in range(0, 3)]
        assert_that(ts.append.mock_calls, is_(equal_to(expected_calls)))


if __name__ == '__main__':
    unittest.main()

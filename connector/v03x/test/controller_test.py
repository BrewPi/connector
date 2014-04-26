from hamcrest import assert_that, is_
from connector.v03x.controller import fetch_dict

__author__ = 'mat'

import unittest


class FetchDictTestCase(unittest.TestCase):
    def test_fetch_not_exist(self):
        d = dict()
        result = fetch_dict(d, 123, lambda x: x+1)
        assert_that(result, is_(124))

    def test_fetch_exist(self):
        d = dict()
        d[123] = "abc"
        result = fetch_dict(d, 123, lambda x: x/0)
        assert_that(result, is_("abc"))



__author__ = 'mat'

import configobj

def test_config(test):
    """fetches the configuration object for the given test."""
    name = test.__qualname__



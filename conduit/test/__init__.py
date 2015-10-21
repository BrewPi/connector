import sys
from test.config import apply_package

__author__ = 'mat'


def setup_package():
    apply_package(sys.modules[__name__])

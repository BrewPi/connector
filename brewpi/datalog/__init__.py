"""
A simple bare-bones abstraction of the 0.x brewpi logging format. The number of columns in the logging is fixed to one
 chamber and one beer.

 This module is pretty much obsolete. It was coded for a developer that was going to work on producing
 graphs from influxdb, so I coded this so real data could be imported. The graphs were never produced.
 However, I'm keeping this around as it may be useful to import brewpi 2.x data into 3.x.
"""

from pkg_resources import declare_namespace

declare_namespace(__name__)

__author__ = 'mat'

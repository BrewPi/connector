"""
The brewpi connector - this package contains the parts that seeks out controllers running the brewpi
software, and provides a programming interface to access them.

These subpackages exist:

datalog: some old code to import legacy brewpi json logs into influx db


"""
from pkg_resources import declare_namespace

declare_namespace(__name__)

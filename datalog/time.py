from datetime import datetime
import time
import calendar

__author__ = 'mat'


def uts_datetime_to_millis(dt:datetime):
    """
    converts a datetime to milliseconds since the epoch.
    >>> uts_datetime_to_millis(datetime(1970,1,1,0,0,0,750999))
    750
    >>> uts_datetime_to_millis(datetime(1970,1,2,0,0,0,750999))
    86400750
    """
    # a lot of sources say to use time.mktime() but this will convert using
    # the local timezone. For anyone east of the meridian, the epoch will be negative time.
    # calender.timegm works on unicode time.
    millis_since_epoch = int(calendar.timegm(dt.utctimetuple())*1000 + (dt.microsecond/1000))
    return millis_since_epoch



def local_datetime_to_millis(dt:datetime):
    """
    Converts a datetime in local time to a datetime in UTC
    >>> local_datetime_to_millis(datetime(1970,1,2,0,0,0))-timezone_utc_offset()
    86400000
    """
    secs_since_epoch = time.mktime(dt.utctimetuple())
    result = int((secs_since_epoch * 1000) + (dt.microsecond/1000))
    return result

def timezone_utc_offset():
    """
    retrieves the current utc offset in milliseconds. The UTC offset is the value that has to be added to
    local time to arrive at UTC time.
    :return the UTC offset in milliseconds
    """
    return time.timezone*1000








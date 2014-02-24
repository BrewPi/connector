"""
   Attempts to open a given connector via a factory function.
"""

import logging

logger = logging.getLogger(__name__)


def open_connector(factory, consumer):
    """
    Attempts to obtain a connection from the factory and passes it to the consumer.
    :param factory: the factory method to open a new connector
    :type factory: callable
    :param consumer:the consumer (a callable) that is passed the connector once opend.
    :type consumer:
    :return the connector created from the factory or None if an error occurred
    """
    connector = None
    try:
        connector = factory()
    except Exception as e:
        # todo - this should really be trace level log
        logger.log(1, "unable to open connector: %s", e)
    else:
        logger.info("opened connector %s", connector)
        if consumer:
            connector = consumer(connector)
    return connector


__author__ = 'mat'

[![Build Status](https://travis-ci.org/BrewPi/connector.svg?branch=master)](https://travis-ci.org/BrewPi/connector)

The Connector provides a remote interface to controller hardware. It builds on top of the controlbox package to
provide access to remote objects running in the container.


## install

### General
    sudo apt install python3.6 python3.6-dev
    mkvirtualenv --python=`which python3.6` connector
    pip install -r requirements.txt

### Test
    pip install -r requirements-test.txt

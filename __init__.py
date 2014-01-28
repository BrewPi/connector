
"""
Install steps
- download python 3 and install to a new directory e.g. c:\python\python33
- In PyCharm, open a console and type "set path=c:\python\python33;%path%"
- download http://pypi.python.org/pypi/distribute/0.6.27 and run with python (python
- download https://raw.github.com/pypa/pip/master/contrib/get-pip.py and run with python
- run "pip install virtualenv"
- run "virtualenv brewpi2" to create a new virtualenv for brewpi
- run "brewpi2\scripts\activate" to activate
    - subsequent packages that are installed for brewpi use are not global

- run "easy_install sphinx" to install documentation generator (setuptools, that provides easy_install, was installed automatically by distribute earlier)


for eclipse CDT
- install mingw
- add to system path %mingw%\bin, and %mingw%\msys\1.0\bin (this is needed for the 'rm' command)
- if after running the test cases, you don't see console output, add PATH to executable environment
    http://stackoverflow.com/questions/3443254/eclipse-cdt-using-mingw-does-not-output-in-console


Technologies for webapp
- STOMP - logical messaging layer above web sockets - http://stomp.github.io/index.html
- SocksJS - websocket browser abstraction
- KnockoutJS - MVVM binding
- http://dailyjs.com/2013/02/04/stack/

"""

__author__ = 'mat'

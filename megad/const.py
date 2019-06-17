import typing
from collections import namedtuple
from functools import partial
from logging import getLogger

_MapKey = typing.TypeVar('_MapKey')
DIR_UP = 1
DIR_DOWN = 0
MAX_P_TIME = 0.25
InputQuery = namedtuple('InputQuery', ['pt', 'click', 'cnt', 'm'], defaults=[0]*4)

"""
These are preconfigured InputQueries, that can be used like this BTN_PRESS(1) where 1 is port number
"""
BTN_PRESS: typing.Callable[[], InputQuery] = partial(InputQuery, m=0)
BTN_RELEASE: typing.Callable[[], InputQuery] = partial(InputQuery, m=1)
BTN_RELEASE_AFTER_LONG: typing.Callable[[], InputQuery] = partial(InputQuery, m=1, cnt=3)
BTN_LONG_PRESS: typing.Callable[[], InputQuery] = partial(InputQuery, m=2, cnt=3)
BTN_DOUBLE_CLICK: typing.Callable[[], InputQuery] = partial(InputQuery, m=2, cnt=2)
BTN_SINGLE_CLICK: typing.Callable[[], InputQuery] = partial(InputQuery, click=1, cnt=1)

lg = getLogger('megad_api')
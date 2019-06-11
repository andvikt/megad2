"""
Центральный класс - Mega отвечает за коммуникацию с устройством, по сути это просто контейнер с ip-адресом и оберткой над
requests с обеспечением необходимой блокировки на время выполнения запроса
"""

import aiohttp
from aiohttp import web
import typing
import asyncio
from urllib.parse import urlencode
from collections import namedtuple
from logging import getLogger, basicConfig
import attr
from functools import partial

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

_MapKey = typing.TypeVar('_MapKey')

DIR_UP = 1
DIR_DOWN = 0
MAX_P_TIME = 0.25

InputQuery = namedtuple('InputQuery', ['pt', 'click', 'cnt', 'm'], defaults=[0]*4)
lg = getLogger('megad_api')

class MegaException(Exception):
    pass

class Unauthorised(MegaException):
    pass

def make_query(query: dict):
    return '&'.join([f'{x}={y}' for x, y in query.items()])


class _MapCallback(typing.Generic[_MapKey]):

    cb_map: typing.Dict[_MapKey, typing.Callable[[_MapKey], ...]]

    def map_callback(self, key: _MapKey, foo):
        if key in self.cb_map:
            raise KeyError(f'{key} already registered')
        self.cb_map[key] = foo
        return foo

    def map_callback_deco(self, key: InputQuery):
        def deco(foo):
            return self.map_callback(key, foo)
        return deco


class Mega(_MapCallback[InputQuery]):

    def __init__(self
                 , host
                 , cb_map: typing.Mapping[InputQuery, typing.Callable[[InputQuery], typing.Any]] = None):
        """

        :param host: ip-address of mega (without http part)
        :param cb_map: callbacks to call on incoming events
        """
        self._host = host
        self.lck = asyncio.locks.Lock()
        self.cb_map = cb_map or {}
        # asyncio.ensure_future(self.start_listen(port_listen))

    async def request(self, *, wait=None, **kwargs):
        async with self.lck:
            url = f'http://{self._host}?{make_query(kwargs)}'
            lg.debug(f'request {url}, wait {wait}')
            async with aiohttp.request('get', url=url) as req:
                ret = await req.text()
                if ret == 'Unauthorized':
                    raise Unauthorised(f'Unauthorised {self._host}')
                if wait:
                    await asyncio.sleep(wait)
                lg.debug(f'response "{ret}" to {url}')
                return ret

    async def handle(self, req: web.Request):
        query = InputQuery(**{x: int(y) for x, y in req.query.items()})
        lg.debug(f'handle request {query}')
        cb = self.cb_map.get(query)
        if not cb is None:
            if asyncio.iscoroutinefunction(cb):
                asyncio.ensure_future(cb(query))
            else:
                cb(query)
        return web.Response(text='OK')


    async def start_listen(self, port):
        """
        Start listen port for incoming messages
        :return:
        """
        server = web.Server(self.handle)
        runner = web.ServerRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        lg.info(f'Mega-d listener started on port {port}')


class Relay(object):
    """
    Базовое реле - вкл, выкл
    """
    def __init__(self, mega: Mega, port, reverse:bool = False):
        self.mega = mega
        self.port = port
        self.reverse=reverse

    async def turn_on(self):
        await self.mega.request(pt=self.port, cmd=f'{self.port}:{int(not self.reverse)}')

    async def turn_off(self):
        await self.mega.request(pt=self.port, cmd=f'{self.port}:{int(self.reverse)}')

    async def turn_on_and_off(self, time:int):
        p = round(abs(time*10))
        await self.mega.request(pt=self.port
                                , wait=time+0.1
                                , cmd=f'{self.port}:{int(not self.reverse)};p{p};{self.port}:{int(self.reverse)}')


@attr.s
class Servo(object):
    """
    Серво-привод на двух реле
    Во время движения блокирует всю мегу, на старте калибруется путем полного прогона в закрытое состояние,
        и не доступно для управления пока не закончится калибровка, по завершении калибровки вызывается калибровочный
        кол-бэк (в нем можно например вызвать установку текущего значения)

    :param move_rel: реле для движения
    :param dir_rel: реле для выбора направления
    :param close_time: время закрытия
    :param calibrate: если True, инициировать калибровку сразу после создания
    :param calibrated_cb: колбэк, вызывается по завершении калибровки
    :param value_set_cb: колбэк, вызывается по завершении работы привода с новым значением текущего положения
        в качестве параметра (можно использовать для уведомления сервера о новом положении привода)
    """
    move_rel: Relay = attr.ib()
    dir_rel: Relay = attr.ib()
    close_time: int = attr.ib()
    _calibrate: bool = attr.ib(default=True)
    calibrated_cb: typing.Callable = attr.ib(default=None)
    value_set_cb: typing.Callable = attr.ib(default=None)
    mega: Mega = attr.ib(default=None)
    _value: float = 0
    lck: asyncio.Lock = attr.ib(factory=asyncio.Lock, init=False)

    def __attrs_post_init__(self):
        if isinstance(self.move_rel, int):
            self.move_rel = Relay(self.mega, self.move_rel)
        if isinstance(self.dir_rel, int):
            self.move_rel = Relay(self.mega, self.dir_rel)
        if self._calibrate:
            asyncio.ensure_future(self.calibrate())

    @property
    def value(self):
        """
        Current servo position in percents (0 to 1)
        :return:
        """
        return self._value

    async def calibrate(self):
        async with self.lck:
            await self.dir_rel.turn_off()
            await self.move_rel.turn_on()
            await asyncio.sleep(self.close_time + 1)
            if self.calibrated_cb:
                self.calibrated_cb()

    async def set_value(self, value):
        assert 0 <= value <= 1, 'new value of servo must be between 0 and 1'
        async with self.lck:
            p_value = (value - self._value) * self.close_time
            if p_value > 0:
                await self.dir_rel.turn_on()
            else:
                await self.dir_rel.turn_off()
            await self.move_rel.turn_on()
            await self.move_rel.turn_on_and_off(abs(p_value))
            self._value += round(p_value * 10) / (self.close_time * 10)
            if self.value_set_cb is not None:
                if asyncio.iscoroutinefunction(self.value_set_cb):
                    asyncio.ensure_future(self.value_set_cb(self._value))
                else:
                    self.value_set_cb(self._value)


class OneWireBus(object, _MapCallback[str]):

    def __init__(self, mega: Mega, port: int, cb_map: typing.Mapping[str, typing.Callable[[float], typing.Any]] = None):
        """
        Обновление температуры, по обновлению вызывается колбэк из словаря cb
        :param mega:
        :param port: порт на котором зарегистрирована шина
        :param cb_map: мэппинг callback-ов на обновление температуры
            ключи - адрес датчика, колбэк должен принимать на вход float - это значение текущей температуры
        """
        self.mega = mega
        self.port = port
        self.cb_map = cb_map or {}

    async def update(self):
        await self.mega.request(pt=self.port, cmd='conv')
        while True:
            await asyncio.sleep(1)
            txt = await self.mega.request(pt=self.port, cmd='list')
            lg.debug(f'Update temp recieved: {txt}')
            if txt != 'Busy':
                break

        for x in txt.split(';'):
            key, temp = x.split(':')
            temp = float(temp)
            if key in self.cb_map:
                foo = self.cb_map[key]
                if asyncio.iscoroutinefunction(foo):
                    asyncio.ensure_future(foo(temp))
                else:
                    foo(temp)

class SpeedSelect(object):

    def __init__(self, mega: Mega, pins: typing.List[int]):
        self.pins = pins
        self.mega = mega

    async def set_value(self, value):
        assert 0<=value<=len(self.pins), f'can not set {value}'
        await self.mega.request(pt=self.pins[0], cmd=';'.join([f'{x}:0' for x in self.pins]))
        if value > 0:
            await self.mega.request(pt=self.pins[value-1], cmd=f'{self.pins[value-1]}:1')

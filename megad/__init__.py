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
from logging import getLogger

DIR_UP = 1
DIR_DOWN = 0
MAX_P_TIME = 0.25

InputQuery = namedtuple('InputQuery', ['pt', 'click', 'cnt', 'm'], defaults=[0]*4)
lg = getLogger(__name__)

class MegaException(Exception):
    pass

class Unauthorised(MegaException):
    pass

class Mega(object):

    def __init__(self
                 , host
                 , port_listen: int = None
                 , cb_map: typing.Mapping[InputQuery, typing.Callable[[InputQuery], typing.Any]] = None):
        """

        :param host: ip-address of mega (without http part)
        :param port_listen: port to listen for incoming messages
        :param cb_map: callbacks to call on incoming events
        """
        self._host = host
        self.lck = asyncio.locks.Lock()
        self.cb_map = cb_map or {}
        self.port_listen = port_listen
        asyncio.ensure_future(self.start_listen(port_listen))

    async def request(self, *, wait=None, **kwargs):
        async with self.lck:
            url = f'http://{self._host}?{urlencode(kwargs)}'
            lg.debug(f'request {url}')
            async with aiohttp.request('get', url=url) as req:
                if wait:
                    await asyncio.sleep(wait)
                ret = await req.text()
                if ret == 'Unauthorized':
                    raise Unauthorised(f'Unauthorised {self._host}')
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
    def __init__(self, mega, port, reverse:bool = False):
        self.mega = Mega
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


class Servo(object):
    """
    Серво-привод на двух реле
    Во время движения блокирует всю мегу
    """
    def __init__(self, move_rel: Relay, dir_rel: Relay, close_time: int, calibrated_cb: typing.Callable = None):
        """

        :param move_rel: реле для движения
        :param dir_rel: реле для выбора направления
        :param close_time: время закрытия
        :param calibrated_cb: колбэк, вызывается по завершении калибровки
        """
        self.move_rel = move_rel
        self.dir_rel = dir_rel
        self.close_time = close_time
        self.value = 0
        self.calibrated_cb = calibrated_cb
        asyncio.ensure_future(self.calibrate())

    async def calibrate(self):
        await self.dir_rel.turn_on()
        await self.move_rel.turn_on()
        await asyncio.sleep(self.close_time + 1)
        await self.dir_rel.turn_off()
        await asyncio.sleep(self.close_time + 1)
        self.calibrated_cb()

    async def set_value(self, value):
        p_value = ((self.value - value) / 100) * self.close_time
        if p_value > 0:
            await self.dir_rel.turn_on()
        else:
            await self.dir_rel.turn_off()
        await self.move_rel.turn_on()
        await self.move_rel.turn_on_and_off(p_value)


class OneWireBus(object):

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

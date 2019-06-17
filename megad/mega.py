import asyncio
import typing

import aiohttp
from aiohttp import web

from .mixins import _MapCallback
from .const import lg, InputQuery
from .utils import make_query, make_server, AppContainer


class MegaException(Exception):
    pass


class Unauthorised(MegaException):
    pass


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
        self._app: AppContainer = AppContainer(host='localhost')
        self._app.get('/')(self.handle)
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
        """
        Handle input from megad
        :param req:
        :return:
        """
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
        self._app.port = port
        await self._app.start()
        lg.info(f'Mega-d listener started on port {port}')

    async def stop(self):
        await self._app.stop()
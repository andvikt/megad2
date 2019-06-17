import asyncio
import typing

from .const import lg
from .mixins import _MapCallback
from .mega import Mega


class OneWireBus(_MapCallback[str]):

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
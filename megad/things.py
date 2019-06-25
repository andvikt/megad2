import asyncio
import typing

import attr

from .mega import Mega


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
    move_rel: typing.Union[Relay, int] = attr.ib()
    dir_rel: typing.Union[Relay, int] = attr.ib()
    close_time: int = attr.ib()
    to_calibrate: bool = attr.ib(default=True)
    calibrated_cb: typing.Callable = attr.ib(default=None)
    value_set_cb: typing.Callable = attr.ib(default=None)
    mega: Mega = attr.ib(default=None)
    _value: float = 0
    lck: asyncio.Lock = attr.ib(factory=asyncio.Lock, init=False)

    def __attrs_post_init__(self):
        if isinstance(self.move_rel, int):
            self.move_rel = Relay(self.mega, self.move_rel)
        if isinstance(self.dir_rel, int):
            self.dir_rel = Relay(self.mega, self.dir_rel)
        if self.to_calibrate:
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
            if asyncio.iscoroutinefunction(self.calibrated_cb):
                await self.calibrated_cb()
            elif isinstance(self.calibrated_cb, typing.Callable):
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


class SpeedSelect(object):

    def __init__(self, mega: Mega, pins: typing.List[int]):
        self.pins = pins
        self.mega = mega

    async def set_value(self, value):
        assert 0<=value<=len(self.pins), f'can not set {value}'
        await self.mega.request(pt=self.pins[0], cmd=';'.join([f'{x}:0' for x in self.pins]))
        if value > 0:
            await self.mega.request(pt=self.pins[value-1], cmd=f'{self.pins[value-1]}:1')
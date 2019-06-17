from pytest import fixture, yield_fixture
import pytest
import asyncio
from megad import Mega, utils, const, OneWireBus
from megad.things import Relay, Servo, SpeedSelect
from aiohttp.web import Application, run_app, RouteTableDef, Request, Response
import aiohttp
import datetime
from functools import wraps
import typing

async def timer(foo: typing.Coroutine):

    start = datetime.datetime.now()
    await foo
    return (datetime.datetime.now() - start).total_seconds()

@fixture()
async def fake_mega():
    que = asyncio.Queue()

    async def handle(request: Request):
        await que.put(request.query_string)
        if request.query.get('cmd') == 'list':
            return Response(text='test_addr_1:25.5;test_addr_2:27.2')
        return Response(status=200, text='OK')

    srv, site = await utils.make_server(handle, 1111)
    yield que
    await site.stop()


@yield_fixture(scope='module')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@fixture(scope='module')
async def mega():
    mega = Mega('localhost:1111')
    yield mega

@fixture(scope='module')
async def client(mega):
    async with mega._app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_rel(mega, fake_mega):
    rel = Relay(mega, 1)
    await rel.turn_on()
    assert await fake_mega.get() == 'pt=1&cmd=1:1'
    await rel.turn_off()
    assert await fake_mega.get() == 'pt=1&cmd=1:0'
    await rel.turn_on_and_off(1)
    assert await fake_mega.get() == 'pt=1&cmd=1:1;p10;1:0'
    done, notdone = await asyncio.wait([utils.cancelok(rel.turn_on_and_off)(10)], timeout=1)
    assert await fake_mega.get() == 'pt=1&cmd=1:1;p100;1:0'
    assert len(notdone) > 0



@pytest.mark.asyncio
async def test_temperature(mega, fake_mega):

    ow = OneWireBus(mega, port=32)
    ev1 = asyncio.Event()
    ev2 = asyncio.Event()

    @ow.map_callback_deco('test_addr_1')
    def ptint_temp(t):
        assert t == 25.5
        ev1.set()

    @ow.map_callback_deco('test_addr_2')
    def ptint_temp(t):
        assert t == 27.2
        ev2.set()

    await ow.update()
    ret = await fake_mega.get()
    assert ret == 'pt=32&cmd=conv'
    ret = await fake_mega.get()
    assert ret == 'pt=32&cmd=list'
    await ev1.wait()
    await ev2.wait()


@pytest.mark.asyncio
async def test_btns(mega, client):
    pressed = asyncio.Event()

    @mega.map_callback_deco(const.BTN_DOUBLE_CLICK(1))
    async def tst(*args):
        pressed.set()

    await client.request('get', f'/?{utils.make_query(const.BTN_DOUBLE_CLICK(1))}')
    await pressed.wait()


@pytest.mark.asyncio
async def test_servo(mega, fake_mega):
    calibrated = asyncio.Event()
    calibrated_event = asyncio.Event()
    value_set_event = asyncio.Event()

    async def set_cb():
        calibrated_event.set()

    async def an_set_cb(val):
        value_set_event.set()

    servo = Servo(
          mega=mega
          , dir_rel=16
          , move_rel=17
          , close_time=2
          , calibrated_cb=set_cb
          , value_set_cb=an_set_cb)

    await calibrated_event.wait()
    tm = await timer(servo.set_value(0.5))
    assert round(tm, 1) in [1.1, 1.2]
    tm = await timer(servo.set_value(0.25))
    assert round(tm, 1) == 0.6
    await value_set_event.wait()


@pytest.mark.asyncio
async def test_speed(mega, fake_mega):
    speed = SpeedSelect(mega, [3,4,5,6])
    await speed.set_value(0)
    data = await fake_mega.get()
    assert data == 'pt=3&cmd=3:0;4:0;5:0;6:0'
    await speed.set_value(2)
    data = await fake_mega.get()
    data = await fake_mega.get()
    assert data == 'pt=4&cmd=4:1'
    with pytest.raises(AssertionError) as err:
        await speed.set_value(5)
    err.match("can not set 5")

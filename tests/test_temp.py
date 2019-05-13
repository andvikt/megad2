from logging import basicConfig, DEBUG
import aiohttp

basicConfig(level=DEBUG)

from megad import Mega, InputQuery, OneWireBus
import asyncio

async def test_click(t):
    print('test click', t)

mega = Mega(
    '192.168.0.14/sec/'
    , 9191
    , {
        InputQuery(pt=1, m=1): test_click
    }
)
ow = OneWireBus(mega, port=14)

async def main():
    await ow.update()

asyncio.get_event_loop().run_until_complete(main())

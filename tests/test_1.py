from logging import basicConfig, DEBUG
import aiohttp

basicConfig(level=DEBUG)

from megad import Mega, InputQuery
import asyncio

async def test_click(t):
    print('test temp', t)

mega = Mega(
    '192.168.0.14/sec/'
    , {
        InputQuery(pt=1, m=1): test_click
    }
)


async def main():
    await mega.start_listen(9191)
    async with aiohttp.request('get', 'http://localhost:9191/?pt=1&m=1') as req:
        await req.text()
    while True:
        await asyncio.sleep(10000)

asyncio.get_event_loop().run_until_complete(main())

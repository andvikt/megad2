from logging import basicConfig, DEBUG
import aiohttp

basicConfig(level=DEBUG)

from megad import Mega, InputQuery, OneWireBus
import asyncio

async def print_temp(t):
    print('test click', t)

mega = Mega(
    '192.168.0.14/sec/'
    , 9191
)
ow = OneWireBus(mega, port=14, cb_map={
    'ffd9da801704': print_temp
})

async def main():
    await ow.update()

asyncio.get_event_loop().run_until_complete(main())
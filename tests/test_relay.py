from logging import basicConfig, DEBUG

basicConfig(level=DEBUG)

from megad import Mega, Relay
import asyncio


mega = Mega('192.168.0.14/sec/')
relay = Relay(mega=mega, port=11)

async def main():
    await relay.turn_off()
    await relay.turn_on()
    await relay.turn_on_and_off(10)

asyncio.get_event_loop().run_until_complete(main())
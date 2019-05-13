from logging import basicConfig, DEBUG
import aiohttp

basicConfig(level=DEBUG)

from megad import Mega, Servo, Relay
import asyncio

def print_calibrated():
    print('calibrated')

def print_new_value(v):
    print(f'new value {v}')

mega = Mega('192.168.0.14/sec/')
servo = Servo(dir_rel=Relay(mega, 15)
              , move_rel=Relay(mega, 15)
              , close_time=12
              , calibrated_cb=print_calibrated
              , value_set_cb=print_new_value)


async def main():
    await servo.calibrate()
    await servo.set_value(.5)

asyncio.get_event_loop().run_until_complete(main())
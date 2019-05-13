 # Simple integration for mega-d
 
 Интеграция с устрйоством MegaD-2561 от ab-log.ru
 Полностью асинхронная (aiohttp)
 Может работать как микро-сервер (метод start_listen)
 
 Реакция на команды от меги реализована через словарь, в котором ключ - это значение передаваемой команды от меги 
 (InputQuery), а значения - любая функция или асинхронная функция, например:
 ```python
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

```

Управление реле осуществляется с помощью класса Relay:
```python
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
```

В модуле так же реализован класс Servo для управления серво-приводами на двух реле.
```python
from logging import basicConfig, DEBUG

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
```

Так же реализован класс OneWire для обновления температуры из шины OneWire
При обновлении температуры вызывается колбэк из словаря колбэков, в котором ключ - адрес onewire, значение - колбэк
```python
from logging import basicConfig, DEBUG

basicConfig(level=DEBUG)

from megad import Mega, OneWireBus
import asyncio

async def print_temp(t):
    print('test click', t)

mega = Mega('192.168.0.14/sec/')
ow = OneWireBus(mega, port=14, cb_map={
    'ffd9da801704': print_temp
})

async def main():
    await ow.update()

asyncio.get_event_loop().run_until_complete(main())
```

Чтобы обновлять температуру периодически можно воспользоваться стандартными методами, например так:
```python
# регулярное обновление

async def reg_update(interval):
    await asyncio.sleep(interval)
    await ow.update()
    asyncio.ensure_future(reg_update(interval))
```
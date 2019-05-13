 # Simple integration for mega-d
 
 Интеграция с устрйоством MegaD-2561 от ab-log.ru
 Полностью асинхронная (aiohttp)
 Может работать как микро-сервер, стартуется автоматически при инициализации класса Mega если указать port_listen
 
 Реакция на команды от меги реализована через словарь, в котором ключ - это значение передаваемой команды от меги 
 (InputQuery), а значения - любая функция или асинхронная функция, например:
 ```python
from logging import basicConfig, DEBUG
import aiohttp

basicConfig(level=DEBUG)

from megad import Mega, InputQuery
import asyncio

# эта функция будет вызываться когда от меги придет запрос
async def test_click(t: InputQuery):
    print('test temp', t)

mega = Mega(
    '192.168.0.14/sec/'
    , 9191
    , {
        InputQuery(pt=1, m=1): test_click # функция будет вызвана только в случае если в запросе будет pt=1 и m=1
    }
)


async def main():
    # имитация запроса от меги, на практике в меге нужно в качестве сервера указать ip:port
    async with aiohttp.request('get', 'http://localhost:9191/?pt=1&m=1') as req:
        await req.text()
    # спим бесконечно долго и ждем запросы от меги
    while True:
        await asyncio.sleep(10000)

asyncio.get_event_loop().run_until_complete(main())
```

Управление реле осуществляется с помощью класса Relay:
```python

```
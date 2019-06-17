from aiohttp import web, test_utils
import typing
import asyncio
import functools
from .const import InputQuery
import attr


@attr.s
class AppContainer:

    host: typing.Optional[str] = attr.ib(default=None)
    port: typing.Optional[int] = attr.ib(default=None)
    _app: web.Application = attr.ib(factory=web.Application)
    _route: web.RouteTableDef = attr.ib(factory=web.RouteTableDef, init=False)

    appRunner = attr.ib(type=web.AppRunner)
    @appRunner.default
    def app_runner(self):
        return web.AppRunner(self._app)

    site = attr.ib(type=web.TCPSite)
    @site.default
    def site(self):
        return web.TCPSite(self.appRunner, self.host, self.port)

    def get(self, path, **kwargs):
        return self._route.get(path, **kwargs)

    def put(self, path, **kwargs):
        return self._route.put(path, **kwargs)

    async def start(self):
        self._app.add_routes(self._route)
        await self.site.start()

    def get_app(self):
        self._app.add_routes(self._route)
        return self._app

    async def stop(self):
        await self.site.stop()

    def test_client(self) -> test_utils.TestClient:
        return test_utils.TestClient(test_utils.TestServer(self.get_app()), loop=asyncio.get_event_loop())

async def make_server(handle: typing.Callable[[web.Request], typing.Awaitable[web.Response]], port: int) -> typing.Tuple[web.Server, web.TCPSite]:
    """
    Make server and start it immidiatly
    :param handle: handler coroutinefunction
    :param port: port on wich server will be started
    :return:
    """
    assert asyncio.iscoroutinefunction(handle), 'handle must coroutine function'
    server = web.Server(handle)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    return server, site

def cancelok(foo):
    """
    Deco foo not to raise on cancelation
    :param foo:
    :return:
    """
    @functools.wraps(foo)
    async def wrapper(*args, **kwargs):
        try:
            return await foo(*args, **kwargs)
        except asyncio.CancelledError:
            return
    return wrapper


def make_query(query: dict):
    if isinstance(query, InputQuery):
        query = query._asdict()
    return '&'.join([f'{x}={y}' for x, y in query.items()])
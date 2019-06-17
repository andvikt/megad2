import typing

from .const import _MapKey, InputQuery


class _MapCallback(typing.Generic[_MapKey]):

    cb_map: typing.Dict[_MapKey, typing.Callable[[_MapKey], typing.Any]]

    def map_callback(self, key: _MapKey, foo):
        if key in self.cb_map:
            raise KeyError(f'{key} already registered')
        self.cb_map[key] = foo
        return foo

    def map_callback_deco(self, key: InputQuery):
        def deco(foo):
            return self.map_callback(key, foo)
        return deco
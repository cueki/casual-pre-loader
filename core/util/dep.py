from collections.abc import Callable
from functools import lru_cache
from types import FunctionType
from typing import Protocol, Self, cast, overload

type Transform[R] = Callable[[R], R]


class HasCache[R](Protocol):
    _cache: dict[str, Transform[R]]


class Dep[R, T: HasCache]:
    """
    A descriptor class that computes an object given another attribute of the same type, caching the result.
    """

    def __init__(self, func: Transform[R]):
        self.func: Transform[R] = func
        self.depname: str = cast(FunctionType, func).__code__.co_varnames[-1]

    def __set_name__(self, owner: type[T], name: str) -> None:
        self.name: str = name

    @overload
    def __get__(self, instance: None, owner: type[T]) -> Self: ...

    @overload
    def __get__(self, instance: T, owner: type[T]) -> T: ...

    def __get__(self, obj: T | None, objtype: type[T]) -> R | Self:
        if obj is None:
            return self

        try:
            return cast(R, obj.__dict__[self.name])
        except KeyError:
            pass

        return self._get_cached_func(obj)(getattr(obj, self.depname))

    def __set__(self, obj: T, value: R) -> None:
        if value is self: # guard against dataclasses' initial set
            return

        if self.name in obj._cache:
            del obj._cache[self.name]

        obj.__dict__[self.name] = value

    def __delete__(self, obj: T) -> None:
        if self.name in obj.__dict__:
            del obj.__dict__[self.name]

        if self.name in obj._cache:
            del obj._cache[self.name]

    def _create_cache(self, obj: T) -> None:
        # hacky, but works well
        if not hasattr(obj, '_cache'):
            obj._cache = {}

    def _get_cached_func(self, obj: T) -> Transform[R]:
        self._create_cache(obj)

        try:
            return obj._cache[self.name]
        except KeyError:
            pass

        func = lru_cache(maxsize=1)(self.func)

        obj._cache[self.name] = func
        return func

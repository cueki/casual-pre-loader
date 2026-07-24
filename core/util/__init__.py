from collections.abc import Callable, Iterable, Mapping
from dataclasses import Field, fields, is_dataclass
from functools import wraps
from typing import (
    Any,
    ClassVar,
    Concatenate,
    Literal,
    Protocol,
    cast,
    overload,
    runtime_checkable,
)

type FieldCompatibleMapping = Mapping[str, Any]
type FieldCompatibleIterable = Iterable[tuple[str, Any]]


@runtime_checkable
class DataClass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


def all_predicates[**P](*predicates: Callable[P, bool]) -> Callable[P, bool]:
    """
    Returns a function that returns true if all functions return a truthy value when run with the same arguements.

    Args:
        predicates: Any number of functions.

    Returns:
        A function that lazily calls all previously provided functions with the same arguments and returns true if they all return true.
    """

    def inner(*args: P.args, **kwargs: P.kwargs) -> bool:
        return all(predicate(*args, **kwargs) for predicate in predicates)

    return inner


@overload
def as_base_class[T, **P, R](
    func: Callable[Concatenate[T, P], R],
    /,
    pass_self: Literal[True] | None,
    cls: type | None
) -> Callable[Concatenate[T, P], R]: ...

@overload
def as_base_class[T, **P, R](
    func: Callable[P, R],
    /,
    pass_self: Literal[False],
    cls: type | None
) -> Callable[Concatenate[T, P], R]: ...

@overload
def as_base_class[T, **P, R](
    func: None,
    /,
    pass_self: Literal[False],
    cls: type | None
) -> Callable[[Callable[P, R]], Callable[Concatenate[T, P], R]]: ...

@overload
def as_base_class[T, **P, R](
    func: None,
    /,
    pass_self: Literal[True] | None,
    cls: type | None
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[Concatenate[T, P], R]]: ...

def as_base_class[T, **P, R](
    func: Callable[P, R] | Callable[Concatenate[T, P], R] | None = None,
    /,
    pass_self: bool | None = None,
    cls: type | None = None
) -> (
    # Callable[[Callable[P, R]], Callable[Concatenate[T, P], R]]
    # | Callable[[Callable[Concatenate[T, P], R]], Callable[Concatenate[T, P], R]]
    # | Callable[Concatenate[T, P], R]
    Callable[..., Callable[Concatenate[T, P], R]]
    | Callable[Concatenate[T, P], R]
):
    """
    A decorator function meant to be used with methods that temporarily sets the instance's `__class__` to its base class while the method runs.
    """

    pass_self = True if pass_self is None else pass_self

    def decorator(func: Callable[..., R]) -> Callable[Concatenate[T, P], R]:
        @wraps(func)
        def wrap(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            old_cls = type(self)
            try:
                object.__setattr__(self, '__class__', cls if cls is not None else old_cls.__base__)
                if pass_self:
                    return func(self, *args, **kwargs)
                return func(*args, **kwargs)
            finally:
                object.__setattr__(self, '__class__', old_cls)

        return wrap

    if func is None:
        return decorator
    return decorator(func)


def update_dataclass(obj: DataClass, other: DataClass | FieldCompatibleMapping | FieldCompatibleIterable | None = None, /, **kwargs) -> None:
    """
    Update a dataclass' values in-place.

    This function uses similar semantics to `dict.update()`, but operates on dataclass instances.
    It filters out fields/kv-pairs not present in the original dataclass' fields.

    The reasoning behind this instead of using `dataclasses.replace()` is to avoid creating a new instance.
    Since dataclass instances are often defined globally at the module-level,
    references to such objects may be held even after they have been replaced,
    e.g. by running `mdl.smdl..datacls = dataclasses.replace(mdl.smdl.datacls, key=value)`.
    Updating in place mitigates desyncronization of data (this does not magically fix data races! Use mutexes!).
    It may also slightly decrease short-term memory usage.

    Args:
        other: An optional dataclass, mapping, or tuple to update with.
        kwargs: Optional additional key-value pairs to update with.
    """

    fs = fields(obj)

    # O(n^2), but is necessary in order to emulate `dict.update()` as closely as possible according to the python documentation
    if other is None:
        pass
    elif is_dataclass(other):
        other = cast(DataClass, other)

        for _f in fields(other):
            for f in fs:
                if _f.name == f.name and _f.type == f.type:
                    setattr(obj, f.name, getattr(other, _f.name))
                    break
    elif isinstance(other, Mapping):
        other = cast(FieldCompatibleMapping, other)

        for k in other:
            for f in fs:
                if f.name == k:
                    setattr(obj, f.name, other[k])
                    break
    else:
        other = cast(FieldCompatibleIterable, other)

        for k, v in other:
            for f in fs:
                if k == f.name:
                    setattr(obj, f.name, v)
                    break

    for k in kwargs:
        for f in fs:
            if k == f.name:
                setattr(obj, f.name, kwargs[k])

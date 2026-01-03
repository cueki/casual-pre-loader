from collections.abc import Callable
from typing import Any


def all_predicates(*preds: Callable[[Any], bool]) -> Callable[[Any], bool]:
    return lambda x: all(p(x) for p in preds)

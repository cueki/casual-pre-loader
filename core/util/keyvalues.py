from collections.abc import Iterator
from pathlib import Path

from sourcepp import kvpp

KVNode = kvpp.KV1 | kvpp.KV1ElementReadable


def parse(text: str) -> kvpp.KV1:
    # kvpp glues a leading BOM onto the first key, so strip it here too for
    # callers passing text they read themselves
    return kvpp.KV1(text.removeprefix('﻿'))


def load(path: Path) -> kvpp.KV1:
    # mods authored on windows often ship a BOM; utf-8-sig drops it
    return parse(path.read_text(encoding='utf-8-sig', errors='replace'))


def child(node: KVNode, key: str) -> KVNode | None:
    """First child with `key` (case-insensitive, like the engine), or None."""
    found = node.get_child(key, 0)
    return None if found.is_invalid() else found


def walk(node: KVNode) -> Iterator[KVNode]:
    """Every descendant of `node`, depth-first, in file order."""
    for c in node.get_children():
        yield c
        yield from walk(c)

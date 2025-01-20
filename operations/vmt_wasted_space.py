from dataclasses import dataclass
from typing import List, Callable, Iterator
import re


@dataclass
class WastedBytes:
    start: int
    length: int
    content: str


def rebuild_content(content: str, waste_bytes: List[WastedBytes]) -> str:
    waste_bytes.sort(key=lambda x: x.start, reverse=True)
    result = content
    for waste in waste_bytes:
        result = result[:waste.start] + result[waste.start + waste.length:]
    return result


def find_closing_bracket(content: str) -> int:
    matches = list(re.finditer(r'}\s*$', content, re.MULTILINE))
    return matches[-1].start() if matches else -1


def append_whitespace(content: str, total_bytes: int) -> str:
    # add before the closing bracket
    closing_pos = find_closing_bracket(content)
    if closing_pos == -1:
        return content

    return (
            content[:closing_pos] +
            ' ' * (total_bytes - 1) + '\n' +
            content[closing_pos:]
    )


class VMTSpaceAnalyzer:
    def __init__(self):
        self.waste_detectors: List[Callable[[str], Iterator[WastedBytes]]] = []

    def add_detector(self, detector: Callable[[str], Iterator[WastedBytes]]):
        self.waste_detectors.append(detector)

    def consolidate_spaces(self, content: bytes) -> bytes:
        try:
            decoded = content.decode('utf-8')
            if not decoded.strip():
                return content

            # collect all wasted bytes
            waste_bytes = []
            for detector in self.waste_detectors:
                waste_bytes.extend(detector(decoded))

            total_waste = sum(w.length for w in waste_bytes)
            if total_waste == 0:
                return content

            # rebuild content
            result = rebuild_content(decoded, waste_bytes)
            result = append_whitespace(result, total_waste)

            return result.encode('utf-8')

        except UnicodeDecodeError:
            return content
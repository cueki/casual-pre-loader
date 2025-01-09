from typing import Iterator
import re
from operations.vmt_wasted_space import  WastedBytes


def comment_detector(content: str) -> Iterator[WastedBytes]:
    # Detect comment lines
    pos = 0
    for line in content.splitlines(keepends=True):
        if line.lstrip().startswith('//'):
            yield WastedBytes(pos, len(line), line)
        pos += len(line)


def quote_detector(content: str) -> Iterator[WastedBytes]:
    # this regex looks for "$attr" "val" and "$attr" val by splitting it into 3 groups
    pattern = re.compile(r'"([^"]+)"\s+(?:"([^"]+)"|(\S+))')

    def can_remove_quotes(value: str) -> bool:
        return ' ' not in value and '\t' not in value and value.strip() != ''

    pos = 0
    for line in content.splitlines(keepends=True):
        for match in pattern.finditer(line):
            attr, quoted_value, unquoted_value = match.groups()
            if (quoted_value is not None and
                    can_remove_quotes(attr) and
                    can_remove_quotes(quoted_value) and not
                    line.lstrip().startswith('//')):
                # Calculate quote positions
                attr_start = match.start(1) - 1
                attr_end = match.end(1)
                value_start = match.start(2) - 1
                value_end = match.end(2)

                # Yield positions relative to file start
                yield WastedBytes(pos + attr_start, 1, '"')
                yield WastedBytes(pos + attr_end, 1, '"')
                yield WastedBytes(pos + value_start, 1, '"')
                yield WastedBytes(pos + value_end, 1, '"')

            # Same as above but handles instances where the attribute is quoted while the value is not
            elif (unquoted_value is not None and
                    can_remove_quotes(attr) and not
                    line.lstrip().startswith('//')):

                attr_start = match.start(1) - 1
                attr_end = match.end(1)

                yield WastedBytes(pos + attr_start, 1, '"')
                yield WastedBytes(pos + attr_end, 1, '"')
        pos += len(line)
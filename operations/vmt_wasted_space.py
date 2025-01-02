from dataclasses import dataclass
from typing import List
import re


@dataclass
class WastedSpace:
    start_pos: int
    length: int
    original_content: str
    line_number: int


class VMTSpaceAnalyzer:
    def __init__(self):
        self.comment_pattern = re.compile(rb'^\s*//.*$', re.MULTILINE)

    def find_closing_bracket(self, content: str) -> int:
        matches = list(re.finditer(r'}\s*$', content, re.MULTILINE))
        return matches[-1].start() if matches else -1

    def analyze_content(self, content: bytes) -> List[WastedSpace]:
        # Analyzes VMT content and returns list of wasted spaces
        wasted_spaces = []
        line_number = 1
        current_pos = 0

        try:
            decoded = content.decode('utf-8')
            lines = decoded.splitlines(keepends=True)

            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith('//'):
                    wasted_spaces.append(WastedSpace(
                        start_pos=current_pos,
                        length=len(line),
                        original_content=line.rstrip('\n\r'),
                        line_number=line_number
                    ))
                current_pos += len(line)
                line_number += 1

            return wasted_spaces

        except UnicodeDecodeError:
            return []

    def consolidate_spaces(self, content: bytes) -> bytes:
        # Process VMT content to consolidate wasted space
        try:
            decoded = content.decode('utf-8')
            closing_bracket_pos = self.find_closing_bracket(decoded)

            if closing_bracket_pos == -1:
                return content

            wasted_spaces = self.analyze_content(content)
            total_wasted_bytes = sum(space.length for space in wasted_spaces)

            if total_wasted_bytes == 0:
                return content

            # Remove comments
            for space in sorted(wasted_spaces, key=lambda x: x.start_pos, reverse=True):
                decoded = decoded[:space.start_pos] + decoded[space.start_pos + space.length:]

            # Find new closing bracket position and structure result
            new_closing_pos = self.find_closing_bracket(decoded)
            if new_closing_pos == -1:
                return content

            prefix = '\n'.join(decoded[:new_closing_pos].split('\n'))
            whitespace = ' ' * (total_wasted_bytes - 1) + '\n'
            result = prefix + whitespace + decoded[new_closing_pos:]

            return result.encode('utf-8')

        except UnicodeDecodeError:
            return content

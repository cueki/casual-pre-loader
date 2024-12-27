from dataclasses import dataclass
from typing import Dict, List, Optional
import re
from pathlib import Path


@dataclass
class WastedSpace:
    start_pos: int  # Start position in file
    length: int  # Length of wasted space
    original_content: str  # Original commented content
    line_number: int  # Line number in file


@dataclass
class VMTFile:
    path: str
    content: bytes
    wasted_spaces: List[WastedSpace]
    total_size: int
    closing_bracket_pos: int


class VMTSpaceAnalyzer:
    def __init__(self):
        self.comment_pattern = re.compile(rb'^\s*//.*$', re.MULTILINE)

    def find_closing_bracket(self, content: str) -> int:
        # Look for the last closing curly bracket
        matches = list(re.finditer(r'}\s*$', content, re.MULTILINE))
        if matches:
            return matches[-1].start()
        else:
            return -1

    def analyze_file(self, content: bytes, filepath: str) -> VMTFile:
        wasted_spaces = []
        line_number = 1
        # First decode the content
        decoded = content.decode('utf-8')
        closing_bracket_pos = self.find_closing_bracket(decoded)

        lines = decoded.splitlines(keepends=True)
        current_pos = 0
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            if stripped.startswith('//'):
                # Found a comment line
                start_pos = current_pos
                line_length = len(line)

                wasted_spaces.append(WastedSpace(
                    start_pos=start_pos,
                    length=line_length,
                    original_content=line.rstrip('\n\r'),
                    line_number=line_number
                ))

                # Update position
                current_pos += line_length
                line_number += 1
                i += 1
            else:
                current_pos += len(line)
                line_number += 1
                i += 1

        return VMTFile(filepath, content, wasted_spaces, len(content), closing_bracket_pos)

    def consolidate_wasted_space(self, vmt_file: VMTFile) -> Optional[bytes]:
        if vmt_file.closing_bracket_pos == -1:
            return None

        try:
            # Calculate total wasted space
            total_wasted_bytes = sum(space.length for space in vmt_file.wasted_spaces)
            if total_wasted_bytes == 0:
                return vmt_file.content

            decoded = vmt_file.content.decode('utf-8')

            # Sort in reverse order to avoid position shifting
            for space in sorted(vmt_file.wasted_spaces, key=lambda x: x.start_pos, reverse=True):
                decoded = decoded[:space.start_pos] + decoded[space.start_pos + space.length:]

            # Need to update the new closing bracket position after comment removal
            new_closing_pos = self.find_closing_bracket(decoded)
            if new_closing_pos == -1:
                return None

            # Find the last non-empty line before the closing bracket
            lines = decoded[:new_closing_pos].split('\n')
            prefix = '\n'.join(lines)

            # Create whitespace with the same number of bytes as comments
            whitespace = ' ' * (total_wasted_bytes - 1) + '\n'

            # Combine: prefix + whitespace + closing bracket + whatever else
            result = prefix + whitespace + decoded[new_closing_pos:]

            return result.encode('utf-8')

        except UnicodeDecodeError:
            return None


class VMTSpaceManager:
    def __init__(self):
        self.analyzer = VMTSpaceAnalyzer()

    def analyze_directory(self, directory: str) -> Dict[str, VMTFile]:
        results = {}
        for path in Path(directory).rglob('*.vmt'):
            with open(path, 'rb') as f:
                content = f.read()
                results[str(path)] = self.analyzer.analyze_file(content, str(path))
        return results

    def print_analysis(self, vmt_files: Dict[str, VMTFile]):
        total_wasted_bytes = 0

        for filepath, vmt_file in vmt_files.items():
            wasted_bytes = sum(space.length for space in vmt_file.wasted_spaces)
            total_wasted_bytes += wasted_bytes

            if wasted_bytes > 0:
                print(f"\nFile: {filepath}")
                print(f"Total size: {vmt_file.total_size} bytes")
                print(f"Wasted space: {wasted_bytes} bytes")
                print("Wasted spaces:")
                for i, space in enumerate(vmt_file.wasted_spaces):
                    print(f"  [{i}] Line {space.line_number}: {space.original_content}")

        print(f"\nTotal wasted bytes across all files: {total_wasted_bytes}")

    def consolidate_spaces(self, directory: str):
        vmt_files = self.analyze_directory(directory)

        for filepath, vmt_file in vmt_files.items():
            if sum(space.length for space in vmt_file.wasted_spaces) > 0:
                new_content = self.analyzer.consolidate_wasted_space(vmt_file)
                if new_content:
                    backup_path = filepath + '.backup'
                    with open(backup_path, 'wb') as f:
                        f.write(vmt_file.content)

                    with open(filepath, 'wb') as f:
                        f.write(new_content)
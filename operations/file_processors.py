import re
from typing import Dict
from models.pcf_file import PCFFile
from operations.color import RGB, analyze_pcf_colors, transform_team_colors
from operations.detectors import comment_detector, quote_detector
from operations.vmt_wasted_space import VMTSpaceAnalyzer, find_closing_bracket


def pcf_color_processor(targets: Dict[str, Dict[str, RGB]]):
    def process_pcf(pcf: PCFFile) -> PCFFile:
        colors = analyze_pcf_colors(pcf)
        return transform_team_colors(pcf, colors, targets)

    return process_pcf


def vmt_space_processor():
    analyzer = VMTSpaceAnalyzer()
    analyzer.add_detector(comment_detector)
    analyzer.add_detector(quote_detector)

    def process_vmt(content: bytes) -> bytes:
        return analyzer.consolidate_spaces(content)

    return process_vmt


def vmt_nodraw_replace_processor():
    def process_vmt(content: bytes) -> bytes:
        try:
            # Decode the VMT content
            text = content.decode('utf-8')
            original_size = len(content)

            # Find the shader name (first line in quotes)
            shader_match = re.match(r'^"([^"]+)"', text)
            if not shader_match:
                return content

            shader_name = shader_match.group(1)

            # Create new VMT content with just nodraw
            new_content = f'"{shader_name}"\n{{\n\t$nodraw\t1\n'

            # Calculate how many bytes we need to pad
            current_size = len(new_content.encode('utf-8'))
            padding_needed = original_size - current_size - 2  # -1 for the closing brace

            # Add padding if needed
            if padding_needed < 0:
                return content  # Can't make it smaller

            # Add padding spaces before closing brace
            new_content += ' ' * padding_needed + '\n}'

            return new_content.encode('utf-8')

        except UnicodeDecodeError:
            return content

    return process_vmt


def vmt_texture_replace_processor(old_texture: str, new_texture: str):
    def process_vmt(content: bytes) -> bytes:
        try:
            text = content.decode('utf-8')
            original_size = len(content)
            print(text)
            pattern = f'\\$basetexture\\s+{re.escape(old_texture)}'
            modified = re.sub(pattern, f'$basetexture {new_texture}', text)
            size_diff = len(modified.encode('utf-8')) - original_size

            closing_pos = find_closing_bracket(modified)
            if closing_pos == -1:
                return content

            # Find the last whitespace line before the closing bracket
            lines = modified[:closing_pos].splitlines(keepends=True)
            if not lines:
                return content

            # Get the last line which should be our whitespace line
            whitespace_line = lines[-1]
            available_space = len(whitespace_line.rstrip('\n'))  # Don't count the newline in available space

            if size_diff < -1:
                print("smaller")
                # Adding space, keep the newline
                modified = (modified[:closing_pos] +
                            ' ' * (-size_diff - 1) + '\n' +
                            modified[closing_pos:])
            elif size_diff > -1:
                if available_space < size_diff:
                    return content
                print("bigger")
                # Find where the whitespace line begins
                whitespace_start = closing_pos - len(whitespace_line)
                # Remove characters from the whitespace but preserve the newline
                modified = (modified[:whitespace_start] +
                            whitespace_line[:-1][:-size_diff] + '\n' +
                            modified[closing_pos:])

            return modified.encode('utf-8')

        except UnicodeDecodeError:
            return content

    return process_vmt
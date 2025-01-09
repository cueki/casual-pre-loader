import re
from typing import Dict
from models.pcf_file import PCFFile
from operations.color import RGB, analyze_pcf_colors, transform_team_colors
from operations.detectors import comment_detector, quote_detector
from operations.pcf_merge import find_duplicate_array_elements, update_array_indices, nullify_unused_elements, \
    reorder_elements
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


def pcf_duplicate_index_processor():
    def process_pcf(pcf: PCFFile) -> PCFFile:
        duplicates = find_duplicate_array_elements(pcf)

        if duplicates:
            print("Found duplicate elements: ")
            for hash_, indices in duplicates.items():
                print(f"Indices: {indices}")

            update_array_indices(pcf, duplicates)
            nullify_unused_elements(pcf, duplicates)
            print("Updated array indices and nullified unused elements")

            # Reorder elements to be sequential
            reorder_elements(pcf)
            print("Reordered elements to be sequential")
        else:
            print("No duplicates found")

        return pcf

    return process_pcf

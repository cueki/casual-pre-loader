import os
from typing import Tuple, List, Optional, Set, Dict, Any
from core.constants import AttributeType
from models.element import PCFElement
from models.pcf_file import PCFFile

def find_in_vpk(vpk_data: bytes, pattern: bytes, context_size: int = 1000) -> List[Tuple[int, bytes]]:
    """
    Find all occurrences of a binary pattern in VPK data.

    Args:
        vpk_data: Raw VPK file data
        pattern: Binary pattern to search for
        context_size: Number of bytes of context to return around match

    Returns:
        List of tuples containing (offset, context bytes)
    """
    matches = []
    pos = 0

    while True:
        try:
            pos = vpk_data.index(pattern, pos)
            context_start = max(0, pos - context_size)
            context_end = min(len(vpk_data), pos + len(pattern) + context_size)
            matches.append((pos, vpk_data[context_start:context_end]))
            pos += 1
        except ValueError:
            break

    return matches


def extract_pcf_signature(pcf_path: str, signature_size: int = 1000) -> bytes:
    """
    Extract a unique binary signature from a PCF file for searching.

    Args:
        pcf_path: Path to PCF file
        signature_size: Size of signature to extract after header

    Returns:
        Signature bytes
    """
    with open(pcf_path, 'rb') as f:
        data = f.read()
        # Get header and chunk after it
        header_end = data.index(b'\x00')
        header = data[:header_end]
        signature = data[header_end:header_end + signature_size]
        return header + signature


def pad_to_size(file_path: str, target_size: int) -> bool:
    """
    Pad a file with null bytes to reach a target size.

    Args:
        file_path: Path to file to pad
        target_size: Desired final size in bytes

    Returns:
        True if successful, False if error
    """
    try:
        current_size = os.path.getsize(file_path)
        if current_size > target_size:
            return False

        if current_size < target_size:
            with open(file_path, 'ab') as f:
                f.write(b'\x00' * (target_size - current_size))

        return os.path.getsize(file_path) == target_size

    except OSError:
        return False


def find_unused_strings(pcf: PCFFile) -> Set[int]:
    """
    Find indices of unused strings in PCF string dictionary.

    Args:
        pcf: PCF file object

    Returns:
        Set of unused string indices
    """
    used_strings: Set[int] = set()

    # Track string usage
    for element in pcf.elements:
        used_strings.add(element.type_name_index)
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Track attribute names
            if isinstance(attr_name, bytes):
                try:
                    idx = pcf.string_dictionary.index(attr_name)
                    used_strings.add(idx)
                except ValueError:
                    pass

            # Track string values
            if attr_type == AttributeType.STRING:
                if isinstance(attr_value, bytes):
                    try:
                        idx = pcf.string_dictionary.index(attr_value)
                        used_strings.add(idx)
                    except ValueError:
                        pass

    # Return unused indices
    return set(range(len(pcf.string_dictionary))) - used_strings


def format_color(color: Tuple[int, int, int, int]) -> str:
    """Format RGBA color tuple for display."""
    return f"RGBA({color[0]}, {color[1]}, {color[2]}, {color[3]})"


def format_vector(vector: Tuple[float, ...]) -> str:
    """Format vector tuple for display."""
    return f"Vector({', '.join(f'{v:.3f}' for v in vector)})"


def format_attribute_value(attr_type: AttributeType, value: Any) -> str:
    """
    Format attribute value for human-readable display.

    Args:
        attr_type: Type of attribute
        value: Attribute value

    Returns:
        Formatted string representation
    """
    if attr_type == AttributeType.COLOR:
        return format_color(value)
    elif attr_type in (AttributeType.VECTOR2, AttributeType.VECTOR3, AttributeType.VECTOR4):
        return format_vector(value)
    elif attr_type == AttributeType.MATRIX:
        return "Matrix[\n" + "\n".join(f"  {format_vector(row)}" for row in value) + "\n]"
    elif isinstance(value, bytes):
        return f'"{value.decode("ascii", errors="replace")}"'
    elif isinstance(value, (list, tuple)):
        return f"[{', '.join(str(x) for x in value)}]"
    return str(value)


def create_backup(file_path: str, backup_suffix: str = '.backup') -> Optional[str]:
    """
    Create backup of a file.

    Args:
        file_path: Path to file to back up
        backup_suffix: Suffix to add to back up file

    Returns:
        Path to back up file if successful, None if failed
    """
    try:
        backup_path = file_path + backup_suffix
        with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        return backup_path
    except OSError:
        return None


def compare_elements(elem1: PCFElement, elem2: PCFElement) -> List[Dict[str, Any]]:
    """
    Compare two PCF elements and return their differences.

    Args:
        elem1: First element
        elem2: Second element

    Returns:
        List of differences with details
    """
    differences = []

    # Compare basic properties
    if elem1.type_name_index != elem2.type_name_index:
        differences.append({
            'type': 'type_index',
            'old': elem1.type_name_index,
            'new': elem2.type_name_index
        })

    if elem1.element_name != elem2.element_name:
        differences.append({
            'type': 'name',
            'old': elem1.element_name,
            'new': elem2.element_name
        })

    # Compare attributes
    all_attrs = set(elem1.attributes.keys()) | set(elem2.attributes.keys())
    for attr_name in all_attrs:
        attr1 = elem1.attributes.get(attr_name)
        attr2 = elem2.attributes.get(attr_name)

        if attr1 is None or attr2 is None:
            differences.append({
                'type': 'attribute',
                'name': attr_name,
                'old': format_attribute_value(attr1[0], attr1[1]) if attr1 else None,
                'new': format_attribute_value(attr2[0], attr2[1]) if attr2 else None
            })
        elif attr1 != attr2:
            differences.append({
                'type': 'attribute',
                'name': attr_name,
                'old': format_attribute_value(attr1[0], attr1[1]),
                'new': format_attribute_value(attr2[0], attr2[1])
            })
    return differences


def pad_path(path: bytes, target_length: int) -> bytes:
    """
    Pad a path with spaces to reach target length while maintaining extension.
    Used for maintaining consistent string lengths in PCF attributes.

    Args:
        path: Path as bytes
        target_length: Desired total length

    Returns:
        Padded path as bytes
    """
    if len(path) >= target_length:
        return path

    try:
        # Split at last dot while preserving the dot in extension
        dot_index = path.rindex(b'.')
        base = path[:dot_index]
        ext = path[dot_index:]

        # Add padding before the extension
        padding_size = target_length - len(path)
        padded = base + b' ' * padding_size + ext

        return padded

    except ValueError:
        # No extension found, pad at end
        return path + b' ' * (target_length - len(path))


def get_file_size(filepath):
    try:
        return os.path.getsize(filepath)
    except (OSError, FileNotFoundError) as e:
        print(f"Error getting file size: {e}")
        return None
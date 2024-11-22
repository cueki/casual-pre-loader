from typing import List, Set, Optional, Any
from pcfcodec import PCFCodec, AttributeType
import copy
import os
import argparse
from dataclasses import dataclass


@dataclass
class ReclaimableSpace:
    """Information about space that can be reclaimed."""
    index: int
    size: int
    type: str
    risk: str
    data: bytes


@dataclass
class Difference:
    """Represents a difference between two PCF files"""
    element_index: int
    element_type: str
    element_name: str
    attribute_name: str
    attribute_type: AttributeType
    old_value: Any
    new_value: Any


def find_reclaimable_space(pcf: PCFCodec) -> List[ReclaimableSpace]:
    """Identify spaces that can be reclaimed in the PCF file."""
    reclaimable = []
    used_strings: Set[int] = set()

    # Track string usage
    for element in pcf.pcf.elements:
        used_strings.add(element.type_name_index)
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Track attribute names
            if isinstance(attr_name, bytes):
                try:
                    idx = pcf.pcf.string_dictionary.index(attr_name)
                    used_strings.add(idx)
                except ValueError:
                    pass

            # Track string values
            if attr_type == AttributeType.STRING:
                if isinstance(attr_value, bytes):
                    try:
                        idx = pcf.pcf.string_dictionary.index(attr_value)
                        used_strings.add(idx)
                    except ValueError:
                        pass

    # Add unused strings to reclaimable space
    for idx, string in enumerate(pcf.pcf.string_dictionary):
        if idx not in used_strings:
            original_data = string if isinstance(string, bytes) else string.encode('ascii')
            size = len(original_data) + 1  # Include null terminator
            reclaimable.append(ReclaimableSpace(
                index=idx,
                size=size,
                type='string',
                risk='safe',
                data=original_data
            ))

    return reclaimable

def remove_unused_strings(pcf: PCFCodec, unused_indices: Set[int]) -> None:
    """Remove unused strings and update all references."""
    new_dictionary = []
    index_map = {}  # Maps old indices to new indices

    for old_idx, string in enumerate(pcf.pcf.string_dictionary):
        if old_idx not in unused_indices:
            index_map[old_idx] = len(new_dictionary)
            new_dictionary.append(string)

    # Update element references
    for element in pcf.pcf.elements:
        if element.type_name_index in index_map:
            element.type_name_index = index_map[element.type_name_index]

        new_attributes = {}
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            if isinstance(attr_name, bytes):
                try:
                    old_idx = pcf.pcf.string_dictionary.index(attr_name)
                    if old_idx in index_map:
                        new_attr_name = pcf.pcf.string_dictionary[old_idx]
                    else:
                        new_attr_name = attr_name
                except ValueError:
                    new_attr_name = attr_name
            else:
                new_attr_name = attr_name
            new_attributes[new_attr_name] = (attr_type, attr_value)
        element.attributes = new_attributes

    pcf.pcf.string_dictionary = new_dictionary

def compare_pcf_files(pcf1: PCFCodec, pcf2: PCFCodec, element_filter: Optional[List[int]] = None) -> List[Difference]:
    """Compare two PCF files and return their differences."""
    differences: List[Difference] = []

    # Compare file versions if different
    if pcf1.pcf.version != pcf2.pcf.version:
        print(f"\nVersion difference:")
        print(f"  Base: {pcf1.pcf.version}")
        print(f"  Source: {pcf2.pcf.version}")

    # Helper function to get element type name
    def get_type_name(pcf: PCFCodec, element: Any) -> str:
        type_str = pcf.pcf.string_dictionary[element.type_name_index]
        return type_str.decode('ascii', errors='replace') if isinstance(type_str, bytes) else str(type_str)

    # Process each element
    min_elements = min(len(pcf1.pcf.elements), len(pcf2.pcf.elements))
    for elem_idx in range(min_elements):
        if element_filter and elem_idx not in element_filter:
            continue

        elem1 = pcf1.pcf.elements[elem_idx]
        elem2 = pcf2.pcf.elements[elem_idx]

        # Compare element types
        type1 = get_type_name(pcf1, elem1)
        type2 = get_type_name(pcf2, elem2)

        if type1 != type2:
            differences.append(Difference(
                element_index=elem_idx,
                element_type=type1,
                element_name=elem1.element_name.decode('ascii', errors='replace')
                if isinstance(elem1.element_name, bytes) else str(elem1.element_name),
                attribute_name="<element_type>",
                attribute_type=AttributeType.STRING,
                old_value=type1,
                new_value=type2
            ))
            continue  # Skip further comparison if types don't match

        # Compare element names
        name1 = elem1.element_name.decode('ascii', errors='replace') if isinstance(elem1.element_name, bytes) else str(
            elem1.element_name)
        name2 = elem2.element_name.decode('ascii', errors='replace') if isinstance(elem2.element_name, bytes) else str(
            elem2.element_name)

        if name1 != name2:
            differences.append(Difference(
                element_index=elem_idx,
                element_type=type1,
                element_name=name1,
                attribute_name="<element_name>",
                attribute_type=AttributeType.STRING,
                old_value=name1,
                new_value=name2
            ))

        # Compare attributes
        all_attrs = set(elem1.attributes.keys()) | set(elem2.attributes.keys())
        for attr_name in all_attrs:
            attr1 = elem1.attributes.get(attr_name)
            attr2 = elem2.attributes.get(attr_name)

            # Handle missing attributes
            if attr1 is None or attr2 is None:
                differences.append(Difference(
                    element_index=elem_idx,
                    element_type=type1,
                    element_name=name1,
                    attribute_name=attr_name.decode('ascii', errors='replace')
                    if isinstance(attr_name, bytes) else str(attr_name),
                    attribute_type=attr1[0] if attr1 else attr2[0],
                    old_value=attr1[1] if attr1 else "<missing>",
                    new_value=attr2[1] if attr2 else "<missing>"
                ))
                continue

            # Compare attribute types
            if attr1[0] != attr2[0]:
                differences.append(Difference(
                    element_index=elem_idx,
                    element_type=type1,
                    element_name=name1,
                    attribute_name=attr_name.decode('ascii', errors='replace')
                    if isinstance(attr_name, bytes) else str(attr_name),
                    attribute_type=attr1[0],
                    old_value=f"Type: {attr1[0].name}",
                    new_value=f"Type: {attr2[0].name}"
                ))
                continue

            # Compare attribute values
            if attr1[1] != attr2[1]:
                differences.append(Difference(
                    element_index=elem_idx,
                    element_type=type1,
                    element_name=name1,
                    attribute_name=attr_name.decode('ascii', errors='replace')
                    if isinstance(attr_name, bytes) else str(attr_name),
                    attribute_type=attr1[0],
                    old_value=attr1[1],
                    new_value=attr2[1]
                ))

    return differences


def estimate_attribute_size(attr_type: AttributeType, value: Any) -> int:
    """Estimate the size an attribute will take in the file."""
    if attr_type == AttributeType.ELEMENT:
        return 4  # uint32
    elif attr_type == AttributeType.INTEGER:
        return 4  # int32
    elif attr_type == AttributeType.FLOAT:
        return 4  # float32
    elif attr_type == AttributeType.BOOLEAN:
        return 1  # uint8
    elif attr_type == AttributeType.STRING:
        if isinstance(value, bytes):
            return len(value) + 1  # Include null terminator
        return len(str(value).encode('ascii')) + 1
    elif attr_type == AttributeType.BINARY:
        return 4 + len(value)  # length + data
    elif attr_type == AttributeType.COLOR:
        return 4  # RGBA
    elif attr_type == AttributeType.VECTOR2:
        return 8  # 2 floats
    elif attr_type == AttributeType.VECTOR3:
        return 12  # 3 floats
    elif attr_type == AttributeType.VECTOR4:
        return 16  # 4 floats
    elif attr_type == AttributeType.MATRIX:
        return 64  # 4x4 matrix of floats
    elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
        base_type = AttributeType(attr_type.value - 14)
        if value == "<missing>":
            return 4  # Just the array length
        return 4 + sum(estimate_attribute_size(base_type, item) for item in value)  # length + items
    return 0

def get_null_value(attr_type: AttributeType) -> Any:
    """Get a null/zero value for a given attribute type."""
    if attr_type == AttributeType.ELEMENT:
        return 0  # uint32
    elif attr_type == AttributeType.INTEGER:
        return 0  # int32
    elif attr_type == AttributeType.FLOAT:
        return 0.0  # float32
    elif attr_type == AttributeType.BOOLEAN:
        return False  # uint8
    elif attr_type == AttributeType.STRING:
        return b""  # empty string
    elif attr_type == AttributeType.BINARY:
        return b""  # empty binary
    elif attr_type == AttributeType.COLOR:
        return 0, 0, 0, 0  # RGBA zeros
    elif attr_type == AttributeType.VECTOR2:
        return 0.0, 0.0  # 2D vector zeros
    elif attr_type == AttributeType.VECTOR3:
        return 0.0, 0.0, 0.0  # 3D vector zeros
    elif attr_type == AttributeType.VECTOR4:
        return 0.0, 0.0, 0.0, 0.0  # 4D vector zeros
    elif attr_type == AttributeType.MATRIX:
        return [(0.0, 0.0, 0.0, 0.0) for _ in range(4)]  # 4x4 matrix zeros
    elif attr_type.value >= AttributeType.ELEMENT_ARRAY.value:
        return []  # empty array
    return None


def merge_pcf_files(
        target_path: str,
        source_path: str,
        output_path: str,
        zero_missing: bool = True,
        dry_run: bool = False,
        verbose: bool = False
) -> bool:
    """
    Merge source PCF into target PCF using comparison-based approach.
    Missing or different values can be zeroed out instead of deleted.

    Args:
        target_path: Path to target PCF file (size will be preserved)
        source_path: Path to source PCF file with changes to merge
        output_path: Path to save merged result
        zero_missing: If True, replace missing/different values with zeros instead of deleting
        dry_run: If True, only check if merge is possible
        verbose: If True, show detailed information about changes
    """
    try:
        # Get target file size
        target_size = os.path.getsize(target_path)
        print(f"\nTarget file size: {target_size} bytes")

        # Load PCF files
        target_pcf = PCFCodec()
        source_pcf = PCFCodec()
        target_pcf.decode(target_path)
        source_pcf.decode(source_path)

        # Compare files to find differences
        differences = compare_pcf_files(target_pcf, source_pcf)

        if not differences:
            print("\nNo differences found between files")
            return True

        # Create working copy for modifications
        merged_pcf = copy.deepcopy(target_pcf)
        changes_to_make = []

        # Analyze changes
        for diff in differences:
            # Track actual change to make
            if diff.new_value == "<missing>" and zero_missing:
                # Replace with zeros instead of deleting
                changes_to_make.append(Difference(
                    element_index=diff.element_index,
                    element_type=diff.element_type,
                    element_name=diff.element_name,
                    attribute_name=diff.attribute_name,
                    attribute_type=diff.attribute_type,
                    old_value=diff.old_value,
                    new_value=get_null_value(diff.attribute_type)
                ))
            else:
                changes_to_make.append(diff)

        # Report changes
        if verbose or dry_run:
            print("\nChanges to make:")
            for diff in changes_to_make:
                print(f"\nElement {diff.element_index} ({diff.element_type})")
                print(f"Name: {diff.element_name}")
                print(f"Attribute: {diff.attribute_name}")
                if diff.new_value == "<missing>":
                    print(f"  Zero out: {diff.old_value}")
                elif diff.old_value == "<missing>":
                    print(f"  Add: {diff.new_value}")
                else:
                    print(f"  Old: {diff.old_value}")
                    print(f"  New: {diff.new_value}")

        if dry_run:
            return True

        # Apply changes
        for diff in changes_to_make:
            element = merged_pcf.pcf.elements[diff.element_index]

            if diff.attribute_name == "<element_type>":
                # Update element type
                type_str = diff.new_value.encode('ascii') if isinstance(diff.new_value, str) else diff.new_value
                type_idx = merged_pcf.pcf.string_dictionary.index(type_str)
                element.type_name_index = type_idx
                continue

            if diff.attribute_name == "<element_name>":
                # Update element name
                element.element_name = diff.new_value.encode('ascii') if isinstance(diff.new_value,
                                                                                    str) else diff.new_value
                continue

            # Handle attribute changes
            attr_name = diff.attribute_name.encode('ascii') if isinstance(diff.attribute_name,
                                                                          str) else diff.attribute_name

            if diff.new_value == "<missing>" and not zero_missing:
                # Only delete if we're not zeroing out
                if attr_name in element.attributes:
                    del element.attributes[attr_name]
            else:
                # Add, modify, or zero out attribute
                new_value = diff.new_value if diff.new_value != "<missing>" else get_null_value(diff.attribute_type)
                element.attributes[attr_name] = (diff.attribute_type, new_value)

        # Save merged PCF
        merged_pcf.encode(output_path)

        # Verify and pad file size
        merged_size = os.path.getsize(output_path)
        if merged_size > target_size:
            print(f"\nError: Merged file ({merged_size} bytes) larger than target ({target_size} bytes)")
            os.remove(output_path)
            return False

        if merged_size < target_size:
            if not pad_file_to_size(output_path, target_size):
                print("Error: Failed to pad file to target size")
                os.remove(output_path)
                return False

        print("\nMerge completed successfully")
        return True

    except Exception as e:
        print(f"Error during merge: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run and os.path.exists(output_path):
            os.remove(output_path)
        return False


def pad_file_to_size(filename: str, target_size: int) -> bool:
    """Pad a file with null bytes to reach the target size."""
    try:
        current_size = os.path.getsize(filename)
        if current_size > target_size:
            print(f"Error: Current size {current_size} exceeds target size {target_size}")
            return False

        if current_size < target_size:
            padding_needed = target_size - current_size
            print(f"\nPadding file with {padding_needed} null bytes")

            with open(filename, 'ab') as f:
                f.write(b'\x00' * padding_needed)

            final_size = os.path.getsize(filename)
            if final_size != target_size:
                print(f"Error: Final size {final_size} doesn't match target {target_size}")
                return False

        return True

    except Exception as e:
        print(f"Error padding file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Merge two PCF files while maintaining original size')
    parser.add_argument('target_pcf', help='Path to target PCF file (size will be preserved)')
    parser.add_argument('source_pcf', help='Path to source PCF file with changes to merge')
    parser.add_argument('output_pcf', help='Path to save merged result')
    parser.add_argument('--no-zero', action='store_true',
                        help='Delete missing values instead of zeroing them out')
    parser.add_argument('--dry-run', action='store_true',
                        help='Check if merge is possible without writing')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed information about changes')
    parser.add_argument('--backup', action='store_true',
                        help='Create backup of target PCF before modifying')

    args = parser.parse_args()

    # Create backup if requested
    if args.backup and os.path.exists(args.target_pcf):
        backup_path = args.target_pcf + '.backup'
        print(f"Creating backup at: {backup_path}")
        try:
            with open(args.target_pcf, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False

    success = merge_pcf_files(
        args.target_pcf,
        args.source_pcf,
        args.output_pcf,
        zero_missing=not args.no_zero,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if success:
        if args.dry_run:
            print("\nDry run successful - merge appears possible!")
        else:
            print("\nMerge completed successfully!")
    else:
        print("\nMerge failed!")
        if args.backup:
            print("You can restore from the backup file if needed")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
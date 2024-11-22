from pcfcodec import PCFCodec, AttributeType
import argparse
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


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


def decode_if_bytes(value: Any) -> str:
    """Safely decode bytes to string if needed"""
    if isinstance(value, bytes):
        return value.decode('ascii', errors='replace')
    return str(value)


def format_value(value: Any) -> str:
    """Format a value for display"""
    if isinstance(value, tuple):
        if len(value) == 4:  # Likely a color
            return f"RGBA{value}"
        if len(value) in (2, 3, 4):  # Likely a vector
            return f"Vector{value}"
        return str(value)
    elif isinstance(value, list):
        return f"[{', '.join(format_value(v) for v in value)}]"
    elif isinstance(value, bytes):
        return f'"{decode_if_bytes(value)}"'
    return str(value)


def compare_pcf_files(pcf1_path: str, pcf2_path: str, element_filter: Optional[List[int]] = None) -> List[Difference]:
    """
    Compare two PCF files and return their differences.

    Args:
        pcf1_path: Path to first PCF file
        pcf2_path: Path to second PCF file
        element_filter: Optional list of element indices to compare

    Returns:
        List of Difference objects describing the changes
    """
    # Load PCF files
    pcf1 = PCFCodec()
    pcf2 = PCFCodec()
    pcf1.decode(pcf1_path)
    pcf2.decode(pcf2_path)

    differences: List[Difference] = []

    # Compare file versions
    if pcf1.pcf.version != pcf2.pcf.version:
        print(f"\nVersion difference:")
        print(f"  File 1: {pcf1.pcf.version}")
        print(f"  File 2: {pcf2.pcf.version}")

    # Compare string dictionaries
    if len(pcf1.pcf.string_dictionary) != len(pcf2.pcf.string_dictionary):
        print(f"\nString dictionary size difference:")
        print(f"  File 1: {len(pcf1.pcf.string_dictionary)} strings")
        print(f"  File 2: {len(pcf2.pcf.string_dictionary)} strings")

    # Compare elements
    min_elements = min(len(pcf1.pcf.elements), len(pcf2.pcf.elements))
    if len(pcf1.pcf.elements) != len(pcf2.pcf.elements):
        print(f"\nElement count difference:")
        print(f"  File 1: {len(pcf1.pcf.elements)} elements")
        print(f"  File 2: {len(pcf2.pcf.elements)} elements")

    # Helper function to get element type name
    def get_type_name(pcf: PCFCodec, element: Any) -> str:
        type_str = pcf.pcf.string_dictionary[element.type_name_index]
        return decode_if_bytes(type_str)

    # Process each element
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
                element_name=decode_if_bytes(elem1.element_name),
                attribute_name="<element_type>",
                attribute_type=AttributeType.STRING,
                old_value=type1,
                new_value=type2
            ))

        # Compare element names
        name1 = decode_if_bytes(elem1.element_name)
        name2 = decode_if_bytes(elem2.element_name)
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
                    attribute_name=decode_if_bytes(attr_name),
                    attribute_type=attr1[0] if attr1 else attr2[0],
                    old_value="<missing>" if attr1 is None else attr1[1],
                    new_value="<missing>" if attr2 is None else attr2[1]
                ))
                continue

            # Compare attribute types
            if attr1[0] != attr2[0]:
                differences.append(Difference(
                    element_index=elem_idx,
                    element_type=type1,
                    element_name=name1,
                    attribute_name=decode_if_bytes(attr_name),
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
                    attribute_name=decode_if_bytes(attr_name),
                    attribute_type=attr1[0],
                    old_value=attr1[1],
                    new_value=attr2[1]
                ))

    return differences


def main():
    parser = argparse.ArgumentParser(description='Compare two PCF files for differences')
    parser.add_argument('pcf1', help='Path to first PCF file')
    parser.add_argument('pcf2', help='Path to second PCF file')
    parser.add_argument('--element', type=int, action='append',
                        help='Element index to compare (can be specified multiple times)')
    parser.add_argument('--group-by', choices=['element', 'type', 'attribute'],
                        help='Group differences by element, type, or attribute name')
    args = parser.parse_args()

    try:
        differences = compare_pcf_files(args.pcf1, args.pcf2, args.element)

        if not differences:
            print("\nNo differences found!")
            return

        print(f"\nFound {len(differences)} differences:")

        if args.group_by == 'element':
            # Group by element index
            by_element = defaultdict(list)
            for diff in differences:
                by_element[diff.element_index].append(diff)

            for elem_idx, elem_diffs in sorted(by_element.items()):
                first_diff = elem_diffs[0]
                print(f"\nElement {elem_idx} ({first_diff.element_type})")
                print(f"Name: {first_diff.element_name}")
                for diff in elem_diffs:
                    print(f"  {diff.attribute_name}:")
                    print(f"    - {format_value(diff.old_value)}")
                    print(f"    + {format_value(diff.new_value)}")

        elif args.group_by == 'type':
            # Group by element type
            by_type = defaultdict(list)
            for diff in differences:
                by_type[diff.element_type].append(diff)

            for type_name, type_diffs in sorted(by_type.items()):
                print(f"\nType: {type_name}")
                for diff in type_diffs:
                    print(f"  Element {diff.element_index} ({diff.element_name})")
                    print(f"    {diff.attribute_name}:")
                    print(f"      - {format_value(diff.old_value)}")
                    print(f"      + {format_value(diff.new_value)}")

        elif args.group_by == 'attribute':
            # Group by attribute name
            by_attribute = defaultdict(list)
            for diff in differences:
                by_attribute[diff.attribute_name].append(diff)

            for attr_name, attr_diffs in sorted(by_attribute.items()):
                print(f"\nAttribute: {attr_name}")
                for diff in attr_diffs:
                    print(f"  Element {diff.element_index} ({diff.element_type})")
                    print(f"    - {format_value(diff.old_value)}")
                    print(f"    + {format_value(diff.new_value)}")

        else:
            # No grouping, show sequential differences
            for diff in differences:
                print(f"\nElement {diff.element_index} ({diff.element_type})")
                print(f"Name: {diff.element_name}")
                print(f"Attribute: {diff.attribute_name}")
                print(f"  - {format_value(diff.old_value)}")
                print(f"  + {format_value(diff.new_value)}")

    except Exception as e:
        print(f"Error comparing files: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
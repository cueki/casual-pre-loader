from typing import Dict, List
from models.pcf_file import PCFFile, PCFElement
from core.traversal import PCFTraversal


def get_element_structure(pcf: PCFFile, element: PCFElement) -> Dict:
    """Extract element structure while ignoring specific indices"""
    structure = {
        'type_name_index': element.type_name_index,
        'element_name': element.element_name,
        'attributes': {}
    }


    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type.value >= 0x0F:  # Array types
            if isinstance(value, list):
                # For arrays, look up the actual element names
                referenced_elements = []
                for idx in value:
                    if 0 <= idx < len(pcf.elements):
                        ref_elem = pcf.elements[idx]
                        if attr_name == b'children':
                            # For children arrays, store the actual element name
                            referenced_elements.append(ref_elem.element_name)
                        else:
                            # For other arrays, store the index for now
                            referenced_elements.append(idx)
                structure['attributes'][attr_name] = (attr_type, referenced_elements)
        else:
            # For single element references, store the referenced element name
            if attr_type.value == 0x01 and isinstance(value, int):  # ELEMENT type
                if 0 <= value < len(pcf.elements):
                    ref_elem = pcf.elements[value]
                    structure['attributes'][attr_name] = (attr_type, ref_elem.element_name)
            else:
                structure['attributes'][attr_name] = (attr_type, value)

    return structure


def verify_pcf_merge(base_pcf: PCFFile, mod_pcf: PCFFile, name_pattern: bytes = None) -> List[str]:
    """
    Verify that elements from mod_pcf are correctly merged into base_pcf.
    Args:
        base_pcf: Base PCF file after merge
        mod_pcf: Original mod PCF file
        name_pattern: Optional bytes pattern to filter element names
    Returns a list of verification messages.
    """
    messages = []

    # Build name-to-element mappings with optional filtering
    mod_elements = {
        elem.element_name: elem for elem in mod_pcf.elements
        if name_pattern is None or name_pattern in elem.element_name
    }
    base_elements = {
        elem.element_name: elem for elem in base_pcf.elements
        if name_pattern is None or name_pattern in elem.element_name
    }

    # Check each element from mod
    for name, mod_elem in mod_elements.items():
        if mod_elem.type_name_index not in [3, 38, 41]:  # Skip non-critical elements
            continue

        if name not in base_elements:
            messages.append(f"ERROR: Element {name} from mod not found in base PCF")
            continue

        base_elem = base_elements[name]
        mod_structure = get_element_structure(mod_pcf, mod_elem)
        base_structure = get_element_structure(base_pcf, base_elem)

        # Compare type indices
        if mod_structure['type_name_index'] != base_structure['type_name_index']:
            messages.append(
                f"ERROR: Type mismatch for {name}: mod={mod_structure['type_name_index']}, base={base_structure['type_name_index']}")

        # Compare attributes
        for attr_name, (mod_type, mod_value) in mod_structure['attributes'].items():
            if attr_name not in base_structure['attributes']:
                messages.append(f"ERROR: Missing attribute {attr_name} in base element {name}")
                continue

            base_type, base_value = base_structure['attributes'][attr_name]

            if mod_type != base_type:
                messages.append(
                    f"ERROR: Attribute type mismatch for {name}.{attr_name}: mod={mod_type}, base={base_type}")
                continue

            if isinstance(mod_value, list):
                # Compare referenced element names for arrays
                if attr_name == b'children':
                    # For children arrays, compare the actual element names
                    print(f"\nDebug - {name} children comparison:")
                    print(f"  Mod children:")
                    for child_name in mod_value:
                        print(f"    - {child_name.decode('ascii')}")
                    print(f"  Base children:")
                    for child_name in base_value:
                        print(f"    - {child_name.decode('ascii')}")

                    mod_refs = set(mod_value)
                    base_refs = set(base_value)
                    if mod_refs != base_refs:
                        missing = {name.decode('ascii') for name in (mod_refs - base_refs)}
                        extra = {name.decode('ascii') for name in (base_refs - mod_refs)}
                        if missing:
                            messages.append(f"ERROR: {name.decode('ascii')} missing children: {missing}")
                        if extra:
                            messages.append(f"ERROR: {name.decode('ascii')} has extra children: {extra}")
                else:
                    # For other arrays, compare element names
                    mod_refs = set(mod_value)
                    base_refs = set(base_value)
                    if mod_refs != base_refs:
                        missing = mod_refs - base_refs
                        extra = base_refs - mod_refs
                        if missing:
                            messages.append(f"ERROR: Missing references in {name}.{attr_name}: {missing}")
                        if extra:
                            messages.append(f"ERROR: Extra references in {name}.{attr_name}: {extra}")
            else:
                # Direct comparison for other values
                if mod_value != base_value:
                    messages.append(f"ERROR: Value mismatch for {name}.{attr_name}: mod={mod_value}, base={base_value}")

    if not messages:
        messages.append("All elements verified successfully")

    return messages


def print_verification(base_pcf: PCFFile, mod_pcf: PCFFile, name_pattern: str = None) -> None:
    """
    Print verification results in a readable format
    Args:
        base_pcf: Base PCF file after merge
        mod_pcf: Original mod PCF file
        name_pattern: Optional string to filter element names (will be encoded to bytes)
    """
    pattern_bytes = name_pattern.encode('ascii') if name_pattern else None
    messages = verify_pcf_merge(base_pcf, mod_pcf, pattern_bytes)
    print("\nPCF Merge Verification Results:")
    print("-" * 40)
    for msg in messages:
        print(msg)


def main():
    pass


if __name__ == "__main__":
    main()
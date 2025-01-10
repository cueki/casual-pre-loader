from typing import Dict
from models.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType
from operations.pcf_compress import get_element_hash


def find_matching_attribute(pcf: PCFFile, element: PCFElement) -> int:
    """Find matching attribute in PCF by comparing hashes. Returns index if found, -1 if not."""
    target_hash = get_element_hash(element)

    for idx, existing_elem in enumerate(pcf.elements):
        if existing_elem.type_name_index == 41:  # Only compare type 41 (attribute) elements
            if get_element_hash(existing_elem) == target_hash:
                return idx
    return -1


def build_attribute_mapping(base_pcf: PCFFile, mod_pcf: PCFFile) -> Dict[int, int]:
    """
    Build mapping of mod attribute indices to game attribute indices.
    Creates new attributes in base_pcf if they don't exist.
    Returns: Dict[mod_index, game_index]
    """
    attribute_mapping = {}

    for mod_idx, mod_elem in enumerate(mod_pcf.elements):
        if mod_elem.type_name_index != 41:  # Skip non-attribute elements
            continue

        # Try to find matching attribute in base PCF
        game_idx = find_matching_attribute(base_pcf, mod_elem)

        if game_idx >= 0:
            # Found existing attribute
            attribute_mapping[mod_idx] = game_idx
        else:
            # Need to add new attribute
            base_pcf.elements.append(mod_elem)
            new_idx = len(base_pcf.elements) - 1
            attribute_mapping[mod_idx] = new_idx
    return attribute_mapping


def update_element_attributes(element: PCFElement, attr_mapping: Dict[int, int]) -> None:
    """Update all attribute references in an element using the mapping."""
    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type == AttributeType.ELEMENT_ARRAY and isinstance(value, list):
            # Update array of attribute references
            new_indices = [attr_mapping.get(idx, idx) for idx in value]
            element.attributes[attr_name] = (attr_type, new_indices)


def is_child_element(element: PCFElement) -> bool:
    """Check if element is a child element (type 3 with empty children array)"""
    if element.type_name_index != 3:
        return False

    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_name == b'children' and value == []:
            return True
    return False


def is_parent_element(element: PCFElement) -> bool:
    """Check if element is a child element (type 3 with non-empty children array)"""
    if element.type_name_index != 3:
        return False

    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_name == b'children' and value != []:
            return True
    return False


def process_child_elements(base_pcf: PCFFile, mod_pcf: PCFFile,
                           attr_mapping: Dict[int, int]) -> Dict[bytes, int]:
    """
    Process all child elements, adding new ones if needed.
    Returns mapping of element names to their indices.
    """
    name_to_idx = {}

    for mod_elem in mod_pcf.elements:
        if not is_child_element(mod_elem):
            continue

        # Update attribute references in the child element
        update_element_attributes(mod_elem, attr_mapping)

        # Try to find matching child in base PCF
        for idx, base_elem in enumerate(base_pcf.elements):
            if base_elem.element_name == mod_elem.element_name and base_elem.type_name_index == 3:
                # Update existing child
                base_pcf.elements[idx] = mod_elem
                name_to_idx[mod_elem.element_name] = idx
                break
        else:
            # Add new child element
            base_pcf.elements.append(mod_elem)
            name_to_idx[mod_elem.element_name] = len(base_pcf.elements) - 1

    return name_to_idx


def find_linker_index(pcf: PCFFile, child_name: bytes) -> int:
    """Find the index of the linker element (type 38) that points to a child with given name."""
    for idx, element in enumerate(pcf.elements):
        if element.type_name_index == 38:  # Linker element
            # Check if this linker points to our target child
            for attr_name, (attr_type, value) in element.attributes.items():
                if attr_type == AttributeType.ELEMENT:
                    target_elem = pcf.elements[value]
                    if target_elem.element_name == child_name:
                        return idx
    return -1


def merge_pcf_elements(base_pcf: PCFFile, mod_pcf: PCFFile) -> PCFFile:
    """
    Merge elements from mod_pcf into base_pcf.
    1. Build mapping of attribute indices
    2. Process child elements and update their attributes
    3. Update parent elements with new child indices
    """
    # First pass: Build attribute mapping
    attr_mapping = build_attribute_mapping(base_pcf, mod_pcf)

    # Second pass: Process child elements
    process_child_elements(base_pcf, mod_pcf, attr_mapping)
    # Final pass: Update parent elements
    for mod_elem in mod_pcf.elements:
        if not is_parent_element(mod_elem):  # Skip non-parent elements
            continue

        # Update attribute references
        update_element_attributes(mod_elem, attr_mapping)

        # # Get child names and find their new indices
        for attr_name, (attr_type, value) in mod_elem.attributes.items():
            if attr_name == b'children':
                # Get child names from original indices
                child_names = [mod_pcf.elements[idx].element_name for idx in value]
                # Map names to new indices
                new_children = [find_linker_index(base_pcf, name) for name in child_names]
                mod_elem.attributes[attr_name] = (attr_type, new_children)
                break

        # # # Update parent element in base PCF
        for idx, base_elem in enumerate(base_pcf.elements):
            if base_elem.element_name == mod_elem.element_name:
                base_pcf.elements[idx] = mod_elem
                break

    result_pcf = base_pcf
    return base_pcf
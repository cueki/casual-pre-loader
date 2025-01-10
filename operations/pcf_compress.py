import copy
from typing import List, Dict
from core.constants import AttributeType
from models.pcf_file import PCFFile, PCFElement


def get_element_hash(element: PCFElement) -> str:
    """Create a hash of element attributes for comparison."""
    sorted_attrs = sorted(
        (name.decode('ascii'), type_, str(value))
        for name, (type_, value) in element.attributes.items()
    )
    return str(sorted_attrs)


def find_duplicate_array_elements(pcf: PCFFile) -> Dict[str, List[int]]:
    """Find duplicate elements referenced in array attributes."""
    hash_to_indices = {}

    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                for idx in value:
                    if idx < len(pcf.elements):
                        referenced_element = pcf.elements[idx]
                        if referenced_element.type_name_index == 41:
                            element_hash = get_element_hash(referenced_element)
                            if element_hash not in hash_to_indices:
                                hash_to_indices[element_hash] = []
                            hash_to_indices[element_hash].append(idx)

    return {hash_: indices for hash_, indices in hash_to_indices.items() if len(indices) > 1}


def update_array_indices(pcf: PCFFile, duplicates: Dict[str, List[int]]):
    """
    Update ELEMENT_ARRAY indices to reuse the first occurrence of duplicate elements.
    """
    # Create a mapping of old indices to their replacement
    index_map = {}
    for indices in duplicates.values():
        first_index = indices[0]  # Keep the first occurrence
        # Map all other indices to the first one
        for idx in indices[1:]:
            index_map[idx] = first_index

    # Update all ELEMENT_ARRAY attributes in the PCF
    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                # Update indices in the array
                new_value = [index_map.get(idx, idx) for idx in value]
                element.attributes[attr_name] = (attr_type, new_value)


def nullify_unused_elements(pcf: PCFFile, duplicates):
    # Get all indices that are duplicates (excluding the first occurrence)
    unused_indices = []
    for indices in duplicates.values():
        unused_indices.extend(indices[1:])

    # For each unused index, rename while preserving length
    for i, idx in enumerate(unused_indices):
        original_element = pcf.elements[idx]
        original_name = original_element.element_name
        new_name = f"unused".encode('ascii')

        # Calculate padding needed
        padding_length = len(original_name) - len(new_name)
        if padding_length < 0:
            print(f"Warning: New name 'unused{i + 1}' is longer than original name {original_name}, skipping")
            continue

        # Add null byte padding to maintain length
        padded_name = new_name + (b'\x20' * padding_length)

        # Update the element name while preserving everything else
        original_element.element_name = padded_name


def reorder_elements(pcf: PCFFile, duplicates: Dict[str, List[int]]):
    """Reorder elements to be sequential while preserving hierarchy."""
    # Get indices of all duplicate elements (except first occurrences)
    duplicate_indices = set()
    for indices in duplicates.values():
        duplicate_indices.update(indices[1:])

    # Create new list without duplicates and mapping of old to new indices
    new_elements = []
    old_to_new = {}
    new_index = 0

    # Process elements in order
    for old_index, element in enumerate(pcf.elements):
        if old_index not in duplicate_indices:
            old_to_new[old_index] = new_index
            new_elements.append(element)
            new_index += 1

    # Update all references in every element
    for element in new_elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                # Map each index to its new position
                new_value = []
                for idx in value:
                    # If it's a duplicate, use the index of first occurrence
                    if idx in duplicate_indices:
                        for indices in duplicates.values():
                            if idx in indices:
                                idx = indices[0]
                                break
                    new_value.append(old_to_new[idx])
                element.attributes[attr_name] = (attr_type, new_value)
            elif attr_type == AttributeType.ELEMENT:
                # Handle single element references
                if value in duplicate_indices:
                    for indices in duplicates.values():
                        if value in indices:
                            value = indices[0]
                            break
                element.attributes[attr_name] = (attr_type, old_to_new[value])

    # Replace the elements list with our reordered version
    pcf.elements = new_elements


def compress_duplicate_elements(pcf: PCFFile) -> PCFFile:
    # Create copy to avoid modifying original
    result_pcf = copy.deepcopy(pcf)

    # Find duplicates
    duplicates = find_duplicate_array_elements(result_pcf)

    if duplicates:
        update_array_indices(result_pcf, duplicates)
        nullify_unused_elements(result_pcf, duplicates)
        reorder_elements(result_pcf, duplicates)
    else:
        print("No duplicates found")

    return result_pcf
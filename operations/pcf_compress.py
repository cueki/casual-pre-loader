import copy
from core.constants import AttributeType, DEFAULTS
from models.pcf_file import PCFFile, PCFElement


def get_element_hash(element: PCFElement):
    # first sort by name only
    sorted_names = sorted(element.attributes.keys(), key=lambda x: x.decode('ascii'))

    # build hash using sorted names
    attr_strings = []
    for name in sorted_names:
        type_, value = element.attributes[name]
        attr_strings.append(f"{name.decode('ascii')}:{type_}:{value}")

    return "|".join(attr_strings)


def find_duplicate_array_elements(pcf: PCFFile):
    # find duplicate elements referenced in array attributes
    # print("\nElement types in file:")
    # for i, element in enumerate(pcf.elements):
    #     print(f"Element {i}: type_name_index={element.type_name_index} name={element.element_name}")
    hash_to_indices = {}

    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                for idx in value:
                    if idx < len(pcf.elements):
                        referenced_element = pcf.elements[idx]
                        if referenced_element.type_name_index not in (0, 3):
                            element_hash = get_element_hash(referenced_element)
                            if element_hash not in hash_to_indices:
                                hash_to_indices[element_hash] = []
                            hash_to_indices[element_hash].append(idx)

    return {hash_: indices for hash_, indices in hash_to_indices.items() if len(indices) > 1}


def update_array_indices(pcf: PCFFile, duplicates):
    # update ELEMENT_ARRAY indices to reuse the first occurrence of duplicate elements.
    # create a mapping of old indices to their replacement
    index_map = {}
    for indices in duplicates.values():
        first_index = indices[0]  # keep the first occurrence
        # map all other indices to the first one
        for idx in indices[1:]:
            index_map[idx] = first_index

    # update all ELEMENT_ARRAY attributes in the PCF
    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                # update indices in the array
                new_value = [index_map.get(idx, idx) for idx in value]
                element.attributes[attr_name] = (attr_type, new_value)


def reorder_elements(pcf: PCFFile, duplicates):
    # get indices of all duplicate elements (except first occurrences)
    duplicate_indices = set()
    for indices in duplicates.values():
        duplicate_indices.update(indices[1:])

    # create new list without duplicates and mapping of old to new indices
    new_elements = []
    old_to_new = {}
    new_index = 0

    # process elements in order
    for old_index, element in enumerate(pcf.elements):
        if old_index not in duplicate_indices:
            old_to_new[old_index] = new_index
            new_elements.append(element)
            new_index += 1

    # update all references in every element
    for element in new_elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                # map each index to its new position
                new_value = []
                for idx in value:
                    # if it's a duplicate, use the index of first occurrence
                    if idx in duplicate_indices:
                        for indices in duplicates.values():
                            if idx in indices:
                                idx = indices[0]
                                break
                    new_value.append(old_to_new[idx])
                element.attributes[attr_name] = (attr_type, new_value)
            elif attr_type == AttributeType.ELEMENT:
                # handle single element references
                if value in duplicate_indices:
                    for indices in duplicates.values():
                        if value in indices:
                            value = indices[0]
                            break
                element.attributes[attr_name] = (attr_type, old_to_new[value])

    # replace the elements list with our reordered version
    pcf.elements = new_elements


def rename_child_elements(pcf: PCFFile):
    for i, element in enumerate(pcf.elements):
        if element.type_name_index == 41:
            element.element_name = str(i).encode('ascii')


def check_and_remove_defaults(pcf: PCFFile):
    """Remove any attributes that match the system defaults"""
    removed_count = 0

    for element in pcf.elements:
        attributes_to_remove = []

        for attr_name, (attr_type, value) in element.attributes.items():
            # Convert attribute name from bytes to string for comparison
            attr_name_str = attr_name.decode('ascii')

            # Check against each default
            for default_name, default_value in DEFAULTS:
                if attr_name_str == default_name:
                    # Handle special cases for different types
                    matches_default = False

                    if isinstance(default_value, (int, float, bool)):
                        matches_default = value == default_value
                    elif isinstance(default_value, tuple):
                        # Handle Vector3 and Color
                        if len(default_value) in (3, 4):
                            matches_default = value == default_value
                    elif isinstance(default_value, bytes):
                        # Handle string comparisons
                        matches_default = value == default_value

                    if matches_default:
                        attributes_to_remove.append(attr_name)
                        removed_count += 1
                        break

        # Remove all identified default attributes
        for attr_name in attributes_to_remove:
            del element.attributes[attr_name]

    return removed_count


def remove_duplicate_elements(pcf: PCFFile) -> PCFFile:
    # create copy to avoid modifying original
    result_pcf = copy.deepcopy(pcf)

    # find duplicates
    duplicates = find_duplicate_array_elements(result_pcf)

    if duplicates:
        update_array_indices(result_pcf, duplicates)
        reorder_elements(result_pcf, duplicates)
        rename_child_elements(result_pcf)
        num_removed = check_and_remove_defaults(result_pcf)
        print(f"Removed {num_removed} redundant default attributes")
    else:
        print("No duplicates found")

    return result_pcf

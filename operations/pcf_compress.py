import copy
from core.constants import AttributeType, ELEMENT_DEFAULTS, ATTRIBUTE_DEFAULTS
from parsers.pcf_file import PCFFile, PCFElement


def get_element_hash(element: PCFElement):
    # first sort by name only
    sorted_names = sorted(element.attributes.keys(), key=lambda x: x.decode('ascii'))

    # build hash using sorted names
    attr_strings = []
    for name in sorted_names:
        type_, value = element.attributes[name]
        attr_strings.append(f"{name.decode('ascii')}:{type_}:{value}")

    return "|".join(attr_strings)


def fix_child_references(pcf: PCFFile) -> bool:
    # this is just in case there are some invalid references, I only saw this once but better safe than sorry
    # first map all particle system definitions by name
    system_indices = {}
    for i, element in enumerate(pcf.elements):
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')
        if type_name == 'DmeParticleSystemDefinition':
            name = element.element_name.decode('ascii')
            system_indices[name] = i

    # look for DmeParticleChild elements that need fixing
    changes_made = False
    for i, element in enumerate(pcf.elements):
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')
        if type_name == 'DmeParticleChild':
            if b'child' in element.attributes:
                attr_type, value = element.attributes[b'child']
                if value == 4294967295:  # invalid reference
                    name = element.element_name.decode('ascii')
                    if name in system_indices:
                        element.attributes[b'child'] = (attr_type, system_indices[name])
                        changes_made = True

    return changes_made


def clean_children_arrays(pcf: PCFFile) -> bool:
    # this removes any duplicate children from the array, if they exist, also only saw this once
    changes_made = False

    for element in pcf.elements:
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')
        if type_name == 'DmeParticleSystemDefinition':
            if b'children' in element.attributes:
                attr_type, value = element.attributes[b'children']
                # convert to set to remove duplicates and back to list
                unique_indices = list(dict.fromkeys(value))  # preserves order
                if len(unique_indices) != len(value):
                    element.attributes[b'children'] = (attr_type, unique_indices)
                    changes_made = True

    return changes_made


def find_duplicate_array_elements(pcf: PCFFile):
    # find duplicate elements referenced in array attributes
    hash_to_indices = {}

    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                for idx in value:
                    if idx < len(pcf.elements):
                        referenced_element = pcf.elements[idx]
                        ref_type_name = pcf.string_dictionary[referenced_element.type_name_index].decode('ascii')
                        if ref_type_name not in ('DmeElement', 'DmeParticleSystemDefinition'):
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


def rename_operators(pcf: PCFFile):
    # this sets the operators name to '' because the name doesn't matter, only the index does
    for i, element in enumerate(pcf.elements):
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')
        if type_name == 'DmeParticleOperator':
            element.element_name = str('').encode('ascii')


def check_and_remove_defaults(pcf: PCFFile):
    # this removes all redundant default attributes, the defaults can be found in core/constants.py
    removed_count = 0

    for element in pcf.elements:
        attributes_to_remove = []

        # get the element type name from string dictionary
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')

        # determine which defaults to check
        defaults_to_check = []
        if type_name == 'DmeParticleOperator':
            defaults_to_check.extend(ATTRIBUTE_DEFAULTS)
        elif type_name == 'DmeParticleSystemDefinition':
            defaults_to_check.extend(ELEMENT_DEFAULTS)

        for attr_name, (attr_type, value) in element.attributes.items():
            attr_name_str = attr_name.decode('ascii')

            # check against each default
            for default_name, default_value in defaults_to_check:
                if attr_name_str == default_name:
                    matches_default = False

                    if isinstance(default_value, (int, float, bool)):
                        matches_default = value == default_value
                    elif isinstance(default_value, tuple):
                        # handle vector
                        if len(default_value) in (3, 4):
                            matches_default = value == default_value
                    elif isinstance(default_value, bytes):
                        # handle string comparisons
                        matches_default = value == default_value

                    if matches_default:
                        attributes_to_remove.append(attr_name)
                        removed_count += 1
                        break

        # remove all identified default attributes
        for attr_name in attributes_to_remove:
            del element.attributes[attr_name]

    return removed_count


def remove_duplicate_elements(pcf: PCFFile) -> PCFFile:
    # work with copy
    result_pcf = copy.deepcopy(pcf)

    # just in case
    fix_child_references(result_pcf)

    # find duplicates
    duplicates = find_duplicate_array_elements(result_pcf)

    if duplicates:
        update_array_indices(result_pcf, duplicates)
        reorder_elements(result_pcf, duplicates)
        rename_operators(result_pcf)
        check_and_remove_defaults(result_pcf)
        clean_children_arrays(result_pcf)
    else:
        print("No duplicates found")

    return result_pcf

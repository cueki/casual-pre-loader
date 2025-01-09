from typing import List, Dict
from core.constants import AttributeType
from models.pcf_file import PCFFile, PCFElement


def find_particle_system(pcf: PCFFile, system_name: str):
    system_name_bytes = system_name.encode('ascii')
    for element in pcf.elements:
        if (element.type_name_index == 3 and  # 3 is for particle system definitions, 41 for attributes
                element.element_name == system_name_bytes):
            return element
    return None


def find_childless_particle_systems(pcf: PCFFile):
    childless_systems = []

    for element in pcf.elements:
        if element.type_name_index == 3:
            for attr_name, (attr_type, value) in element.attributes.items():
                if attr_name == b'children':
                    if not value:  # we don't want to be messing with the parent elements
                        name = element.element_name.decode('ascii')
                        childless_systems.append(name)

    return childless_systems


def get_referenced_elements(pcf: PCFFile, element: PCFElement) -> Dict[str, List[PCFElement]]:
    # this gets the nested elements for a particleSystemDefinition from the array based on index provided in array
    references = {}

    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type == AttributeType.ELEMENT_ARRAY:
            name = attr_name.decode('ascii')
            references[name] = []
            for idx in value:
                if 0 <= idx < len(pcf.elements):
                    references[name].append(pcf.elements[idx])

    return references


def format_value(value: any) -> str:
    # decode for comparison
    if isinstance(value, bytes):
        return value.decode('ascii', errors='replace')
    elif isinstance(value, (tuple, list)) and len(value) == 4:  # Likely a color
        return f"RGBA{value}"
    return str(value)


def get_element_attributes(element: PCFElement):
    # make dict of {name: [type, value]}, skip ELEMENT_ARRAY's because they don't matter in this context
    attributes = {}
    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type != AttributeType.ELEMENT_ARRAY:
            name = attr_name.decode('ascii')
            formatted_value = format_value(value)
            attributes[name] = (attr_type, formatted_value)
    return attributes


def compare_elements(elem1: PCFElement, elem2: PCFElement) -> Dict[str, dict]:
    # make a set of the attributes from both particle systems
    attrs1 = get_element_attributes(elem1)
    attrs2 = get_element_attributes(elem2)
    all_attrs = set(attrs1.keys()) | set(attrs2.keys())

    differences = {}

    for attr in all_attrs:
        # find the attributes that don't show up in both particleSystemDefinitions
        if attr not in attrs1:
            differences[attr] = {'status': 'missing_in_first', 'value': attrs2[attr]}
        elif attr not in attrs2:
            differences[attr] = {'status': 'missing_in_second', 'value': attrs1[attr]}
        # find where the attributes with the same name have different values
        elif attrs1[attr] != attrs2[attr]:
            differences[attr] = {
                'status': 'different',
                'first': attrs1[attr],
                'second': attrs2[attr]
            }

    return differences


def print_differences(differences: Dict[str, dict]) -> str:
    # Returns a string instead of printing directly
    output = []
    indent = "  "

    if not differences:
        return f"{indent}[Identical]"

    for attr, diff in differences.items():
        if diff['status'] == 'different':
            output.append(f"{indent}{attr}:")
            output.append(f"{indent}  File 1: {diff['first'][1]}")
            output.append(f"{indent}  File 2: {diff['second'][1]}")
        elif diff['status'] == 'missing_in_first':
            output.append(f"{indent}{attr}: [Only in file 2] {diff['value'][1]}")
        elif diff['status'] == 'missing_in_second':
            output.append(f"{indent}{attr}: [Only in file 1] {diff['value'][1]}")

    return '\n'.join(output)


def compare_particle_systems(pcf1: PCFFile, pcf2: PCFFile, particle_system_name: str):
    system1 = find_particle_system(pcf1, particle_system_name)
    system2 = find_particle_system(pcf2, particle_system_name)
    print(f"Comparing {particle_system_name}")

    if not system1 or not system2:
        print(f"Particle system '{particle_system_name}' not found in {'first' if not system1 else 'second'} file")
        return

    # Compare base particle system attributes
    base_differences = compare_elements(system1, system2)
    if base_differences:
        print("\nBASE ATTRIBUTES:")
        print(print_differences(base_differences))

    # Get referenced elements from both systems
    refs1 = get_referenced_elements(pcf1, system1)
    refs2 = get_referenced_elements(pcf2, system2)

    # Compare categories
    all_categories = set(refs1.keys()) | set(refs2.keys())

    for category in sorted(all_categories):
        category_has_differences = False
        category_output = [f"\n{category.upper()}:"]

        if category not in refs1:
            category_output.append(f"  [Category only exists in second file]")
            print('\n'.join(category_output))
            continue
        if category not in refs2:
            category_output.append(f"  [Category only exists in first file]")
            print('\n'.join(category_output))
            continue

        elements1 = refs1[category]
        elements2 = refs2[category]

        # Create maps of element names to elements for easier comparison
        elem_map1 = {e.element_name.decode('ascii'): e for e in elements1}
        elem_map2 = {e.element_name.decode('ascii'): e for e in elements2}

        all_names = set(elem_map1.keys()) | set(elem_map2.keys())

        for name in sorted(all_names):
            element_output = []

            if name not in elem_map1:
                category_has_differences = True
                element_output.extend([f"\nElement: {name}", "  [Only exists in second file]"])
            elif name not in elem_map2:
                category_has_differences = True
                element_output.extend([f"\nElement: {name}", "  [Only exists in first file]"])
            else:
                # Compare elements and their attributes
                differences = compare_elements(elem_map1[name], elem_map2[name])
                if differences:
                    category_has_differences = True
                    element_output.append(f"Element: {name}")
                    element_output.extend([f"  {line}" for line in str(print_differences(differences)).splitlines()])

            if element_output:
                category_output.extend(element_output)

        if category_has_differences:
            print('\n'.join(category_output))


def get_element_hash(element: PCFElement) -> str:
    """Create a hash of element attributes for comparison."""
    sorted_attrs = sorted(
        (name.decode('ascii'), type_, str(value))
        for name, (type_, value) in element.attributes.items()
    )
    return str(sorted_attrs)


def find_duplicate_array_elements(pcf: PCFFile) -> Dict[str, List[int]]:
    """
    Find duplicate elements referenced in array attributes, where element.type_name_index == 41.
    Returns a dictionary of attribute hashes mapping to lists of element indices.
    Only includes entries with more than one index (actual duplicates).
    """
    # Dictionary to store hash -> [element indices]
    hash_to_indices = {}

    # Examine each element in the PCF
    for element in pcf.elements:
        # Look through all attributes
        for attr_name, (attr_type, value) in element.attributes.items():
            # Check if it's an element array
            if attr_type == AttributeType.ELEMENT_ARRAY:
                # Check each referenced element index
                for idx in value:
                    if idx < len(pcf.elements):
                        referenced_element = pcf.elements[idx]
                        # Check if referenced element is type 41
                        if referenced_element.type_name_index == 41:
                            element_hash = get_element_hash(referenced_element)
                            if element_hash not in hash_to_indices:
                                hash_to_indices[element_hash] = []
                            hash_to_indices[element_hash].append(idx)

    # Filter to only include duplicates
    duplicates = {
        hash_: indices
        for hash_, indices in hash_to_indices.items()
        if len(indices) > 1
    }

    return duplicates


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


def find_used_elements(pcf: PCFFile) -> set:
    """Find indices of elements that are referenced in ELEMENT_ARRAY attributes."""
    used_indices = set()

    for element in pcf.elements:
        for _, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                used_indices.update(value)
            elif attr_type == AttributeType.ELEMENT:
                used_indices.add(value)

    return used_indices


def reorder_elements(pcf: PCFFile):
    """Reorder elements to be sequential, updating all references."""
    # Find which elements are actually used
    used_indices = find_used_elements(pcf)

    # Create mapping of old indices to new indices
    old_to_new = {}
    new_index = 0

    for old_index in range(len(pcf.elements)):
        if old_index in used_indices:
            old_to_new[old_index] = new_index
            new_index += 1

    # Create new elements list in correct order
    new_elements = []
    for old_index, element in enumerate(pcf.elements):
        if old_index in used_indices:
            new_elements.append(element)

    # Update all references in ELEMENT_ARRAY attributes
    for element in new_elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT_ARRAY:
                new_value = [old_to_new[idx] for idx in value]
                element.attributes[attr_name] = (attr_type, new_value)
            elif attr_type == AttributeType.ELEMENT:
                new_value = old_to_new[value]
                element.attributes[attr_name] = (attr_type, new_value)

    # Replace elements list with reordered one
    pcf.elements = new_elements

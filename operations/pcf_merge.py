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


if __name__ == "__main__":
    pcf_game = PCFFile("../medicgun_beam.pcf")
    pcf_mod = PCFFile("../medicgun_beam_mod.pcf")
    pcf_game.decode()
    pcf_mod.decode()
    particle_systems = find_childless_particle_systems(pcf_game)
    for system in particle_systems:
        compare_particle_systems(pcf_game, pcf_mod, system)

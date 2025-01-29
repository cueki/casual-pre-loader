import json
from pathlib import Path
from typing import Set, List, Dict
from parsers.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType


def find_child_elements(pcf: PCFFile, element_idx: int, visited: Set[int]):
    if element_idx in visited:
        return set()

    visited.add(element_idx)
    children = set()
    element = pcf.elements[element_idx]

    # check if this is a DmeParticleChild
    type_name = pcf.string_dictionary[element.type_name_index]
    if type_name == b'DmeParticleChild':
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT:
                if value != 4294967295:
                    children.add(value)
                    children.update(find_child_elements(pcf, value, visited))

    # handle ELEMENT_ARRAY attributes
    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type == AttributeType.ELEMENT_ARRAY:
            for child_idx in value:
                if child_idx != 4294967295:
                    children.add(child_idx)
                    children.update(find_child_elements(pcf, child_idx, visited))

    return children


def find_element_by_name(pcf: PCFFile, element_name: str):
    element_name_bytes = element_name.encode('ascii')
    for idx, element in enumerate(pcf.elements):
        if element.element_name == element_name_bytes:
            return idx
    return None


def extract_element_tree(pcf: PCFFile, element_idx: int) -> Dict[int, PCFElement]:
    visited = set()
    tree = {element_idx: pcf.elements[element_idx]}
    children = find_child_elements(pcf, element_idx, visited)

    for child_idx in children:
        tree[child_idx] = pcf.elements[child_idx]

    return tree


def get_pcf_element_names(pcf: PCFFile) -> List[str]:
    names = []
    for element in pcf.elements:
        type_name = pcf.string_dictionary[element.type_name_index]
        if type_name == b'DmeParticleSystemDefinition':
            names.append(element.element_name.decode('ascii'))
    return names


def build_reverse_element_map(particle_system_map: Dict[str, List[str]]) -> Dict[str, str]:
    element_to_pcf = {}
    for pcf_file, elements in particle_system_map.items():
        for element in elements:
            element_to_pcf[element] = pcf_file
    return element_to_pcf


def rebuild_particle_files(mod_pcf_path: str, game_pcf_dir: str, particle_system_map) -> Dict[str, PCFFile]:

    # Load the mod PCF
    mod_pcf = PCFFile(mod_pcf_path).decode()

    # Get all element names from the mod PCF
    mod_elements = get_pcf_element_names(mod_pcf)

    # Build reverse mapping of elements to PCF files
    element_to_pcf = build_reverse_element_map(particle_system_map)

    # Group mod elements by their target PCF files
    pcf_to_elements: Dict[str, Set[str]] = {}
    for element in mod_elements:
        if element in element_to_pcf:
            target_pcf = element_to_pcf[element]
            if target_pcf not in pcf_to_elements:
                pcf_to_elements[target_pcf] = set()
            pcf_to_elements[target_pcf].add(element)

    # For each affected PCF file, rebuild it with the mod elements
    rebuilt_pcfs = {}
    for target_pcf, mod_element_names in pcf_to_elements.items():
        print(f"Rebuilding {target_pcf} with elements: {mod_element_names}")

        # Load the original game PCF
        game_pcf_path = Path(game_pcf_dir) / target_pcf
        game_pcf = PCFFile(str(game_pcf_path)).decode()

        # Create new PCF with same version as mod
        new_pcf = PCFFile(mod_pcf_path, version=mod_pcf.version)
        new_pcf.string_dictionary = mod_pcf.string_dictionary.copy()

        # Start with root element
        elements_to_keep = {0: game_pcf.elements[0]}  # Use game PCF's root

        # Get all required elements for this PCF
        required_elements = set(particle_system_map[target_pcf])

        # Process each required element
        for element_name in required_elements:
            # Determine source PCF based on whether it's in mod elements
            if element_name in mod_element_names:
                element_idx = find_element_by_name(mod_pcf, element_name)
                source_pcf = mod_pcf
            else:
                element_idx = find_element_by_name(game_pcf, element_name)
                source_pcf = game_pcf

                # If not found in either, raise error
                if element_idx is None:
                    raise ValueError(f"Element {element_name} not found in either mod or game PCF")

                # If using game PCF, ensure its string dictionary entries exist in our PCF
                for string in game_pcf.string_dictionary:
                    if string not in new_pcf.string_dictionary:
                        new_pcf.string_dictionary.append(string)

            # Extract the element and its children
            element_tree = extract_element_tree(source_pcf, element_idx)

            # Add elements to our collection
            for old_idx, element in element_tree.items():
                if old_idx not in elements_to_keep:
                    elements_to_keep[old_idx] = element

        # Create mapping of old indices to new sequential indices
        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(elements_to_keep.keys())}

        # Build new elements list with updated references
        new_elements = []
        for old_idx, element in elements_to_keep.items():
            new_element = PCFElement(
                type_name_index=element.type_name_index,
                element_name=element.element_name,
                data_signature=element.data_signature,
                attributes={}
            )

            # Update element references in attributes
            for attr_name, (attr_type, value) in element.attributes.items():
                if attr_type == AttributeType.ELEMENT:
                    if value != 4294967295 and value in old_to_new:
                        new_element.attributes[attr_name] = (attr_type, old_to_new[value])
                    else:
                        new_element.attributes[attr_name] = (attr_type, value)
                elif attr_type == AttributeType.ELEMENT_ARRAY:
                    new_value = []
                    for idx in value:
                        if idx != 4294967295 and idx in old_to_new:
                            new_value.append(old_to_new[idx])
                        else:
                            new_value.append(idx)
                    new_element.attributes[attr_name] = (attr_type, new_value)
                else:
                    new_element.attributes[attr_name] = (attr_type, value)

            new_elements.append(new_element)

        # Update root element's particleSystemDefinitions array
        root = new_elements[0]
        attr_type, _ = root.attributes[b'particleSystemDefinitions']

        # Add all particle system elements to root's definitions
        particle_system_indices = []
        for idx, element in enumerate(new_elements[1:], 1):  # Skip root element
            type_name = new_pcf.string_dictionary[element.type_name_index]
            if type_name == b'DmeParticleSystemDefinition':
                particle_system_indices.append(idx)

        root.attributes[b'particleSystemDefinitions'] = (attr_type, particle_system_indices)

        new_pcf.elements = new_elements
        rebuilt_pcfs[target_pcf] = new_pcf

    return rebuilt_pcfs


def load_particle_system_map(map_path: str) -> Dict[str, List[str]]:
    with open(map_path, 'r') as f:
        return json.load(f)
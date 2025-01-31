import json
from pathlib import Path
from typing import Set, List, Dict
from operations.pcf_merge import merge_pcf_files
from parsers.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType


def load_particle_system_map(map_path: str) -> Dict[str, List[str]]:
    with open(map_path, 'r') as f:
        return json.load(f)


def find_child_elements(pcf: PCFFile, element_idx: int, visited: Set[int]) -> Set[int]:
    # find all child elements of a given element index
    if element_idx in visited:
        return set()

    visited.add(element_idx)
    children = set()
    element = pcf.elements[element_idx]

    # check if this is a DmeParticleChild which uses a single ELEMENT type for child reference
    type_name = pcf.string_dictionary[element.type_name_index]
    if type_name == b'DmeParticleChild':
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT:
                if value != 4294967295:
                    children.add(value)
                    children.update(find_child_elements(pcf, value, visited))

    # handle regular ELEMENT_ARRAY attributes for all elements
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
    # extract an element and all its children from a PCF file.
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


def build_reverse_element_map(particle_system_map) -> Dict[str, str]:
    element_to_pcf = {}
    for pcf_file, elements in particle_system_map.items():
        for element in elements:
            element_to_pcf[element] = pcf_file
    return element_to_pcf


def rebuild_particle_files(mod_pcf_path: str, game_pcf_dir: str, particle_system_map) -> list[PCFFile]:
    # load the mod PCF
    mod_pcf = PCFFile(mod_pcf_path).decode()

    # get all element names from the mod PCF
    mod_elements = get_pcf_element_names(mod_pcf)

    # build reverse mapping of elements to PCF files
    element_to_pcf = build_reverse_element_map(particle_system_map)

    # list for output
    rebuilt_particle_files = []

    # group mod elements by their target PCF files
    pcf_to_elements = {}
    for element in mod_elements:
        if element in element_to_pcf:
            target_pcf = element_to_pcf[element]
            if target_pcf not in pcf_to_elements:
                pcf_to_elements[target_pcf] = set()
            pcf_to_elements[target_pcf].add(element)

    # for each PCF file, save mod and game elements separately
    for target_pcf, mod_element_names in pcf_to_elements.items():
        # load the original game PCF
        game_pcf_path = Path(game_pcf_dir) / target_pcf
        game_pcf = PCFFile(str(game_pcf_path)).decode()
        mod_pcf_output = PCFFile(mod_pcf_path, version=mod_pcf.version)
        mod_pcf_output.string_dictionary = mod_pcf.string_dictionary

        # start with the root element (index 0) from the mod PCF
        mod_elements_to_keep = {0: mod_pcf.elements[0]}

        # extract mod elements and their children
        for element_name in mod_element_names:
            element_idx = find_element_by_name(mod_pcf, element_name)
            if element_idx is not None:
                element_tree = extract_element_tree(mod_pcf, element_idx)
                mod_elements_to_keep.update(element_tree)

        # create mapping of old indices to new sequential indices for mod elements
        mod_old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(mod_elements_to_keep.keys())}

        # build new elements list for mod PCF
        mod_new_elements = []
        for old_idx, element in mod_elements_to_keep.items():
            new_element = PCFElement(
                type_name_index=element.type_name_index,
                element_name=element.element_name,
                data_signature=element.data_signature,
                attributes={}
            )

            # update element references
            for attr_name, (attr_type, value) in element.attributes.items():
                # single element
                if attr_type == AttributeType.ELEMENT:
                    if value != 4294967295 and value in mod_old_to_new:
                        new_element.attributes[attr_name] = (attr_type, mod_old_to_new[value])
                    else:
                        new_element.attributes[attr_name] = (attr_type, value)
                # element array
                elif attr_type == AttributeType.ELEMENT_ARRAY:
                    new_value = []
                    for idx in value:
                        if idx != 4294967295 and idx in mod_old_to_new:
                            new_value.append(mod_old_to_new[idx])
                        else:
                            new_value.append(idx)
                    new_element.attributes[attr_name] = (attr_type, new_value)
                else:
                    new_element.attributes[attr_name] = (attr_type, value)

            mod_new_elements.append(new_element)

        # update root particleSystemDefinitions array
        root = mod_new_elements[0]
        attr_type, _ = root.attributes[b'particleSystemDefinitions']

        # add all particle system elements to root's definitions
        particle_system_indices = []
        for idx, element in enumerate(mod_new_elements[1:], 1):  # skip root element
            type_name = mod_pcf_output.string_dictionary[element.type_name_index]
            if type_name == b'DmeParticleSystemDefinition':
                particle_system_indices.append(idx)

        root.attributes[b'particleSystemDefinitions'] = (attr_type, particle_system_indices)

        # this is our stripped mod elements all in one PCF object
        mod_pcf_output.elements = mod_new_elements

        # now we load the game's version
        game_pcf_output = PCFFile(str(game_pcf_path), version=game_pcf.version)
        game_pcf_output.string_dictionary = game_pcf.string_dictionary

        # from here onward it's the same as above but just with game files
        game_elements_to_keep = {0: game_pcf.elements[0]}

        for element_name in particle_system_map[target_pcf]:
            if element_name not in mod_element_names:
                element_idx = find_element_by_name(game_pcf, element_name)
                if element_idx is not None:
                    element_tree = extract_element_tree(game_pcf, element_idx)
                    game_elements_to_keep.update(element_tree)

        game_old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(game_elements_to_keep.keys())}

        game_new_elements = []
        for old_idx, element in game_elements_to_keep.items():
            new_element = PCFElement(
                type_name_index=element.type_name_index,
                element_name=element.element_name,
                data_signature=element.data_signature,
                attributes={}
            )

            for attr_name, (attr_type, value) in element.attributes.items():
                if attr_type == AttributeType.ELEMENT:
                    if value != 4294967295 and value in game_old_to_new:
                        new_element.attributes[attr_name] = (attr_type, game_old_to_new[value])
                    else:
                        new_element.attributes[attr_name] = (attr_type, value)
                elif attr_type == AttributeType.ELEMENT_ARRAY:
                    new_value = []
                    for idx in value:
                        if idx != 4294967295 and idx in game_old_to_new:
                            new_value.append(game_old_to_new[idx])
                        else:
                            new_value.append(idx)
                    new_element.attributes[attr_name] = (attr_type, new_value)
                else:
                    new_element.attributes[attr_name] = (attr_type, value)

            game_new_elements.append(new_element)

        root = game_new_elements[0]
        attr_type, _ = root.attributes[b'particleSystemDefinitions']

        particle_system_indices = []
        for idx, element in enumerate(game_new_elements[1:], 1):
            type_name = game_pcf_output.string_dictionary[element.type_name_index]
            if type_name == b'DmeParticleSystemDefinition':
                particle_system_indices.append(idx)

        root.attributes[b'particleSystemDefinitions'] = (attr_type, particle_system_indices)

        # game file PCF object
        game_pcf_output.elements = game_new_elements

        # merge the two into one
        rebuilt_particle_files.append(merge_pcf_files(game_pcf_output, mod_pcf_output))

    return rebuilt_particle_files

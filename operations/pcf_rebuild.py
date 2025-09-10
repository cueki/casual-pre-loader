import json
from pathlib import Path
from typing import Set, List, Dict
from valve_parsers import PCFFile, PCFElement
from core.constants import AttributeType


def load_particle_system_map(map_path: str) -> Dict[str, List[str]]:
    with open(map_path, 'r') as f:
        return json.load(f)


def find_child_elements(pcf: PCFFile, element_idx: int, visited: Set[int]) -> Set[int]:
    if element_idx in visited:
        return set()

    visited.add(element_idx)
    children = set()
    element = pcf.elements[element_idx]
    children.add(element_idx)

    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type == AttributeType.ELEMENT and value != 4294967295:
            children.add(value)
            children.update(find_child_elements(pcf, value, visited))
        elif attr_type == AttributeType.ELEMENT_ARRAY:
            for child_idx in value:
                if child_idx != 4294967295:
                    children.add(child_idx)
                    children.update(find_child_elements(pcf, child_idx, visited))

    return children


def find_element_by_name(pcf: PCFFile, element_name: str):
    element = pcf.find_element_by_name(element_name)
    if element:
        return pcf.elements.index(element)
    return None


def get_element_tree(pcf: PCFFile, element_idx: int) -> Dict[int, PCFElement]:
    visited = set()
    indices = find_child_elements(pcf, element_idx, visited)
    return {idx: pcf.elements[idx] for idx in indices}


def get_pcf_element_names(pcf: PCFFile) -> List[str]:
    system_defs = pcf.get_elements_by_type('DmeParticleSystemDefinition')
    return [elem.element_name.decode('ascii') for elem in system_defs]


def build_reverse_element_map(particle_system_map) -> Dict[str, str]:
    element_to_pcf = {}
    for pcf_file, particles in particle_system_map.items():
        for particle in particles:
            element_to_pcf[particle] = pcf_file

    return element_to_pcf


def extract_elements(pcf: PCFFile, element_names) -> PCFFile:
    # create new PCF file with same version and string dictionary
    pcf_output = PCFFile(pcf.input_file, version=pcf.version)
    pcf_output.string_dictionary = pcf.string_dictionary

    # start with the root element (index 0)
    elements_to_keep = {0: pcf.elements[0]}

    # extract elements and their children
    for element_name in element_names:
        element_idx = find_element_by_name(pcf, element_name)
        if element_idx is not None:
            element_tree = get_element_tree(pcf, element_idx)
            elements_to_keep.update(element_tree)

    # create mapping of old indices to new sequential indices
    old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(elements_to_keep.keys())}

    # build new elements list
    new_elements = []
    for old_idx, element in elements_to_keep.items():
        new_element = PCFElement(
            type_name_index=element.type_name_index,
            element_name=element.element_name,
            data_signature=element.data_signature,
            attributes={}
        )

        # update element references
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type == AttributeType.ELEMENT:
                # handle single element reference
                if value != 4294967295 and value in old_to_new:
                    new_element.attributes[attr_name] = (attr_type, old_to_new[value])
                else:
                    new_element.attributes[attr_name] = (attr_type, value)
            elif attr_type == AttributeType.ELEMENT_ARRAY:
                # handle array of element references
                new_value = []
                for idx in value:
                    if idx != 4294967295 and idx in old_to_new:
                        new_value.append(old_to_new[idx])
                    else:
                        new_value.append(idx)
                new_element.attributes[attr_name] = (attr_type, new_value)
            else:
                # copy non-reference attributes as-is
                new_element.attributes[attr_name] = (attr_type, value)

        new_elements.append(new_element)

    # update root particleSystemDefinitions array
    root = new_elements[0]
    attr_type, _ = root.attributes[b'particleSystemDefinitions']

    # add all particle system elements to root's definitions
    particle_system_indices = []
    for idx, element in enumerate(new_elements[1:], 1):  # skip root element
        type_name = pcf_output.string_dictionary[element.type_name_index]
        if type_name == b'DmeParticleSystemDefinition':
            particle_system_indices.append(idx)

    root.attributes[b'particleSystemDefinitions'] = (attr_type, particle_system_indices)

    # set elements in output PCF
    pcf_output.elements = new_elements

    return pcf_output


def rebuild_particle_files(mod_pcf_path: str, particle_system_map):
    # load the mod PCF
    mod_pcf = PCFFile(mod_pcf_path).decode()

    # get all element names from the mod PCF
    mod_elements = get_pcf_element_names(mod_pcf)

    # build reverse mapping of elements to PCF files
    element_to_pcf = build_reverse_element_map(particle_system_map)

    # group mod elements by their target PCF files
    pcf_to_elements = {}
    for element in mod_elements:
        if element in element_to_pcf:
            target_pcf = element_to_pcf[element]
            if target_pcf not in pcf_to_elements:
                pcf_to_elements[target_pcf] = set()
            pcf_to_elements[target_pcf].add(element)

    # jesus fuck ive been here for 20 hours, fun challenge though :)
    list_of_shit_to_extract = []
    for filepath, particle_set in pcf_to_elements.items():
        list_of_shit_to_extract.append((Path(filepath).name, particle_set, mod_pcf))

    return list_of_shit_to_extract

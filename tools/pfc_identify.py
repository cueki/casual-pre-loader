from typing import Dict, List
from parsers.pcf_file import PCFFile


def get_parent_particle_systems(pcf: PCFFile) -> List[str]:
    systems = []
    for element in pcf.elements:
        type_name = pcf.string_dictionary[element.type_name_index].decode('ascii')
        if type_name == 'DmeParticleSystemDefinition':
            # check if it has children
            if b'children' in element.attributes:
                attr_type, children = element.attributes[b'children']
                if children:
                    system_name = element.element_name.decode('ascii')
                    systems.append(system_name)
    return systems


def find_best_match(systems: List[str], particle_map: Dict[str, List[str]]):
    best_match = ("", 0.0)

    system_set = set(systems)

    for pcf_file, known_systems in particle_map.items():
        known_set = set(known_systems)

        # calculate Jaccard similarity
        intersection = len(system_set.intersection(known_set))
        union = len(system_set.union(known_set))

        if union == 0:
            similarity = 0.0
        else:
            similarity = intersection / union

        if similarity > best_match[1]:
            best_match = (pcf_file, similarity)

    return best_match


def identify_pcf_file(pcf_path: str, particle_map: Dict[str, List[str]]):
    pcf = PCFFile(pcf_path)
    pcf.decode()
    systems = get_parent_particle_systems(pcf)
    return find_best_match(systems, particle_map)
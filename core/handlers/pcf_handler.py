from core.parsers.pcf_file import PCFFile, PCFElement


def get_parent_elements(pcf: PCFFile) -> set[str]:
    system_definitions = set()
    child_elements = set()

    for element in pcf.elements:
        type_name = pcf.string_dictionary[element.type_name_index]
        element_name = element.element_name.decode('ascii')

        if type_name == b'DmeParticleSystemDefinition':
            system_definitions.add(element_name)
        elif type_name == b'DmeParticleChild':
            child_elements.add(element_name)

    # parent elements are those that aren't also children
    parent_elements = system_definitions - child_elements
    return parent_elements


def check_parents(pcf: PCFFile, parents: set[str]) -> bool:
    for element in pcf.elements:
        if pcf.string_dictionary[element.type_name_index] == b'DmeParticleSystemDefinition':
            element_name = element.element_name.decode('ascii')
            if element_name in parents:
                return True
    return False


def update_materials(base: PCFFile, mod: PCFFile) -> PCFFile:
    # build map of element name to material
    mod_materials = {}
    for element in mod.elements:
        element_name = element.element_name.decode('ascii')
        if b'material' in element.attributes:
            mod_materials[element_name] = element.attributes[b'material']

    result = PCFFile(base.input_file)
    result.version = base.version
    result.string_dictionary = base.string_dictionary.copy()
    result.elements = []

    for element in base.elements:
        # create copy
        new_element = PCFElement(
            type_name_index=element.type_name_index,
            element_name=element.element_name,
            data_signature=element.data_signature,
            attributes=element.attributes.copy()
        )

        # update material
        element_name = element.element_name.decode('ascii')
        if element_name in mod_materials:
            new_element.attributes[b'material'] = mod_materials[element_name]

        result.elements.append(new_element)

    return result


from valve_parsers import PCFFile, PCFElement
from core.constants import AttributeType


def copy_element(element: PCFElement, offset: int, source_pcf: PCFFile,
                 target_pcf: PCFFile) -> PCFElement:
    # get the type name string from the source PCF
    type_name = source_pcf.string_dictionary[element.type_name_index]

    # handle DmeElement root and find/add type name in target PCF's string dictionary
    try:
        if type_name == b'DmeElement':
            new_type_name_index = 0
        else:
            try:
                new_type_name_index = target_pcf.string_dictionary.index(type_name)
            except ValueError:
                # add new type name to dictionary if it doesn't exist
                new_type_name_index = len(target_pcf.string_dictionary)
                target_pcf.string_dictionary.append(type_name)
    except Exception as e:
        raise ValueError(f"Error processing type name '{type_name.decode('ascii')}': {str(e)}")

    new_element = PCFElement(
        type_name_index=new_type_name_index,
        element_name=element.element_name,
        data_signature=element.data_signature,
        attributes={}
    )

    # copy and update attributes
    for attr_name, (attr_type, value) in element.attributes.items():
        # first ensure the attribute name exists in target PCF's string dictionary
        try:
            target_pcf.string_dictionary.index(attr_name)
        except ValueError:
            # add new attribute name if it doesn't exist
            target_pcf.string_dictionary.append(attr_name)

        # now handle the attribute value based on type
        if attr_type == AttributeType.ELEMENT:
            # update single element reference
            new_value = value + offset if value != 4294967295 else value
            new_element.attributes[attr_name] = (attr_type, new_value)

        elif attr_type == AttributeType.ELEMENT_ARRAY:
            # update array of element references
            new_value = [idx + offset if idx != 4294967295 else idx for idx in value]
            new_element.attributes[attr_name] = (attr_type, new_value)

        else:
            # copy other attributes as-is
            new_element.attributes[attr_name] = (attr_type, value)

    return new_element


def merge_pcf_files(pcf1: PCFFile, pcf2: PCFFile) -> PCFFile:
    # get starting offset for element indices
    element_offset = len(pcf1.elements)

    # root is always index 0
    root_idx = 0
    root_element = pcf1.elements[root_idx]

    # copy and update non-root elements from pcf2
    new_elements = []
    new_system_indices = []

    for i, element in enumerate(pcf2.elements):
        # skip the root element from pcf2
        if i == root_idx:
            continue

        new_element = copy_element(element, element_offset - 1, pcf2, pcf1)
        new_elements.append(new_element)

        # track new particle system definitions
        type_name = pcf2.string_dictionary[element.type_name_index]
        if type_name == b'DmeParticleSystemDefinition':
            new_system_indices.append(len(pcf1.elements) + len(new_elements) - 1)

    # update the root element's particleSystemDefinitions array with new system indices
    attr_type, existing_systems = root_element.attributes[b'particleSystemDefinitions']
    root_element.attributes[b'particleSystemDefinitions'] = (attr_type, existing_systems + new_system_indices)

    # add all new elements to pcf1
    pcf1.elements.extend(new_elements)

    return pcf1
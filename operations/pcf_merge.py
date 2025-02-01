from parsers.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType


def copy_element(element: PCFElement, offset: int, source_pcf: PCFFile,
                 target_pcf: PCFFile) -> PCFElement:
    # get the type name string from the source PCF
    type_name = source_pcf.string_dictionary[element.type_name_index]

    # find or add type name in target PCF's string dictionary
    try:
        new_type_name_index = target_pcf.string_dictionary.index(type_name)
    except ValueError:
        new_type_name_index = len(target_pcf.string_dictionary)
        target_pcf.string_dictionary.append(type_name)

    new_element = PCFElement(
        type_name_index=new_type_name_index,
        element_name=element.element_name,
        data_signature=element.data_signature,
        attributes={}
    )

    # copy and update attributes
    for attr_name, (attr_type, value) in element.attributes.items():
        # ensure attribute name exists in target PCF's string dictionary
        try:
            target_pcf.string_dictionary.index(attr_name)
        except ValueError:
            target_pcf.string_dictionary.append(attr_name)

        # handle the attribute value based on type
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


def merge_pcf_files(pcfs: [PCFFile, ...]) -> PCFFile:
    if not pcfs:
        raise ValueError("At least one PCF file must be provided")

    # If only one PCF, return it
    if len(pcfs) == 1:
        return pcfs[0]

    # Use the first PCF as the base
    base_pcf = pcfs[0]

    # Initialize result PCF with properties from the first file
    result_pcf = PCFFile(base_pcf.input_file, version=base_pcf.version)
    result_pcf.string_dictionary = base_pcf.string_dictionary.copy()

    # Start with the root element from the first PCF
    result_pcf.elements = [base_pcf.elements[0]]
    root_element = result_pcf.elements[0]

    # Track current offset and particle system indices
    current_offset = len(result_pcf.elements)
    all_system_indices = []

    # Get initial particle systems from the first PCF
    attr_type, base_systems = root_element.attributes[b'particleSystemDefinitions']
    all_system_indices.extend(base_systems)

    # Copy non-root elements from the first PCF
    for i, element in enumerate(base_pcf.elements[1:], 1):
        result_pcf.elements.append(copy_element(element, 0, base_pcf, result_pcf))

    # Process each additional PCF file
    for pcf in pcfs[1:]:
        file_system_indices = []

        # Copy and update non-root elements
        for i, element in enumerate(pcf.elements[1:], 1):  # Skip root element
            new_element = copy_element(element, current_offset - 1, pcf, result_pcf)
            result_pcf.elements.append(new_element)

            # Track particle system definitions
            type_name = pcf.string_dictionary[element.type_name_index]
            if type_name == b'DmeParticleSystemDefinition':
                file_system_indices.append(len(result_pcf.elements) - 1)

        # Update offset for next file
        current_offset = len(result_pcf.elements)
        all_system_indices.extend(file_system_indices)

    # Update the root element's particleSystemDefinitions with all systems
    root_element.attributes[b'particleSystemDefinitions'] = (attr_type, all_system_indices)

    return result_pcf

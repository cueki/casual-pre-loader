from parsers.pcf_file import PCFFile
from operations.pcf_compress import remove_duplicate_elements


def pcf_empty_root_processor():
    def process_pcf(pcf: PCFFile) -> PCFFile:
        root_element = pcf.elements[0]
        attr_type, _ = root_element.attributes[b'particleSystemDefinitions']
        root_element.attributes[b'particleSystemDefinitions'] = (attr_type, [])
        return pcf

    return process_pcf


def pcf_mod_processor(mod_path: str):
    def process_pcf(game_pcf) -> PCFFile:
        mod_pcf = PCFFile(mod_path)
        mod_pcf.decode()
        result = remove_duplicate_elements(mod_pcf)
        return result

    return process_pcf

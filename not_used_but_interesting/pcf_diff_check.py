from models.pcf_file import PCFFile
from core.traversal import PCFTraversal
from typing import Dict, Any, Set, Tuple


def get_element_attributes(pcf: PCFFile) -> Dict[str, Dict[str, Any]]:
    elements = {}

    for element in pcf.elements:
        element_name = element.element_name.decode('ascii', errors='replace')
        elements[element_name] = {}

        for attr_name, (attr_type, value) in element.attributes.items():
            try:
                if isinstance(value, bytes):
                    value = value.decode('ascii', errors='replace')
                elif isinstance(value, (tuple, list)):
                    value = [v.decode('ascii', errors='replace') if isinstance(v, bytes) else v for v in value]
            except:
                pass

            if isinstance(attr_name, bytes):
                attr_name = attr_name.decode('ascii', errors='replace')

            elements[element_name][attr_name] = {
                'value': value,
                'type': attr_type.name
            }

    return elements


def compare_attributes(elem1: Dict[str, Any],
                       elem2: Dict[str, Any],
                       pcf1_name: str,
                       pcf2_name: str) -> Tuple[Set[str], Set[str], Dict[str, Tuple]]:
    attrs1 = set(elem1.keys())
    attrs2 = set(elem2.keys())

    only_in_1 = attrs1 - attrs2
    only_in_2 = attrs2 - attrs1
    differing_values = {}

    common_attrs = attrs1 & attrs2
    for attr in common_attrs:
        if elem1[attr]['value'] != elem2[attr]['value']:
            differing_values[attr] = (elem1[attr]['value'], elem2[attr]['value'])

    return only_in_1, only_in_2, differing_values


def compare_pcfs(pcf1_path: str, pcf2_path: str) -> None:
    print(f"\nComparing PCF files:")
    print(f"File 1: {pcf1_path}")
    print(f"File 2: {pcf2_path}")

    pcf1 = PCFFile(pcf1_path)
    pcf1.decode()
    pcf2 = PCFFile(pcf2_path)
    pcf2.decode()

    elements1 = get_element_attributes(pcf1)
    elements2 = get_element_attributes(pcf2)

    all_elements = set(elements1.keys()) | set(elements2.keys())

    for element in sorted(all_elements):
        if element not in elements1:
            print(f"\nElement missing from {pcf1_path}: {element}")
            continue

        if element not in elements2:
            print(f"\nElement missing from {pcf2_path}: {element}")
            continue

        only_in_1, only_in_2, differing_values = compare_attributes(
            elements1[element], elements2[element], pcf1_path, pcf2_path
        )

        if only_in_1 or only_in_2 or differing_values:
            print(f"\nDifferences in element: {element}")

            if only_in_1:
                print(f"  Attributes only in {pcf1_path}:")
                for attr in sorted(only_in_1):
                    print(f"    - {attr}: {elements1[element][attr]['value']}")

            if only_in_2:
                print(f"  Attributes only in {pcf2_path}:")
                for attr in sorted(only_in_2):
                    print(f"    - {attr}: {elements2[element][attr]['value']}")

            if differing_values:
                print("  Different values:")
                for attr, (val1, val2) in sorted(differing_values.items()):
                    print(f"    - {attr}:")
                    print(f"      {pcf1_path}: {val1}")
                    print(f"      {pcf2_path}: {val2}")


def main():
    compare_pcfs("dxhr_fx_mod.pcf", "dxhr_fx.pcf")


if __name__ == "__main__":
    main()
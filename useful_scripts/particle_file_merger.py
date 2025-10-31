#!/usr/bin/env python3
"""
Script for merging particle files manually.
This needs to be moved into root, or you need to update imports for it to work.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from valve_parsers import PCFFile
from operations.pcf_rebuild import get_pcf_element_names, extract_elements
from core.folder_setup import folder_setup


def load_particle_system_map() -> Dict[str, List[str]]:
    map_path = folder_setup.install_dir / "particle_system_map.json"
    with open(map_path, 'r') as f:
        return json.load(f)


def find_conflicting_elements(pcf_files: List[PCFFile], target_elements: List[str]) -> Dict[str, List[int]]:
    element_sources = defaultdict(list)

    for i, pcf in enumerate(pcf_files):
        available_elements = set(get_pcf_element_names(pcf))
        for element in target_elements:
            if element in available_elements:
                element_sources[element].append(i)

    return {elem: sources for elem, sources in element_sources.items() if len(sources) > 1}


def resolve_conflicts(conflicts: Dict[str, List[int]], pcf_files: List[Path]) -> Dict[str, int]:
    decisions = {}

    if not conflicts:
        return decisions

    print(f"\nFound {len(conflicts)} conflicting particle elements:")

    for element_name, source_indices in conflicts.items():
        print(f"\n'{element_name}' found in:")
        for i, source_idx in enumerate(source_indices):
            print(f"  [{i+1}] {pcf_files[source_idx].name}")

        while True:
            try:
                choice = input(f"Choose source for '{element_name}' [1-{len(source_indices)}]: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(source_indices):
                        decisions[element_name] = source_indices[idx]
                        break
                print(f"Invalid choice. Please enter 1-{len(source_indices)}")
            except (ValueError, KeyboardInterrupt):
                print("\n Operation cancelled by user")
                sys.exit(1)

    return decisions


def remap_element_attributes(element, old_to_new: Dict[int, int], string_dict, AttributeType, PCFElement):
    type_name = string_dict['extracted'][element.type_name_index]
    new_type_idx = string_dict['merged'].index(type_name)

    new_element = PCFElement(
        type_name_index=new_type_idx,
        element_name=element.element_name,
        data_signature=element.data_signature,
        attributes={}
    )

    for attr_name, (attr_type, value) in element.attributes.items():
        if attr_type == AttributeType.ELEMENT:
            if value != 4294967295 and value in old_to_new:
                new_element.attributes[attr_name] = (attr_type, old_to_new[value])
            else:
                new_element.attributes[attr_name] = (attr_type, value)
        elif attr_type == AttributeType.ELEMENT_ARRAY:
            new_value = [old_to_new[idx] if idx != 4294967295 and idx in old_to_new else idx for idx in value]
            new_element.attributes[attr_name] = (attr_type, new_value)
        else:
            new_element.attributes[attr_name] = (attr_type, value)

    return new_element


def create_merged_pcf(pcf_files: List[PCFFile], pcf_paths: List[Path],
                     target_elements: List[str], conflict_decisions: Dict[str, int]) -> PCFFile:
    from core.constants import AttributeType
    from valve_parsers import PCFElement

    base_pcf = pcf_files[0]
    merged_pcf = PCFFile(pcf_paths[0], version=base_pcf.version)
    merged_pcf.string_dictionary = base_pcf.string_dictionary.copy()
    merged_pcf.elements = base_pcf.elements.copy()

    for element_name in target_elements:
        if element_name not in conflict_decisions or conflict_decisions[element_name] == 0:
            continue

        source_idx = conflict_decisions[element_name]
        source_pcf = pcf_files[source_idx]
        print(f" Replacing '{element_name}' with version from {pcf_paths[source_idx].name}")

        extracted = extract_elements(source_pcf, [element_name])

        for string in extracted.string_dictionary:
            if string not in merged_pcf.string_dictionary:
                merged_pcf.string_dictionary.append(string)

        old_to_new = {old_idx: len(merged_pcf.elements) + old_idx - 1
                      for old_idx in range(1, len(extracted.elements))}

        string_dict = {'extracted': extracted.string_dictionary, 'merged': merged_pcf.string_dictionary}
        for old_idx, element in enumerate(extracted.elements[1:], 1):
            new_element = remap_element_attributes(element, old_to_new, string_dict, AttributeType, PCFElement)
            merged_pcf.elements.append(new_element)

    root = merged_pcf.elements[0]
    system_indices = [i for i, elem in enumerate(merged_pcf.elements[1:], 1)
                      if merged_pcf.string_dictionary[elem.type_name_index] == b'DmeParticleSystemDefinition']

    if b'particleSystemDefinitions' in root.attributes:
        attr_type, _ = root.attributes[b'particleSystemDefinitions']
        root.attributes[b'particleSystemDefinitions'] = (attr_type, system_indices)

    return merged_pcf


def main():
    parser = argparse.ArgumentParser(
        description="Merge particle systems from multiple PCF files for a specific target particle file",
        epilog="Example: python particle_file_merger.py --target 'particles/taunt_fx.pcf' file1.pcf file2.pcf -o merged_taunt_fx.pcf"
    )

    parser.add_argument(
        '--target',
        required=True,
        help='Target particle file from particle_system_map.json (e.g., "particles/taunt_fx.pcf")'
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input PCF files to merge from'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output PCF file'
    )

    args = parser.parse_args()

    try:
        particle_map = load_particle_system_map()
    except FileNotFoundError:
        print("Error: particle_system_map.json not found")
        sys.exit(1)

    target = args.target
    if target not in particle_map:
        print(f"Error: Target '{target}' not found in particle_system_map.json")
        print("Available targets:")
        for available_target in sorted(particle_map.keys()):
            display_name = available_target.replace('particles/', '')
            print(f"  - {display_name}")
        sys.exit(1)

    target_elements = particle_map[args.target]
    print(f"Target: {args.target}")
    print(f"Need {len(target_elements)} elements: {', '.join(target_elements)}")

    pcf_paths = []
    pcf_files = []

    for file_path in args.input_files:
        path = Path(file_path)
        if not path.exists():
            print(f" Error: File '{file_path}' does not exist")
            sys.exit(1)

        try:
            pcf = PCFFile(path).decode()
            pcf_paths.append(path)
            pcf_files.append(pcf)
            elements = get_pcf_element_names(pcf)
            print(f" Loaded {path.name} ({len(elements)} particle systems)")
        except Exception as e:
            print(f" Error loading '{file_path}': {e}")
            sys.exit(1)

    # resolve conflicts
    print(f"\n Checking for conflicts among target elements...")
    conflicts = find_conflicting_elements(pcf_files, target_elements)
    if conflicts:
        conflict_decisions = resolve_conflicts(conflicts, pcf_paths)
    else:
        print(" No conflicts found!")
        conflict_decisions = {}

    print(f"\n Creating merged PCF file...")
    try:
        merged_pcf = create_merged_pcf(pcf_files, pcf_paths, target_elements, conflict_decisions)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged_pcf.encode(output_path)

        print(f"\nSuccessfully created '{output_path}'")
        print(f"Contains {len(merged_pcf.elements)-1} particle systems")

        final_elements = get_pcf_element_names(merged_pcf)
        missing_elements = set(target_elements) - set(final_elements)

        if missing_elements:
            print(f"Missing elements (not found in input files): {', '.join(missing_elements)}")
        else:
            print(f"All target elements included!")

    except Exception as e:
        print(f" Error creating merged PCF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

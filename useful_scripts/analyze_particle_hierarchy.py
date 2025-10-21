#!/usr/bin/env python3
"""
Script to analyze particle system hierarchy by examining parent-child relationships.
This will show which systems reference other systems as children.
Has the ability to generate the particle_system_map.json as output.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from valve_parsers import PCFFile, AttributeType


def analyze_particle_hierarchy(pcf_file: PCFFile, verbose: bool = False) -> Dict[str, Dict]:
    if not pcf_file.elements:
        return {}

    particle_systems = {}
    system_name_to_index = {}
    
    # first pass: collect all particle systems
    for i, element in enumerate(pcf_file.elements):
        element_type = pcf_file.string_dictionary[element.type_name_index].decode('ascii', errors='replace')
        if element_type == 'DmeParticleSystemDefinition':
            system_name = element.element_name.decode('ascii', errors='replace')
            particle_systems[system_name] = {
                'index': i,
                'element': element,
                'children': [],
                'referenced_by': [],
                'operators': [],
                'renderers': [],
                'initializers': [],
                'emitters': []
            }
            system_name_to_index[system_name] = i
    
    if verbose:
        print(f"Found {len(particle_systems)} particle systems")
    
    # second pass: analyze relationships
    for system_name, system_info in particle_systems.items():
        element = system_info['element']
        
        if verbose:
            print(f"\nAnalyzing: {system_name}")
        
        # look through attributes for references
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            attr_name_str = attr_name.decode('ascii', errors='replace')

            if attr_type == AttributeType.STRING and attr_value:
                value_str = attr_value.decode('ascii', errors='replace') if isinstance(attr_value, bytes) else str(attr_value)

                if value_str in system_name_to_index:
                    attr_lower = attr_name_str.lower()
                    if 'child' in attr_lower or 'definition' in attr_lower:
                        system_info['children'].append(value_str)
                        particle_systems[value_str]['referenced_by'].append(system_name)
                        if verbose:
                            print(f"  -> Child: {value_str} (via {attr_name_str})")

            elif attr_type == AttributeType.ELEMENT and attr_value is not None:
                # handle single ELEMENT references (e.g., DmeParticleChild's 'child' attribute)
                if isinstance(attr_value, int) and 0 <= attr_value < len(pcf_file.elements):
                    ref_element = pcf_file.elements[attr_value]
                    ref_name = ref_element.element_name.decode('ascii', errors='replace')
                    if ref_name in particle_systems:
                        attr_lower = attr_name_str.lower()
                        if 'child' in attr_lower or 'definition' in attr_lower:
                            system_info['children'].append(ref_name)
                            particle_systems[ref_name]['referenced_by'].append(system_name)
                            if verbose:
                                print(f"  -> Child: {ref_name} (via {attr_name_str})")

            elif attr_type in [AttributeType.STRING_ARRAY, AttributeType.ELEMENT_ARRAY] and attr_value:
                references = []

                if attr_type == AttributeType.ELEMENT_ARRAY:
                    for element_index in attr_value:
                        if 0 <= element_index < len(pcf_file.elements):
                            ref_element = pcf_file.elements[element_index]
                            ref_type = pcf_file.string_dictionary[ref_element.type_name_index].decode('ascii', errors='replace')
                            ref_name = ref_element.element_name.decode('ascii', errors='replace')

                            # if it's a DmeParticleChild, follow its 'child' attribute to get the actual system
                            if ref_type == 'DmeParticleChild':
                                for child_attr_name, (child_attr_type, child_attr_value) in ref_element.attributes.items():
                                    child_attr_name_str = child_attr_name.decode('ascii', errors='replace')
                                    if child_attr_name_str == 'child' and child_attr_type == AttributeType.ELEMENT:
                                        if isinstance(child_attr_value, int) and 0 <= child_attr_value < len(pcf_file.elements):
                                            actual_system = pcf_file.elements[child_attr_value]
                                            ref_name = actual_system.element_name.decode('ascii', errors='replace')
                                        break

                            if ref_name in particle_systems:
                                references.append(ref_name)
                else:
                    for item in attr_value:
                        if isinstance(item, bytes):
                            item_str = item.decode('ascii', errors='replace')
                            if item_str in particle_systems:
                                references.append(item_str)

                attr_lower = attr_name_str.lower()
                for ref_name in references:
                    if 'child' in attr_lower:
                        system_info['children'].append(ref_name)
                        particle_systems[ref_name]['referenced_by'].append(system_name)
                        if verbose:
                            print(f"  -> Child: {ref_name} (via {attr_name_str})")
                    elif 'operator' in attr_lower:
                        system_info['operators'].append(ref_name)
                        if verbose:
                            print(f"  -> Operator: {ref_name} (via {attr_name_str})")
                    elif 'render' in attr_lower:
                        system_info['renderers'].append(ref_name)
                        if verbose:
                            print(f"  -> Renderer: {ref_name} (via {attr_name_str})")
                    elif 'initial' in attr_lower:
                        system_info['initializers'].append(ref_name)
                        if verbose:
                            print(f"  -> Initializer: {ref_name} (via {attr_name_str})")
                    elif 'emit' in attr_lower:
                        system_info['emitters'].append(ref_name)
                        if verbose:
                            print(f"  -> Emitter: {ref_name} (via {attr_name_str})")
    
    return particle_systems


def find_root_systems(particle_systems: Dict[str, Dict]) -> List[str]:
    # find systems with no reference in children
    root_systems = []
    for system_name, system_info in particle_systems.items():
        if not system_info['referenced_by']:
            root_systems.append(system_name)
    return sorted(root_systems)


def build_hierarchy_tree(particle_systems: Dict[str, Dict], root_system: str, visited: Set[str] = None) -> Dict:
    # le recursion XD
    if visited is None:
        visited = set()
    
    if root_system in visited:
        return {"name": root_system, "children": [], "circular": True}
    
    visited.add(root_system)
    
    system_info = particle_systems.get(root_system, {})
    children = []
    
    for child_name in system_info.get('children', []):
        child_tree = build_hierarchy_tree(particle_systems, child_name, visited.copy())
        children.append(child_tree)
    
    return {
        "name": root_system,
        "children": children,
        "operators": system_info.get('operators', []),
        "renderers": system_info.get('renderers', []),
        "initializers": system_info.get('initializers', []),
        "emitters": system_info.get('emitters', [])
    }


def print_hierarchy_tree(tree: Dict, indent: int = 0, show_components: bool = False):
    prefix = "  " * indent
    circular_marker = " (CIRCULAR)" if tree.get('circular') else ""
    print(f"{prefix}{tree['name']}{circular_marker}")
    
    if show_components:
        for comp_type in ['operators', 'renderers', 'initializers', 'emitters']:
            components = tree.get(comp_type, [])
            if components:
                print(f"{prefix}  {comp_type.title()}: {', '.join(components)}")
    
    for child in tree.get('children', []):
        print_hierarchy_tree(child, indent + 1, show_components)


def compare_with_element0(pcf_file: PCFFile, particle_systems: Dict[str, Dict]) -> \
        tuple[list[str], list[str], dict[str, list[str]]]:
    # element 0 from Mass Effect
    element0_systems = []
    if pcf_file.elements:
        element_0 = pcf_file.elements[0]
        for attr_name, (attr_type, attr_value) in element_0.attributes.items():
            attr_name_str = attr_name.decode('ascii', errors='replace')
            if attr_name_str == 'particleSystemDefinitions' and attr_type == AttributeType.ELEMENT_ARRAY:
                for element_index in attr_value:
                    if 0 <= element_index < len(pcf_file.elements):
                        ref_element = pcf_file.elements[element_index]
                        system_name = ref_element.element_name.decode('ascii', errors='replace')
                        element0_systems.append(system_name)
                break

    root_systems = find_root_systems(particle_systems)
    set_element0 = set(element0_systems)
    set_roots = set(root_systems)
    
    only_in_element0 = sorted(set_element0 - set_roots)
    only_in_roots = sorted(set_roots - set_element0)
    
    return sorted(element0_systems), root_systems, {
        'only_in_element0': only_in_element0,
        'only_in_roots': only_in_roots,
        'common': sorted(set_element0 & set_roots)
    }


def generate_particle_system_map_with_parents(pcf_directory: Path, output_file: str = "particle_system_map.json"):
    # generate a particle system map showing only the parent (root) systems for each PCF file.
    particle_map = {}
    
    pcf_files = list(pcf_directory.glob("*.pcf"))
    if not pcf_files:
        print(f"No PCF files found in {pcf_directory}")
        return
    
    print(f"Analyzing {len(pcf_files)} PCF files...")
    
    for pcf_path in sorted(pcf_files):
        relative_path = f"particles/{pcf_path.name}"
        
        try:
            pcf = PCFFile(pcf_path).decode()
            particle_systems = analyze_particle_hierarchy(pcf, verbose=False)
            
            if not particle_systems:
                continue

            root_systems = find_root_systems(particle_systems)
            particle_map[relative_path] = sorted(root_systems)
            
        except Exception as e:
            print(f"Error processing {pcf_path}: {e}")
            continue

    with open(output_file, 'w') as f:
        json.dump(particle_map, f, indent=2, sort_keys=True)
    
    print(f"Generated particle system map with parent elements: {output_file}")

    total_files = len(particle_map)
    total_parent_systems = sum(len(systems) for systems in particle_map.values())
    
    print(f"Summary:")
    print(f"  PCF files processed: {total_files}")
    print(f"  Total parent systems: {total_parent_systems}")
    print(f"  Average parent systems per file: {total_parent_systems/total_files:.1f}" if total_files > 0 else "")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze particle system hierarchy and parent-child relationships'
    )
    parser.add_argument('pcf_file', nargs='?', help='Path to a specific PCF file to analyze')
    parser.add_argument('-d', '--directory', default='particles',
                       help='Directory containing PCF files (default: particles)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed analysis')
    parser.add_argument('--tree', action='store_true',
                       help='Show hierarchical tree view')
    parser.add_argument('--components', action='store_true',
                       help='Show operators, renderers, etc. in tree view')
    parser.add_argument('--compare', action='store_true',
                       help='Compare hierarchy analysis with Element 0')
    parser.add_argument('--all', action='store_true',
                       help='Analyze all PCF files in the directory')
    parser.add_argument('--generate-map', action='store_true',
                       help='Generate particle_system_map.json with parent elements')
    parser.add_argument('--output', default='particle_system_map.json',
                       help='Output file for generated particle map (default: particle_system_map.json)')
    
    args = parser.parse_args()

    if args.generate_map:
        pcf_directory = Path(args.directory)
        if not pcf_directory.exists():
            print(f"Error: Directory '{args.directory}' does not exist.")
            sys.exit(1)
        generate_particle_system_map_with_parents(pcf_directory, args.output)
        return
    
    def analyze_single_file(pcf_path: Path):
        print(f"Analyzing: {pcf_path}")
        print("=" * 60)
        
        try:
            pcf = PCFFile(pcf_path).decode()
            particle_systems = analyze_particle_hierarchy(pcf, args.verbose)
            
            if not particle_systems:
                print("No particle systems found.")
                return
            
            print(f"\nSummary:")
            print(f"  Total particle systems: {len(particle_systems)}")

            root_systems = find_root_systems(particle_systems)
            print(f"  Root systems (not referenced by others): {len(root_systems)}")
            
            if args.compare:
                element0_systems, roots, differences = compare_with_element0(pcf, particle_systems)
                print(f"  Element 0 systems: {len(element0_systems)}")
                print(f"  Common systems: {len(differences['common'])}")
                
                if differences['only_in_element0']:
                    print(f"  Only in Element 0: {differences['only_in_element0']}")
                if differences['only_in_roots']:
                    print(f"  Only in root analysis: {differences['only_in_roots']}")
            
            if args.tree:
                print(f"\nHierarchy Trees:")
                print("-" * 40)
                for root_name in root_systems:
                    tree = build_hierarchy_tree(particle_systems, root_name)
                    print_hierarchy_tree(tree, show_components=args.components)
                    print()

            systems_with_children = [(name, info) for name, info in particle_systems.items() if info['children']]
            if systems_with_children:
                print(f"\nSystems with children ({len(systems_with_children)}):")
                for system_name, system_info in sorted(systems_with_children):
                    children = ', '.join(system_info['children'])
                    print(f"  {system_name} -> {children}")
            else:
                print(f"\nNo parent-child relationships found between particle systems.")
        
        except Exception as e:
            print(f"Error processing {pcf_path}: {e}")
    
    if args.pcf_file:
        pcf_path = Path(args.pcf_file)
        if not pcf_path.exists():
            print(f"Error: PCF file '{args.pcf_file}' does not exist.")
            sys.exit(1)
        analyze_single_file(pcf_path)
    
    elif args.all:
        pcf_directory = Path(args.directory)
        if not pcf_directory.exists():
            print(f"Error: Directory '{args.directory}' does not exist.")
            sys.exit(1)
        
        pcf_files = list(pcf_directory.glob("*.pcf"))
        if not pcf_files:
            print(f"No PCF files found in {pcf_directory}")
            sys.exit(1)
        
        for pcf_path in sorted(pcf_files):
            analyze_single_file(pcf_path)
            print("\n" + "="*80 + "\n")
    
    else:
        # default: analyze first file
        pcf_directory = Path(args.directory)
        if not pcf_directory.exists():
            print(f"Error: Directory '{args.directory}' does not exist.")
            sys.exit(1)
        
        pcf_files = list(pcf_directory.glob("*.pcf"))
        if not pcf_files:
            print(f"No PCF files found in {pcf_directory}")
            sys.exit(1)
        
        pcf_path = sorted(pcf_files)[0]
        analyze_single_file(pcf_path)


if __name__ == "__main__":
    main()

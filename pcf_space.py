from pcfcodec import PCFCodec, AttributeType
from typing import Dict, List, Tuple, Set
import os
import struct
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SpaceReclamationInfo:
    """Information about potential space that could be reclaimed."""
    bytes_saved: int
    risk_level: str  # 'safe', 'moderate', 'risky'
    description: str
    location: str

def analyze_unused_strings(pcf: PCFCodec) -> List[SpaceReclamationInfo]:
    """Find strings in the dictionary that aren't referenced by any element."""
    reclamation_opportunities = []
    
    # Build set of all used string indices
    used_strings: Set[int] = set()
    
    # Check element type names
    for element in pcf.pcf.elements:
        used_strings.add(element.type_name_index)
        
        # Check attribute names and string values
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Convert attribute name to string for dictionary lookup
            if isinstance(attr_name, bytes):
                attr_name_str = attr_name.decode('ascii', errors='replace')
            else:
                attr_name_str = attr_name
                
            # Find index of attribute name in string dictionary
            try:
                attr_name_idx = pcf.pcf.string_dictionary.index(
                    attr_name_str.encode('ascii') if isinstance(attr_name_str, str) else attr_name_str
                )
                used_strings.add(attr_name_idx)
            except ValueError:
                pass
                
            # Check string values
            if attr_type == AttributeType.STRING:
                if isinstance(attr_value, bytes):
                    try:
                        str_idx = pcf.pcf.string_dictionary.index(attr_value)
                        used_strings.add(str_idx)
                    except ValueError:
                        pass
    
    # Find unused strings
    for idx, string in enumerate(pcf.pcf.string_dictionary):
        if idx not in used_strings:
            if isinstance(string, bytes):
                string_len = len(string) + 1  # Include null terminator
            else:
                string_len = len(string.encode('ascii')) + 1
                
            reclamation_opportunities.append(SpaceReclamationInfo(
                bytes_saved=string_len,
                risk_level='safe',
                description=f'Unused string: "{string.decode("ascii", errors="replace") if isinstance(string, bytes) else string}"',
                location=f'String dictionary index {idx}'
            ))
    
    return reclamation_opportunities

def analyze_redundant_attributes(pcf: PCFCodec) -> List[SpaceReclamationInfo]:
    """Find attributes that might be redundant or unnecessary."""
    reclamation_opportunities = []
    
    # Track common default values
    default_values = {
        'visible': (AttributeType.BOOLEAN, True),
        'enabled': (AttributeType.BOOLEAN, True),
        'alpha': (AttributeType.FLOAT, 1.0),
        'scale': (AttributeType.FLOAT, 1.0),
    }
    
    # Track attribute usage patterns
    attribute_values = defaultdict(lambda: defaultdict(int))
    
    # Analyze each element's attributes
    for elem_idx, element in enumerate(pcf.pcf.elements):
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Convert attribute name to string for comparison
            if isinstance(attr_name, bytes):
                attr_name_str = attr_name.decode('ascii', errors='replace')
            else:
                attr_name_str = attr_name
                
            # Track value frequency for this attribute
            value_key = f"{attr_value}"
            attribute_values[attr_name_str][value_key] += 1
            
            # Check for default values that could be omitted
            if attr_name_str in default_values:
                default_type, default_value = default_values[attr_name_str]
                if attr_type == default_type and attr_value == default_value:
                    # Calculate bytes saved
                    bytes_saved = 3  # 2 bytes for name index, 1 for type
                    if attr_type == AttributeType.FLOAT:
                        bytes_saved += 4
                    elif attr_type == AttributeType.BOOLEAN:
                        bytes_saved += 1
                        
                    reclamation_opportunities.append(SpaceReclamationInfo(
                        bytes_saved=bytes_saved,
                        risk_level='moderate',
                        description=f'Default value attribute: {attr_name_str} = {attr_value}',
                        location=f'Element {elem_idx}'
                    ))
    
    # Look for attributes with very low variance (might be unnecessary)
    for attr_name, values in attribute_values.items():
        if len(values) == 1 and sum(values.values()) > 1:
            # This attribute has the same value everywhere it appears
            value = list(values.keys())[0]
            occurrences = list(values.values())[0]
            
            reclamation_opportunities.append(SpaceReclamationInfo(
                bytes_saved=0,  # Needs manual calculation based on type
                risk_level='moderate',
                description=f'Uniform attribute: {attr_name} = {value} ({occurrences} occurrences)',
                location='Multiple elements'
            ))
    
    return reclamation_opportunities

def analyze_empty_elements(pcf: PCFCodec) -> List[SpaceReclamationInfo]:
    """Find elements that might be unnecessary or empty."""
    reclamation_opportunities = []
    
    for elem_idx, element in enumerate(pcf.pcf.elements):
        # Check for elements with no attributes
        if len(element.attributes) == 0:
            reclamation_opportunities.append(SpaceReclamationInfo(
                bytes_saved=16,  # Basic element overhead
                risk_level='moderate',
                description='Empty element with no attributes',
                location=f'Element {elem_idx}'
            ))
            continue
            
        # Check for elements that only have default/empty values
        all_default = True
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            if attr_type == AttributeType.STRING and (not attr_value or attr_value == b''):
                continue
            elif attr_type == AttributeType.FLOAT and attr_value == 0.0:
                continue
            elif attr_type == AttributeType.BOOLEAN and not attr_value:
                continue
            all_default = False
            break
            
        if all_default:
            # Calculate approximate bytes saved
            bytes_saved = 16  # Basic element overhead
            bytes_saved += sum(3 + (4 if t == AttributeType.FLOAT else 1) 
                             for t, _ in element.attributes.values())
            
            reclamation_opportunities.append(SpaceReclamationInfo(
                bytes_saved=bytes_saved,
                risk_level='risky',
                description='Element with only default/empty values',
                location=f'Element {elem_idx}'
            ))
    
    return reclamation_opportunities

def analyze_pcf_space_reclamation(pcf_path: str) -> None:
    """Analyze PCF file for potential space reclamation opportunities."""
    try:
        # Load PCF file
        codec = PCFCodec()
        codec.decode(pcf_path)
        
        file_size = os.path.getsize(pcf_path)
        print(f"\nAnalyzing PCF file: {pcf_path}")
        print(f"Current file size: {file_size:,} bytes")
        print("=" * 60)
        
        # Collect all reclamation opportunities
        opportunities = []
        opportunities.extend(analyze_unused_strings(codec))
        opportunities.extend(analyze_redundant_attributes(codec))
        opportunities.extend(analyze_empty_elements(codec))
        
        # Sort by bytes saved
        opportunities.sort(key=lambda x: x.bytes_saved, reverse=True)
        
        # Group by risk level
        risk_groups = {
            'safe': [],
            'moderate': [],
            'risky': []
        }
        
        total_possible_savings = 0
        for opp in opportunities:
            risk_groups[opp.risk_level].append(opp)
            total_possible_savings += opp.bytes_saved
        
        # Print summary
        print("\nSpace Reclamation Opportunities:")
        print("-" * 40)
        
        for risk_level in ['safe', 'moderate', 'risky']:
            group = risk_groups[risk_level]
            if not group:
                continue
                
            print(f"\n{risk_level.upper()} Modifications:")
            print("-" * 20)
            group_savings = sum(opp.bytes_saved for opp in group)
            print(f"Total potential savings: {group_savings:,} bytes")
            
            for opp in group:
                if opp.bytes_saved > 0:
                    print(f"\n• Save {opp.bytes_saved:,} bytes:")
                else:
                    print("\n• Potential savings (needs manual calculation):")
                print(f"  {opp.description}")
                print(f"  Location: {opp.location}")
        
        # Print overall summary
        print("\nOverall Summary:")
        print("-" * 40)
        print(f"Total potential space savings: {total_possible_savings:,} bytes")
        print(f"Percentage of file size: {(total_possible_savings/file_size)*100:.1f}%")
        
        # Recommendations
        print("\nRecommendations:")
        print("-" * 40)
        if risk_groups['safe']:
            print("• Start with safe modifications (unused strings)")
        if risk_groups['moderate']:
            print("• Test moderate risk changes in a backup file first")
        if risk_groups['risky']:
            print("• Carefully evaluate risky changes - they may affect functionality")
        print("• Always test modifications in a non-production environment")
        
    except Exception as e:
        print(f"Error analyzing PCF file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze PCF file for space reclamation opportunities')
    parser.add_argument('pcf_path', help='Path to PCF file to analyze')
    
    args = parser.parse_args()
    analyze_pcf_space_reclamation(args.pcf_path)

if __name__ == "__main__":
    main()
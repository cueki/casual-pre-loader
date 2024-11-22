import os
from typing import Tuple, List
from pcfcodec import PCFCodec, AttributeType
from dataclasses import dataclass

@dataclass
class PCFInfo:
    """Information about an optimized PCF."""
    offset: int
    original_size: int
    optimized_size: int
    bytes_saved: int

def find_pcfs_in_vpk(vpk_data: bytes) -> List[Tuple[int, int]]:
    """Find PCF files in VPK data, returns list of (offset, size)."""
    pcfs = []
    pos = 0
    
    while True:
        # Look for PCF header
        pos = vpk_data.find(b'<!-- dmx encoding binary', pos)
        if pos == -1:
            break
            
        # Find end of PCF by looking for next header or reasonable chunk
        next_pos = vpk_data.find(b'<!-- dmx encoding binary', pos + 100)
        if next_pos == -1:
            # If last PCF, take reasonable chunk
            pcf_size = 10000  # Assume reasonable max size
        else:
            pcf_size = next_pos - pos
        
        pcfs.append((pos, pcf_size))
        pos += 1
    
    return pcfs

def optimize_pcf(pcf_data: bytes) -> Tuple[bytes, int]:
    """Optimize a PCF and return (optimized_data, bytes_saved)."""
    with open('temp.pcf', 'wb') as f:
        f.write(pcf_data)
    
    try:
        pcf = PCFCodec()
        pcf.decode('temp.pcf')
        
        # Count original strings
        original_size = sum(len(s) + 1 if isinstance(s, bytes) else len(s.encode('ascii')) + 1 
                          for s in pcf.pcf.string_dictionary)
        
        # Find used strings
        used_strings = set()
        for element in pcf.pcf.elements:
            used_strings.add(element.type_name_index)
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                if isinstance(attr_name, bytes):
                    try:
                        used_strings.add(pcf.pcf.string_dictionary.index(attr_name))
                    except ValueError:
                        pass
                if attr_type == AttributeType.STRING and isinstance(attr_value, bytes):
                    try:
                        used_strings.add(pcf.pcf.string_dictionary.index(attr_value))
                    except ValueError:
                        pass
        
        # Calculate space saved from unused strings
        bytes_saved = sum(len(s) + 1 if isinstance(s, bytes) else len(s.encode('ascii')) + 1
                         for i, s in enumerate(pcf.pcf.string_dictionary)
                         if i not in used_strings)
        
        if bytes_saved > 0:
            # Create new dictionary with only used strings
            new_dict = []
            index_map = {}
            for old_idx, string in enumerate(pcf.pcf.string_dictionary):
                if old_idx in used_strings:
                    index_map[old_idx] = len(new_dict)
                    new_dict.append(string)
            
            # Update references
            for element in pcf.pcf.elements:
                if element.type_name_index in index_map:
                    element.type_name_index = index_map[element.type_name_index]
                
                new_attributes = {}
                for attr_name, (attr_type, attr_value) in element.attributes.items():
                    if isinstance(attr_name, bytes):
                        try:
                            old_idx = pcf.pcf.string_dictionary.index(attr_name)
                            if old_idx in index_map:
                                new_attr_name = pcf.pcf.string_dictionary[old_idx]
                            else:
                                new_attr_name = attr_name
                        except ValueError:
                            new_attr_name = attr_name
                    else:
                        new_attr_name = attr_name
                    new_attributes[new_attr_name] = (attr_type, attr_value)
                element.attributes = new_attributes
            
            pcf.pcf.string_dictionary = new_dict
            
            # Save optimized PCF
            pcf.encode('temp_optimized.pcf')
            with open('temp_optimized.pcf', 'rb') as f:
                optimized_data = f.read()
                
            return optimized_data, bytes_saved
            
        return pcf_data, 0
        
    except Exception as e:
        print(f"Error optimizing PCF: {e}")
        return pcf_data, 0
        
    finally:
        for f in ['temp.pcf', 'temp_optimized.pcf']:
            if os.path.exists(f):
                os.remove(f)

def optimize_vpk_pcfs(vpk_path: str) -> List[PCFInfo]:
    """Find and optimize all PCFs in a VPK file."""
    try:
        print(f"\nReading {vpk_path}...")
        with open(vpk_path, 'rb') as f:
            vpk_data = f.read()
        
        # Find all PCFs
        print("\nLocating PCFs...")
        pcfs = find_pcfs_in_vpk(vpk_data)
        print(f"Found {len(pcfs)} PCFs")
        
        # Optimize each PCF
        optimized = []
        total_saved = 0
        saved_bytes = bytearray()
        modified_vpk = bytearray(vpk_data)
        
        for i, (offset, size) in enumerate(pcfs, 1):
            print(f"\nProcessing PCF {i}/{len(pcfs)} at offset {offset} (0x{offset:X})")
            pcf_data = vpk_data[offset:offset + size]
            
            # Try to optimize
            optimized_data, bytes_saved = optimize_pcf(pcf_data)
            
            if bytes_saved > 0:
                optimized.append(PCFInfo(
                    offset=offset,
                    original_size=len(pcf_data),
                    optimized_size=len(optimized_data),
                    bytes_saved=bytes_saved
                ))
                
                # Write optimized PCF
                modified_vpk[offset:offset + len(optimized_data)] = optimized_data
                # Save freed bytes
                saved_bytes.extend(pcf_data[len(optimized_data):])
                total_saved += bytes_saved
                print(f"Optimized: saved {bytes_saved} bytes")
        
        if total_saved > 0:
            print(f"\nWriting output files...")
            
            # Write optimized VPK with byte pool
            with open(vpk_path + '.optimized', 'wb') as f:
                f.write(modified_vpk)
                f.write(saved_bytes)
            print(f"Created optimized VPK with {total_saved} bytes saved")
            
            # Write byte pool separately
            with open(vpk_path + '.bytepool', 'wb') as f:
                f.write(saved_bytes)
            print(f"Saved byte pool")
            
            print("\nOptimization details:")
            for info in optimized:
                print(f"\nPCF at offset {info.offset} (0x{info.offset:X}):")
                print(f"  Original size: {info.original_size} bytes")
                print(f"  Optimized size: {info.optimized_size} bytes")
                print(f"  Bytes saved: {info.bytes_saved} bytes")
        
        return optimized
        
    except Exception as e:
        print(f"Error processing VPK: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimize PCFs in VPK and collect saved bytes')
    parser.add_argument('--vpk', type=int, nargs='+', help='Specific VPK numbers to process')
    parser.add_argument('--range', type=int, nargs=2, metavar=('START', 'END'),
                       help='Process range of VPKs (e.g., 0 26)')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup before modifying')
    
    args = parser.parse_args()
    
    if not (args.vpk or args.range):
        parser.error("Must specify either --vpk or --range")
    
    # Determine which VPKs to process
    vpk_numbers = []
    if args.vpk:
        vpk_numbers.extend(args.vpk)
    if args.range:
        vpk_numbers.extend(range(args.range[0], args.range[1] + 1))
    
    vpk_numbers = sorted(set(vpk_numbers))
    total_bytes_saved = 0
    
    # Process each VPK
    for vpk_num in vpk_numbers:
        vpk_filename = f"tf2_misc_{vpk_num:03d}.vpk"
        
        if not os.path.exists(vpk_filename):
            print(f"\nSkipping {vpk_filename} - file not found")
            continue
        
        print(f"\nProcessing {vpk_filename}")
        print("=" * 60)
        
        if args.backup:
            backup_path = vpk_filename + '.backup'
            print(f"Creating backup at: {backup_path}")
            with open(vpk_filename, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
        
        results = optimize_vpk_pcfs(vpk_filename)
        total_saved = sum(r.bytes_saved for r in results)
        total_bytes_saved += total_saved
        
        if total_saved > 0:
            print(f"\nSaved {total_saved} bytes in {vpk_filename}")
    
    if total_bytes_saved > 0:
        print(f"\nTotal bytes saved across all VPKs: {total_bytes_saved} ({total_bytes_saved/1024:.2f} KB)")

if __name__ == "__main__":
    main()
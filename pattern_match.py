import os
from typing import List, Tuple, Optional
import re

def read_binary_file(filename: str) -> bytes:
    """Read entire file as bytes."""
    with open(filename, 'rb') as f:
        return f.read()

def get_pcf_signature(pcf_path: str) -> bytes:
    """Extract a unique binary signature from PCF file."""
    pcf_data = read_binary_file(pcf_path)
    
    # Get the PCF header (everything up to the first null byte)
    header_end = pcf_data.index(b'\x00')
    header = pcf_data[:header_end]
    
    # Get a chunk of data after the header for stronger matching
    signature_chunk_size = 256  # Adjust this value based on needs
    signature = pcf_data[header_end:header_end + signature_chunk_size]
    
    return header + signature

def add_missing_zeros(i: int) -> str:
    """Pad numbers with leading zeros."""
    if i < 10:
        return f"00{i}"
    if i < 100:
        return f"0{i}"
    return str(i)

def find_binary_pattern(data: bytes, pattern: bytes, context_size: int = 100) -> List[Tuple[int, bytes]]:
    """Find all occurrences of pattern in data with context."""
    matches = []
    start = 0
    
    while True:
        try:
            index = data.index(pattern, start)
            
            # Get context around match
            context_start = max(0, index - context_size)
            context_end = min(len(data), index + len(pattern) + context_size)
            context = data[context_start:context_end]
            
            matches.append((index, context))
            start = index + 1
            
        except ValueError:
            break
    
    return matches

def search_vpks_for_pcf(pcf_path: str, vpk_dir: str, start_vpk: int = 0, end_vpk: int = 26) -> None:
    """
    Search through VPK files for binary patterns matching a PCF file.
    
    Args:
        pcf_path: Path to the PCF file to search for
        vpk_dir: Directory containing VPK files
        start_vpk: Starting VPK number (default: 0)
        end_vpk: Ending VPK number (default: 26)
    """
    # Get PCF signature
    try:
        pcf_signature = get_pcf_signature(pcf_path)
        print(f"Generated signature from {pcf_path} ({len(pcf_signature)} bytes)")
        print(f"Signature starts with: {pcf_signature[:50].hex()}")
    except FileNotFoundError:
        print(f"Error: PCF file {pcf_path} not found")
        return
    except Exception as e:
        print(f"Error reading PCF file: {e}")
        return

    total_matches = 0
    
    # Search through VPK files
    for vpk_num in range(start_vpk, end_vpk + 1):
        vpk_filename = f"tf2_misc_{add_missing_zeros(vpk_num)}.vpk"
        vpk_path = os.path.join(vpk_dir, vpk_filename)
        
        try:
            print(f"\nSearching {vpk_filename}...")
            vpk_data = read_binary_file(vpk_path)
            
            # Find matches with context
            matches = find_binary_pattern(vpk_data, pcf_signature)
            
            if matches:
                print(f"Found {len(matches)} potential matches in {vpk_filename}")
                total_matches += len(matches)
                
                for i, (offset, context) in enumerate(matches, 1):
                    print(f"\nMatch #{i} at offset: {offset} (0x{offset:X})")
                    print("Context preview:")
                    print("-" * 60)
                    
                    # Try to show some readable context
                    try:
                        # Convert non-printable bytes to dots for readability
                        readable = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in context)
                        print(readable)
                    except Exception as e:
                        print(f"Error displaying context: {e}")
                    
                    print("-" * 60)
            else:
                print("No matches found")
                
        except FileNotFoundError:
            print(f"Warning: VPK file {vpk_filename} not found")
        except Exception as e:
            print(f"Error processing {vpk_filename}: {e}")
    
    print(f"\nSearch complete. Found {total_matches} total potential matches.")

def main():
    """Main entry point with example usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search VPK files for PCF binary patterns')
    parser.add_argument('pcf_path', help='Path to the PCF file to search for')
    parser.add_argument('--vpk-dir', default='.', help='Directory containing VPK files')
    parser.add_argument('--start', type=int, default=0, help='Starting VPK number')
    parser.add_argument('--end', type=int, default=26, help='Ending VPK number')
    
    args = parser.parse_args()
    
    search_vpks_for_pcf(args.pcf_path, args.vpk_dir, args.start, args.end)

if __name__ == "__main__":
    main()
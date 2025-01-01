from typing import Dict, List
from pathlib import Path
import os
from models.pcf_file import PCFFile


class PCFHandler:
    def __init__(self, vpk_handler):
        self.vpk = vpk_handler

    def list_pcf_files(self) -> List[str]:
        return self.vpk.find_files('*.pcf')

    def process_pcf(self, pcf_name: str, processor: callable, create_backup: bool = True) -> bool:
        """
        Process a PCF file using a provided processor function.
        pcf_name can be just the filename (e.g., 'explosion.pcf') or a full path
        The processor function should take a PCFFile object and return modified bytes.
        """
        # If it's just a filename, find its full path
        if '/' not in pcf_name:
            full_path = self.vpk.find_file_path(pcf_name)
            if not full_path:
                print(f"Could not find PCF file: {pcf_name}")
                return False
        else:
            full_path = pcf_name

        # Create temp file for processing
        temp_path = f"temp_{Path(pcf_name).name}"

        try:
            # Extract PCF
            if not self.vpk.extract_file(full_path, temp_path):
                print(f"Failed to extract {full_path}")
                return False

            # Load and process PCF
            pcf = PCFFile(temp_path)
            pcf.decode()

            # Apply processor function
            processed_pcf = processor(pcf)

            # Encode processed PCF to temp file
            processed_pcf.encode(temp_path)

            # Read processed data
            with open(temp_path, 'rb') as f:
                new_data = f.read()

            # Patch back into VPK
            return self.vpk.patch_file(full_path, new_data, create_backup)

        except Exception as e:
            print(f"Error processing PCF: {e}")
            return False

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def batch_process(self, pattern: str, processor: callable,
                      create_backup: bool = True) -> Dict[str, bool]:
        """
        Process multiple PCF files matching a pattern.
        Returns dictionary of {filepath: success}
        """
        results = {}
        for pcf_path in self.vpk.find_files(pattern):
            results[pcf_path] = self.process_pcf(pcf_path, processor, create_backup)
        return results
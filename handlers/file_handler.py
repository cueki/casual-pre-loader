from typing import List
from pathlib import Path
import os
from models.pcf_file import PCFFile


class FileHandler:
    def __init__(self, vpk_handler):
        self.vpk = vpk_handler

    def list_pcf_files(self) -> List[str]:
        return self.vpk.find_files('*.pcf')

    def list_vmt_files(self) -> List[str]:
        return self.vpk.find_files('*.vmt')

    def process_file(self, file_name: str, processor: callable, create_backup: bool = True) -> bool:
        """
        Process a file using a provided processor function.
        Args:
            file_name: Can be just the filename (e.g., 'explosion.pcf') or a full path if you know it
            processor: Callable that modifies the temporary file extracted from the vpk
            create_backup: Whether to create a backup of the vpk before modifying
        Returns:
            bool: Success or failure
        """
        # If it's just a filename, find its full path
        if '/' not in file_name:
            full_path = self.vpk.find_file_path(file_name)
            if not full_path:
                print(f"Could not find file: {file_name}")
                return False
        else:
            full_path = file_name

        # Create temp file for processing
        temp_path = f"temp_{Path(file_name).name}"

        try:
            # Extract file as temporary for processing
            if not self.vpk.extract_file(full_path, temp_path):
                print(f"Failed to extract {full_path}")
                return False

            # Process based on file type
            file_type = Path(file_name).suffix.lower()
            if file_type == '.pcf':
                old_pcf = PCFFile(temp_path)
                old_pcf.decode()
                new_pcf = processor(old_pcf)
                new_pcf.encode(temp_path)
            elif file_type == '.vmt':
                with open(temp_path, 'rb') as f:
                    old_vmt = f.read()
                new_vmt = processor(old_vmt)
                with open(temp_path, 'wb') as f:
                    f.write(new_vmt)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

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

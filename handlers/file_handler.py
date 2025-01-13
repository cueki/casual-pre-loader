import os
from typing import List
from pathlib import Path
from models.pcf_file import PCFFile


class FileHandler:
    def __init__(self, vpk_handler):
        self.vpk = vpk_handler

    def list_pcf_files(self) -> List[str]:
        return self.vpk.find_files('*.pcf')

    def list_vmt_files(self) -> List[str]:
        return self.vpk.find_files('*.vmt')

    def process_file(self, file_name: str, processor: callable, create_backup: bool = True) -> bool:
        # if it's just a filename, find its full path
        if '/' not in file_name:
            full_path = self.vpk.find_file_path(file_name)
            if not full_path:
                print(f"Could not find file: {file_name}")
                return False
        else:
            full_path = file_name

        # create temp file for processing
        temp_path = f"temp_{Path(file_name).name}"

        try:
            # get original file size before any processing
            entry_info = self.vpk.get_file_entry(full_path)
            if not entry_info:
                print(f"Failed to get file entry for {full_path}")
                return False
            original_size = entry_info[2].entry_length

            # extract file as temporary for processing
            if not self.vpk.extract_file(full_path, temp_path):
                print(f"Failed to extract {full_path}")
                return False

            # process based on file type
            file_type = Path(file_name).suffix.lower()
            if file_type == '.pcf':
                pcf = PCFFile(temp_path)
                pcf.decode()
                processed = processor(pcf)
                processed.encode(temp_path)

                # read processed PCF data and check size
                with open(temp_path, 'rb') as f:
                    new_data = f.read()

                if len(new_data) != original_size:
                    # print(f"WARNING: PCF size mismatch in {file_name}")
                    # print(f"Original size: {original_size}, New size: {len(new_data)}")
                    if len(new_data) < original_size:
                        padding_needed = original_size - len(new_data)
                        print(f"Adding {padding_needed} bytes of padding")
                        new_data = new_data[:-1] + b' ' * padding_needed + new_data[-1:]
                    else:
                        print(f"ERROR: New PCF is {len(new_data) - original_size} bytes larger than original!")
                        return False

            elif file_type == '.vmt':
                with open(temp_path, 'rb') as f:
                    content = f.read()
                new_data = processor(content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # patch back into VPK
            return self.vpk.patch_file(full_path, new_data, create_backup)

        except Exception as e:
            print(f"Error processing file: {e}")
            return False

        finally:
            # cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
import os
import shutil
import traceback
from typing import List
from pathlib import Path
from valve_parsers import VPKFile, PCFFile
from core.folder_setup import folder_setup


def copy_config_files(custom_content_dir):
    # config copy
    config_dest_dir = custom_content_dir / "cfg" / "w"
    config_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/cfg/w/config.cfg', config_dest_dir)

    # vscript copy
    vscript_dest_dir = custom_content_dir / "scripts" / "vscripts"
    vscript_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/scripts/vscripts/randommenumusic.nut', vscript_dest_dir)

    # vgui copy
    vgui_dest_dir = custom_content_dir / "resource" / "ui"
    vgui_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/resource/ui/vguipreload.res', vgui_dest_dir)


class FileHandler:
    def __init__(self, vpk_file_path: str):
        self.vpk = VPKFile(str(vpk_file_path))

    def list_pcf_files(self) -> List[str]:
        return self.vpk.find_files('*.pcf')

    def list_vmt_files(self) -> List[str]:
        return self.vpk.find_files('*.vmt')

    def process_file(self, file_name: str, processor: callable, create_backup: bool = True) -> bool | None:
        # if it's just a filename, find its full path
        if '/' not in file_name:
            full_path = self.vpk.find_file_path(file_name)
            if not full_path:
                print(f"Could not find file: {file_name}")
                return False
        else:
            full_path = file_name

        # create temp file for processing in working directory
        temp_path = folder_setup.get_temp_path(f"temp_{Path(file_name).name}")

        try:
            # get original file info
            file_info = self.vpk.get_file_info(full_path)
            if not file_info:
                print(f"Failed to get file info for {full_path}")
                return False
            original_size = file_info['size']

            # process based on file type
            file_type = Path(file_name).suffix.lower()
            if file_type == '.pcf':
                # get file data directly into memory for PCF processing
                pcf_data = self.vpk.get_file_data(full_path)
                if not pcf_data:
                    print(f"Failed to get data for {full_path}")
                    return False
                
                # write to temp file for PCF processing
                with open(temp_path, 'wb') as f:
                    f.write(pcf_data)
                
                pcf = PCFFile(temp_path).decode()
                processed = processor(pcf)
                processed.encode(temp_path)

                # read processed PCF data and check size
                with open(temp_path, 'rb') as f:
                    new_data = f.read()

            elif file_type in ['.vmt', '.txt', '.res']:
                # get file data directly into memory for text processing
                content = self.vpk.get_file_data(full_path)
                if not content:
                    print(f"Failed to get data for {full_path}")
                    return False
                new_data = processor(content)

            else:
                print(f"Error: Unsupported file type '{file_type}' for file {file_name}")
                return False

            # check if the processed file size matches the original size
            if len(new_data) != original_size:
                if len(new_data) < original_size:
                    # pad to match original size
                    padding_needed = original_size - len(new_data)
                    print(f"Adding {padding_needed} bytes of padding to {file_name}")
                    new_data = new_data + b' ' * padding_needed

                else:
                    print(f"ERROR: {file_name} is {len(new_data) - original_size} bytes larger than original! "
                          f"This should be ignored unless you know what you are doing")
                    return False

            # patch back into VPK
            return self.vpk.patch_file(full_path, new_data, create_backup)

        except Exception as e:
            print(f"Error processing file {file_name}:")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception message: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            return False

        finally:
            # cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

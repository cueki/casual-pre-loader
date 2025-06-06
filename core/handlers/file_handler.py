import os
import shutil
import traceback
from typing import List
from pathlib import Path
from core.parsers.pcf_file import PCFFile
from core.parsers.vpk_file import VPKFile
from core.folder_setup import folder_setup


def copy_config_files(custom_content_dir, skip_valve_rc=False):
    # config copy
    config_dest_dir = custom_content_dir / "cfg" / "w"
    config_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/cfg/w/config.cfg', config_dest_dir)

    # valve.rc copy
    if not skip_valve_rc:
        valverc_dest_dir = custom_content_dir / "cfg"
        valverc_dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(folder_setup.install_dir / 'backup/cfg/valve.rc', valverc_dest_dir)

    # vscript copy
    vscript_dest_dir = custom_content_dir / "scripts" / "vscripts"
    vscript_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/scripts/vscripts/randommenumusic.nut', vscript_dest_dir)

    # vgui copy
    vgui_dest_dir = custom_content_dir / "resource" / "ui"
    vgui_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/resource/ui/vguipreload.res', vgui_dest_dir)


def scan_for_valve_rc_files(tf_path):
    if not tf_path:
        return [], False

    custom_dir = Path(tf_path) / 'custom'
    if not custom_dir.exists():
        return [], False

    found_files = []

    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue

        if item.is_dir():
            valve_rc_file = item / "cfg" / "valve.rc"
            if valve_rc_file.exists():
                found_files.append(f"Folder: {item.name}/cfg/valve.rc")

        elif (item.is_file() and
              item.suffix.lower() == ".vpk"):
            try:
                vpk_file = VPKFile(str(item))
                vpk_file.parse_directory()
                valve_path = vpk_file.find_file_path("cfg/valve.rc")
                if valve_path or vpk_file.find_file_path("valve.rc"):
                    found_files.append(f"VPK: {item.name}")
            except Exception as e:
                print(f"Error checking VPK {item}: {e}")

    valve_rc_found = len(found_files) > 0

    return found_files, valve_rc_found


class FileHandler:
    def __init__(self, vpk_file_path: str):
        self.vpk = VPKFile(str(vpk_file_path))
        self.vpk.parse_directory()

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
            # get original file size before any processing
            entry_info = self.vpk.get_file_entry(full_path)
            if not entry_info:
                print(f"Failed to get file entry for {full_path}")
                return False
            original_size = entry_info[2].entry_length

            # extract file as temporary for processing
            if not self.vpk.extract_file(full_path, str(temp_path)):
                print(f"Failed to extract {full_path}")
                return False

            # process based on file type
            file_type = Path(file_name).suffix.lower()
            if file_type == '.pcf':
                pcf = PCFFile(temp_path).decode()
                processed = processor(pcf)
                processed.encode(temp_path)

                # read processed PCF data and check size
                with open(temp_path, 'rb') as f:
                    new_data = f.read()
            elif file_type in ['.vmt', '.txt', '.res']:
                with open(temp_path, 'rb') as f:
                    content = f.read()
                new_data = processor(content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # check if the processed file size matches the original size
            if len(new_data) != original_size:
                if len(new_data) < original_size:
                    # maintain proper termination
                    padding_needed = original_size - len(new_data)
                    print(f"Adding {padding_needed} bytes of padding to {file_name}")
                    new_data = new_data[:-1] + b' ' * padding_needed + new_data[-1:]
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

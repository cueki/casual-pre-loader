import logging
import os
import shutil
from pathlib import Path
from typing import List

from valve_parsers import PCFFile, VPKFile

from core.folder_setup import folder_setup

log = logging.getLogger()

def generate_config(has_mastercomfig=False, needs_quickprecache=False, show_console=True):
    config_parts = []
    config_parts.append('sv_pure -1; sv_allow_point_servercommand always; map itemtest; wait 10; script_execute randommenumusic; disconnect; wait 1; clear')

    if has_mastercomfig:
        config_parts.append('exec comfig/echo')

    if needs_quickprecache:
        config_parts.append('exec quickprecache.cfg')

    final_part = 'playmenumusic'
    if show_console:
        final_part += '; showconsole'

    final_part += '; exec w/kitty.cfg'
    config_parts.append(final_part)

    return '; '.join(config_parts) + '\n'


def copy_config_files(custom_content_dir):
    # config copy
    config_dest_dir = custom_content_dir / "cfg" / "w"
    config_dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(folder_setup.install_dir / 'backup/cfg/w/config.cfg', config_dest_dir)
    shutil.copy2(folder_setup.install_dir / 'backup/cfg/w/kitty.cfg', config_dest_dir)

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

    def process_file(self, file_name: str, content) -> bool | None:
        # if it's just a filename, find its full path
        if '/' not in file_name:
            full_path = self.vpk.find_file_path(file_name)
            if not full_path:
                log.warning(f"Could not find file: {file_name}")
                return False
        else:
            full_path = file_name

        # create temp file for processing in working directory
        temp_path = folder_setup.temp_dir / f"temp_{Path(file_name).name}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # get original file info
            file_info = self.vpk.get_file_info(full_path)
            if not file_info:
                log.warning(f"Failed to get file info for {full_path}")
                return False
            original_size = file_info['size']

            if isinstance(content, PCFFile):
                # encode PCF to get bytes
                content.encode(temp_path)
                with open(temp_path, 'rb') as f:
                    new_data = f.read()
            elif isinstance(content, bytes):
                # already have bytes
                new_data = content
            else:
                log.error(f"Unsupported content type '{type(content).__name__}' for file {file_name}", stack_info=True)
                return False

            # check if the processed file size matches the original size
            if len(new_data) != original_size:
                if len(new_data) < original_size:
                    # pad to match original size
                    padding_needed = original_size - len(new_data)
                    log.info(f"Adding {padding_needed} bytes of padding to {file_name}")
                    new_data = new_data + b' ' * padding_needed

                else:
                    log.warning(
                            f"{file_name} is {len(new_data) - original_size} bytes larger than original! This should be ignored unless you know what you are doing"
                    )
                    return False

            # patch back into VPK
            return self.vpk.patch_file(full_path, new_data, create_backup=False)

        except Exception:
            log.exception(f"Error processing file {file_name}")
            return False

        finally:
            # cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

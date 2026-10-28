import logging
from pathlib import Path

from valve_parsers import PCFFile, VPKFile

from core.config import config
from core.util.file import copyfile, delete

log = logging.getLogger()

def generate_config(has_mastercomfig: bool = False, needs_quickprecache: bool = False, show_console: bool = True):
    config_parts = [
        'sv_pure -1; sv_allow_point_servercommand always; map itemtest; wait 10; script_execute randommenumusic; disconnect; wait 1; clear'
    ]

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
    config_dest_dir = custom_content_dir / 'cfg' / 'w'
    config_dest_dir.mkdir(parents=True, exist_ok=True)
    copyfile(config.install_dir / 'backup/cfg/w/config.cfg', config_dest_dir)
    copyfile(config.install_dir / 'backup/cfg/w/kitty.cfg', config_dest_dir)

    vscript_dest_dir = custom_content_dir / 'scripts' / 'vscripts'
    vscript_dest_dir.mkdir(parents=True, exist_ok=True)
    copyfile(config.install_dir / 'backup/scripts/vscripts/randommenumusic.nut', vscript_dest_dir)

    # vgui copy: vguipreload.res plus everything it #bases.
    # mainmenuoverride.res is excluded, it gets placed separately by patch_mainmenuoverride()
    vgui_dest_dir = custom_content_dir / 'resource' / 'ui'
    vgui_dest_dir.mkdir(parents=True, exist_ok=True)
    for file in (config.install_dir / 'backup/resource/ui').iterdir():
        if file.suffix == '.res' and file.stem.lower() != 'mainmenuoveride':
            copyfile(file, vgui_dest_dir)


class FileHandler:
    def __init__(self, vpk_file: Path):
        self.vpk = VPKFile(vpk_file)

    def list_pcf_files(self) -> list[str]:
        return self.vpk.find_files('*.pcf')

    def list_vmt_files(self) -> list[str]:
        return self.vpk.find_files('*.vmt')

    def process_file(self, file_name: str, content: bytes | PCFFile) -> bool:
        # if it's just a filename, find its full path
        if '/' not in file_name:
            full_path = self.vpk.find_file_path(file_name)
            if not full_path:
                log.warning(f'Could not find file: {file_name}')
                return False
        else:
            full_path = file_name

        temp_path = config.temp_dir / file_name
        temp_path = temp_path.with_name('temp_' + temp_path.name)
        try:
            file_info = self.vpk.get_file_info(full_path)
            if not file_info:
                log.warning(f'Failed to get file info for {full_path}')
                return False
            original_size = file_info['size']

            if isinstance(content, PCFFile):
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                content.encode(temp_path) # encode PCF to get bytes
                with temp_path.open('rb') as fd:
                    content = fd.read()
            elif not isinstance(content, bytes):
                log.error(f'Unsupported content type {type(content)} for file {file_name}', stack_info=True)
                return False

            padding = original_size - len(content)
            if padding > 0:
                log.debug(f'Adding {padding} bytes of padding to {file_name}')
                new_data = content + b' ' * padding
                return self.vpk.patch_file(full_path, new_data, create_backup=False)
            elif padding < 0:
                log.warning(f'{file_name} is {-padding} bytes larger than original! This should be ignored unless you know what you are doing')
                return False
        except Exception:
            log.exception(f'Error processing file {file_name}')
            return False
        finally:
            if temp_path.is_file():
                delete(temp_path)

        return True

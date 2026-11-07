import logging
import shutil
from fnmatch import fnmatchcase
from pathlib import Path

from valve_parsers import VPKFile

from core.config import config
from core.constants import (
    BACKUP_MAINMENU_FOLDER,
    VGUI_PRELOAD_EXCLUDE,
    VGUI_PRELOAD_FILE,
    VGUI_PRELOAD_GROUPS,
)
from core.util.vpk import normalize_vpk_paths

log = logging.getLogger()


def patch_mainmenuoverride(tf_path: Path):
    custom_dir = tf_path / 'custom'
    if not custom_dir.is_dir():
        return

    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue

        if (item.is_file() and
              item.suffix.lower() == ".vpk" and
              "casual_preloader" not in item.name.lower()):
            _process_vpk(item)

    # check if any directory has mainmenuoverride.res
    found_mainmenuoverride = False
    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue

        if item.is_dir():
            mainmenuoverride_file = item / "resource" / "ui" / "mainmenuoverride.res"
            if mainmenuoverride_file.is_file():
                _add_vguipreload_string(mainmenuoverride_file)
                found_mainmenuoverride = True

    if not found_mainmenuoverride:
        # create backup folder in custom/ with mainmenuoverride.res
        backup_folder = custom_dir / BACKUP_MAINMENU_FOLDER
        backup_folder_custom = backup_folder / "resource" / "ui"
        backup_folder_custom.mkdir(parents=True, exist_ok=True)

        # copy mainmenuoverride.res to backup folder
        shutil.copy2(config.install_dir / 'backup/resource/ui/mainmenuoverride.res', backup_folder_custom/ 'mainmenuoverride.res')

        # info.vdf so tf2 accepts res file
        shutil.copy2(config.install_dir / 'backup/info.vdf', backup_folder / 'info.vdf')
        _add_vguipreload_string(backup_folder_custom / "mainmenuoverride.res")


def _add_vguipreload_string(file_path: Path):
    try:
        with file_path.open('r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if "vguipreload.res" not in content:
            with file_path.open('w', encoding='utf-8') as f:
                f.write('#base "vguipreload.res"\n' + content)
            return True
    except Exception:
        log.exception(f'Failed to modify {file_path}')


def _process_vpk(vpk_path: Path):
    try:
        vpk_file = VPKFile(vpk_path)
        target_files = vpk_file.find_files("resource/ui/mainmenuoverride.res")

        # skip if no mainmenuoverride.res
        if not target_files:
            return

        custom_dir = vpk_path.parent
        vpk_name = vpk_path.stem
        extract_dir = custom_dir / vpk_name
        extract_dir.mkdir(parents=True, exist_ok=True)

        vpk_file.extract_all(str(extract_dir))

        extracted_mainmenuoverride_file = extract_dir / "resource" / "ui" / "mainmenuoverride.res"
        _add_vguipreload_string(extracted_mainmenuoverride_file)

        # delete the original VPK file
        vpk_path.unlink()

    except Exception:
        log.exception(f"Error extracting VPK {vpk_path}")


def generate_vgui_preload(custom_content_dir: Path, custom_dir: Path) -> int:
    '''
    Write VGUI_PRELOAD_FILE, which vguipreload.res #bases, with an ImagePanel for every material picked by VGUI_PRELOAD_GROUPS.

    Materials are gathered from custom_content_dir and everything in custom_dir,
    except our own VPK since custom_content_dir is about to replace it.

    Args:
        custom_content_dir: Content waiting to be packed into our VPK, the file is written to its resource/ui folder.
        custom_dir: The game's custom/ directory.

    Returns:
        The number of ImagePanel entries written.
    '''

    try:
        # material paths relative to materials/
        materials = _index_folder(custom_content_dir)

        vpk_paths = []
        for item in sorted(custom_dir.iterdir()):
            if '_casual_preloader' in item.name.lower():
                continue

            if item.is_dir():
                materials |= _index_folder(item)
            elif item.suffix.lower() == '.vpk':
                vpk_paths.append(item)

        for vpk_path in normalize_vpk_paths(vpk_paths):
            materials |= _index_vpk(vpk_path)

        entries = []
        seen = set()
        for group, settings in VGUI_PRELOAD_GROUPS.items():
            entries.append(f'\n\t\t// {group.upper()}\n')
            for path in _select_materials(materials, settings):
                if path in seen:
                    continue
                seen.add(path)

                # I dont know if this is required but we write both
                name = path.rsplit('/', 1)[-1]
                entries.append(_image_panel(name, f'../{path}.vmt'))
                entries.append(_image_panel(name, f'../{path}.vtf'))

        output_file = custom_content_dir / 'resource' / 'ui' / VGUI_PRELOAD_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            '"Resource/UI/MainMenuOverride.res"\n'
            '{\n'
            '\t"PreloadPanel"\n'
            '\t{\n'
            '\t\t"ControlName"\t"EditablePanel"\n'
            '\t\t"fieldName"\t"PreloadPanel"\n'
            '\t\t"xpos"\t"6969"\n'
            '\t\t"visible"\t"1"\n'
            + ''.join(entries) +
            '\t}\n'
            '}\n',
            encoding='utf-8',
        )

        count = len(seen) * 2
        log.info(f'Wrote {count} vgui preload entries to {output_file}')
        return count

    except Exception:
        log.exception('Failed to generate vgui preload')
        return 0


def _index_folder(root: Path) -> set[str]:
    '''
    Find the materials in a loose mod folder.

    Args:
        root: The mod folder, i.e. the one containing materials/.

    Returns:
        Lowercase material paths relative to materials/ without an extension.
    '''

    materials = set()
    if not root.is_dir():
        return materials

    # case-sensitive filesystems can have both materials/ and Materials/
    for materials_dir in root.iterdir():
        if not (materials_dir.is_dir() and materials_dir.name.lower() == 'materials'):
            continue
        for dirpath, _, filenames in materials_dir.walk():
            for filename in filenames:
                file = dirpath / filename
                if file.is_file() and file.suffix.lower() in ('.vmt', '.vtf'):
                    materials.add(file.relative_to(materials_dir).with_suffix('').as_posix().lower())

    return materials


def _index_vpk(vpk_path: Path) -> set[str]:
    '''
    Find the materials in a VPK. Errors are logged rather than raised so one bad VPK does not stop the install.

    Args:
        vpk_path: The VPK to read, for multi-part VPKs this is the _dir.vpk.

    Returns:
        Lowercase material paths relative to materials/ without an extension.
    '''

    materials = set()
    try:
        vpk_file = VPKFile(vpk_path)
        for extension in ('vmt', 'vtf'):
            for file_path in vpk_file.list_files(extension=extension):
                file_path = file_path.lower()
                if file_path.startswith('materials/'):
                    materials.add(file_path.removeprefix('materials/').removesuffix(f'.{extension}'))
    except Exception:
        log.exception(f'Failed to read {vpk_path} for vgui preload, skipping it')

    return materials


def _select_materials(materials: set[str], settings: dict) -> list[str]:
    '''
    Pick the materials that belong to a VGUI_PRELOAD_GROUPS group.

    Args:
        materials: Material paths as returned by _index_folder() and _index_vpk().
        settings: The group's settings, materials must match an "include" pattern and no "exclude" pattern.

    Returns:
        The selected material paths, sorted, without anything in VGUI_PRELOAD_EXCLUDE.
    '''

    exclude = settings.get('exclude', [])
    return sorted(
        path for path in materials
        if any(fnmatchcase(path, pattern) for pattern in settings['include'])
        and path not in VGUI_PRELOAD_EXCLUDE
        and not any(fnmatchcase(path, pattern) for pattern in exclude)
    )


def _image_panel(name: str, image: str) -> str:
    '''
    Format an ImagePanel entry for the PreloadPanel.

    Args:
        name: The panel's name.
        image: The image path, relative to materials/vgui/.

    Returns:
        The entry as KeyValues text.
    '''

    return (
        f'\t\t"{name}"\n'
        '\t\t{\n'
        '\t\t\t"ControlName"\t"ImagePanel"\n'
        '\t\t\t"visible"\t"1"\n'
        f'\t\t\t"image"\t"{image}"\n'
        '\t\t}\n'
    )

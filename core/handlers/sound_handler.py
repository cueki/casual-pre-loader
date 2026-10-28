import logging
import re
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import TypedDict

from valve_parsers import VPKFile

from core.util.file import copyfile, move

log = logging.getLogger()


class SoundMapping(TypedDict):
    source_file: Path
    canonical_path: Path
    final_path: Path


class ProcessStatus(TypedDict):
    files_moved: int
    scripts_updated: int
    scripts_copied: int
    message: str

class SoundHandler:
    sound_extensions = ('.wav', '.mp3')
    script_extensions = ('.txt')

    def process_temp_sound_mods(self, temp_mods_dir: Path, backup_scripts_dir: Path, vpk_paths: list[Path]) -> ProcessStatus | None:
        temp_sound_dir = temp_mods_dir / 'sound'
        if not temp_sound_dir.is_dir():
            return

        all_sound_files = [
            f
            for root, dirs, files in temp_sound_dir.walk()
            for file in files
            if (f := root / file).suffix.lower() in self.sound_extensions
        ]

        if not all_sound_files:
            return

        file_mappings = create_vpk_based_mappings(all_sound_files, vpk_paths)
        if not file_mappings:
            return {
                'files_moved': 0,
                'scripts_updated': 0,
                'scripts_copied': 0,
                'message': 'No sound files found in VPK for mapping'
            }

        # collect paths for script searching
        canonical_paths = [mapping['canonical_path'] for mapping in file_mappings]

        # identify which script files are needed
        needed_scripts = identify_needed_scripts(canonical_paths, backup_scripts_dir)

        # copy needed script files to temp_mods_dir/scripts/ (excluding any sound script files from mods)
        temp_scripts_dir = temp_mods_dir / 'scripts'
        copied_scripts = copy_needed_scripts(needed_scripts, temp_scripts_dir)

        # move/restructure sound files based on VPK mappings
        n_moved_files = move_sound_files(file_mappings)

        # update script files with final paths
        modified_scripts = []
        if copied_scripts and file_mappings:
            modified_scripts = update_script_paths(copied_scripts, file_mappings)

        return {
            'files_moved': n_moved_files,
            'scripts_updated': len(modified_scripts),
            'scripts_copied': len(copied_scripts),
            'message': f'Moved {n_moved_files} sounds, updated {len(copied_scripts)} scripts'
        }


def identify_needed_scripts(canonical_paths: list[Path], backup_scripts_dir: Path) -> list[Path]:
    # identify script files needed based on VPK paths
    needed_scripts = set()

    # normalize paths for matching
    paths_to_match = {path.with_suffix('').as_posix().lower() for path in canonical_paths}

    # scan all *sound*.txt files in backup directory
    for script_path in list(backup_scripts_dir.glob('*sound*.txt')):
        try:
            with script_path.open('r', encoding='utf-8', errors='ignore') as fd:
                content = fd.read().lower().replace('\\', '/')

            # check if any paths appear in this script file
            found_matches = []
            for path in paths_to_match:
                if path in content:
                    found_matches.append(path)
                    needed_scripts.add(script_path)
        except Exception:
            log.exception(f'Error reading sound script file {script_path}')
            continue

    return list(needed_scripts)


def copy_needed_scripts(needed_scripts: list[Path], temp_scripts_dir: Path) -> list[str]:
    # copy needed script files from backup/
    temp_scripts_dir.mkdir(parents=True, exist_ok=True)
    copied_scripts = []

    for script_path in needed_scripts:
        target_path = temp_scripts_dir / script_path.name

        try:
            copyfile(script_path, target_path)
            copied_scripts.append(str(target_path))
        except Exception:
            log.exception(f'Error copying script file {script_path} to {target_path}')

    return copied_scripts


def update_script_files(script_files: list[str], path_mappings: Mapping[str, str]) -> list[str]:
    # update script files to reference the new misc/ paths
    modified_files = []
    for script_file in script_files:
        try:
            with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            log.exception(f'Error reading {script_file}')
            continue

        original_content = content
        for old_path, new_path in path_mappings.items():
            # escape the path, then make pattern flexible to match both slash types (thanks, valve)
            escaped_old_path = re.escape(old_path).replace('/', r'[/\\]')
            pattern = rf'("wave"\s*")([^"]*{escaped_old_path}[^"]*?)(")'
            # scripts don't agree with the VPK on casing (e.g. weapons/samurai/TF_Katana_01.wav),
            # so the inner match/replace has to ignore case too
            old_path_re = re.compile(re.escape(old_path), re.IGNORECASE)

            def replace_wave(match, *, old_path_re, new_path):
                prefix = match.group(1)  # "wave"    "
                wave_path = match.group(2)  # the actual path with potential special chars
                suffix = match.group(3)  # "

                # special character prefixes (like ), #, $, etc.)
                special_chars = r'[\*\#\@\>\<\^\(\)\{\}\$\!\?\&\~\`\+\%]'
                special_prefix_match = re.match(rf'^({special_chars}+)(.*)', wave_path)

                if special_prefix_match:
                    special_prefix = special_prefix_match.group(1)
                    actual_path = special_prefix_match.group(2)
                else:
                    special_prefix = ''
                    actual_path = wave_path

                # normalize actual_path to handle mixed slash types
                normalized_actual_path = actual_path.replace('\\', '/')
                if old_path_re.search(normalized_actual_path):
                    new_actual_path = old_path_re.sub(lambda _: new_path, normalized_actual_path)
                    new_wave_path = f'{special_prefix}{new_actual_path}'
                    return f'{prefix}{new_wave_path}{suffix}'

                return match.group(0)  # no change if pattern doesn't match
            replace_wave = partial(replace_wave, old_path_re=old_path_re, new_path=new_path)

            content = re.sub(pattern, replace_wave, content, flags=re.IGNORECASE)

        # write back if modified
        if content != original_content:
            try:
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files.append(script_file)
            except Exception:
                log.exception(f'Error writing {script_file}')

    return modified_files

def create_vpk_based_mappings(sound_files: list[Path], vpk_paths: list[Path]) -> list[SoundMapping]:
    # create mappings between mod sound files and their VPK paths
    vpk_files = []
    for vpk_path in vpk_paths:
        try:
            vpk = VPKFile(vpk_path)
            vpk_files.append(vpk)
        except Exception:
            log.exception(f'Error loading {vpk_path}')

    if not vpk_files:
        log.error('No valid VPK files could be loaded', stack_info=True)
        return []

    file_mappings = []
    files_to_remove = []
    vpk_no_prefix = ['misc', 'vo', 'ui']

    for sound_file in sound_files:
        # search all VPK files for this filename
        canonical_path = None
        for vpk in vpk_files:
            vpk_file_path = vpk.find_file_path(sound_file.name)
            if vpk_file_path:
                canonical_path = Path(vpk_file_path[6:])  # remove 'sound/' prefix
                break

        if canonical_path is not None:
            # determine final placement path
            if canonical_path.parts[0] in vpk_no_prefix:
                # files in vo/, ui/, misc/ don't get misc/ prefix
                final_path = canonical_path
            else:
                # other files get misc/ prefix
                final_path = Path(f'misc/{canonical_path}')

            mapping: SoundMapping = {
                'source_file': sound_file,
                'canonical_path': canonical_path,
                'final_path': final_path,
            }
            file_mappings.append(mapping)

        else:
            files_to_remove.append(sound_file)

    # remove files not found in VPK
    removed_count = 0
    for file_to_remove in files_to_remove:
        try:
            file_to_remove.unlink()
            removed_count += 1
        except Exception:
            log.exception(f'Error removing {file_to_remove}')

    return file_mappings


def move_sound_files(file_mappings: list[SoundMapping]) -> int:
    # move sound files to their VPK based locations
    n_moved_files = 0

    for mapping in file_mappings:
        sound_dir = None
        for parent in mapping['source_file'].parents:
            if parent.name == 'sound':
                sound_dir = parent
                break

        if sound_dir:
            target_path = sound_dir / mapping['final_path']
        else:
            log.error('No sound_dir found!', stack_info=True)
            break

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if move(mapping['source_file'], target_path) is not None:
                n_moved_files += 1
        except Exception:
            log.exception(f'Error moving {mapping['source_file']} to {target_path}')

    return n_moved_files


def update_script_paths(script_files: list[str], file_mappings: list[SoundMapping]) -> list[str]:
    path_mappings = {
        Path(mapping['canonical_path']).as_posix(): mapping['final_path'].as_posix() for mapping in file_mappings
    }

    return update_script_files(script_files, path_mappings)

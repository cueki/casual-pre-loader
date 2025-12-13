import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from valve_parsers import VPKFile

log = logging.getLogger()


class SoundHandler:
    def __init__(self):
        self.sound_extensions = ['.wav', '.mp3']
        self.script_extensions = ['.txt']

    def process_temp_sound_mods(self, temp_mods_dir: Path, backup_scripts_dir: Path, vpk_paths: List[Path]) -> Optional[dict]:
        temp_sound_dir = temp_mods_dir / 'sound'
        if not temp_sound_dir.exists():
            return None

        # Single scan - filter by extension in memory
        all_sound_files = [
            f for f in temp_sound_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in self.sound_extensions
        ]

        if not all_sound_files:
            return None

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
        moved_files = move_sound_files(file_mappings)

        # update script files with final paths
        modified_scripts = []
        if copied_scripts and file_mappings:
            modified_scripts = update_script_paths(copied_scripts, file_mappings)

        return {
            'files_moved': len(moved_files),
            'scripts_updated': len(modified_scripts),
            'scripts_copied': len(copied_scripts),
            'message': f'Moved {len(moved_files)} sounds, updated {len(copied_scripts)} scripts'
        }


def identify_needed_scripts(canonical_paths: List[str], backup_scripts_dir: Path) -> List[str]:
    # identify script files needed based on VPK paths
    needed_scripts = set()

    # normalize paths for matching
    paths_to_match = set()
    for path in canonical_paths:
        normalized_path = path.replace('\\', '/').lower()
        # remove extension
        path_without_ext = str(Path(normalized_path).with_suffix('')).replace('\\', '/')
        paths_to_match.add(path_without_ext)

    # scan all *sound*.txt files in backup directory
    script_files = list(backup_scripts_dir.glob('*sound*.txt'))
    found_sound_paths = set()

    for script_file in script_files:
        try:
            with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                normalized_content = content.lower().replace('\\', '/')

            # check if any paths appear in this script file
            found_matches = []
            for path in paths_to_match:
                if path in normalized_content:
                    found_matches.append(path)
                    found_sound_paths.add(path)
                    if str(script_file) not in needed_scripts:
                        needed_scripts.add(str(script_file))

        except Exception:
            log.exception(f"Error reading sound script file {script_file}")
            continue


    return list(needed_scripts)


def copy_needed_scripts(needed_scripts: List[str], temp_scripts_dir: Path) -> List[str]:
    # copy needed script files from backup/
    temp_scripts_dir.mkdir(parents=True, exist_ok=True)
    copied_scripts = []

    for script_file in needed_scripts:
        script_path = Path(script_file)
        target_path = temp_scripts_dir / script_path.name

        try:
            shutil.copy2(script_path, target_path)
            copied_scripts.append(str(target_path))
        except Exception:
            log.exception(f"Error copying script file {script_file} to {target_path}")

    return copied_scripts


def update_script_files(script_files: List[str], path_mappings: List[Tuple[str, str]]) -> List[str]:
    # update script files to reference the new misc/ paths
    modified_files = []
    for script_file in script_files:
        try:
            with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            log.exception(f"Error reading {script_file}")
            continue

        original_content = content
        for old_path, new_path in path_mappings:
            old_path = old_path.replace('\\', '/')
            new_path = new_path.replace('\\', '/')

            # escape the path, then make pattern flexible to match both slash types (thanks, valve)
            escaped_old_path = re.escape(old_path).replace('/', r'[/\\]')
            pattern = rf'("wave"\s*")([^"]*{escaped_old_path}[^"]*?)(")'

            def replace_wave(match):
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
                    special_prefix = ""
                    actual_path = wave_path

                # normalize actual_path to handle mixed slash types
                normalized_actual_path = actual_path.replace('\\', '/')
                if old_path in normalized_actual_path:
                    new_actual_path = normalized_actual_path.replace(old_path, new_path)
                    new_wave_path = f"{special_prefix}{new_actual_path}"
                    return f"{prefix}{new_wave_path}{suffix}"

                return match.group(0)  # no change if pattern doesn't match

            content = re.sub(pattern, replace_wave, content, flags=re.IGNORECASE)

        # write back if modified
        if content != original_content:
            try:
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files.append(script_file)
            except Exception:
                log.exception(f"Error writing {script_file}")

    return modified_files


def create_vpk_based_mappings(sound_files: List[Path], vpk_paths: List[Path]) -> List[Dict]:
    # create mappings between mod sound files and their VPK paths
    vpk_files = []
    for vpk_path in vpk_paths:
        try:
            vpk = VPKFile(str(vpk_path))
            vpk_files.append(vpk)
        except Exception:
            log.exception(f"Error loading {vpk_path}")
            continue

    if not vpk_files:
        log.error("No valid VPK files could be loaded", stack_info=True)
        return []

    file_mappings = []
    files_to_remove = []
    vpk_no_prefix = ['misc', 'vo', 'ui']

    for sound_file in sound_files:
        filename = sound_file.name
        canonical_path = None

        # search all VPK files for this filename
        for vpk in vpk_files:
            vpk_file_path = vpk.find_file_path(filename)
            if vpk_file_path:
                canonical_path = vpk_file_path[6:]  # remove 'sound/' prefix
                break

        if canonical_path:
            # determine final placement path
            canonical_parts = Path(canonical_path).parts
            if canonical_parts[0] in vpk_no_prefix:
                # files in vo/, ui/, misc/ don't get misc/ prefix
                final_path = canonical_path
            else:
                # other files get misc/ prefix
                final_path = f"misc/{canonical_path}"

            mapping = {
                'source_file': sound_file,
                'canonical_path': canonical_path,
                'final_path': final_path,
                'filename': filename
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
            log.exception(f"Error removing {file_to_remove}")

    return file_mappings


def move_sound_files(file_mappings: List[Dict]) -> List[Tuple[str, str]]:
    # move sound files to their VPK based locations
    moved_files = []

    for mapping in file_mappings:
        source_file = mapping['source_file']
        final_path = mapping['final_path']

        sound_dir = None
        for parent in source_file.parents:
            if parent.name == 'sound':
                sound_dir = parent
                break

        if sound_dir:
            target_path = sound_dir / final_path
        else:
            log.error(f"No {sound_dir} found!", stack_info=True)
            break

        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if source_file != target_path:  # only move if different
                shutil.move(str(source_file), str(target_path))
                moved_files.append((str(source_file), str(target_path)))
        except Exception:
            log.exception(f"Error moving {source_file} to {target_path}")

    return moved_files


def update_script_paths(script_files: List[str], file_mappings: List[Dict]) -> List[str]:
    # create mapping from canonical path to final path
    path_mappings = {}
    for mapping in file_mappings:
        canonical_with_ext = str(Path(mapping['canonical_path'])).replace('\\', '/')
        final_with_ext = str(Path(mapping['final_path'])).replace('\\', '/')
        path_mappings[canonical_with_ext] = final_with_ext

    return update_script_files(script_files, list(path_mappings.items()))

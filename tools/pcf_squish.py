import os
import copy
import shutil
from pathlib import Path
from typing import List, Set, Dict
from parsers.pcf_file import PCFFile
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.pcf_merge import merge_pcf_files
from operations.pcf_compress import remove_duplicate_elements
from core.folder_setup import folder_setup


def create_dx8_copies(file_handler, mods_dir: Path):
    # quick hack to generate dx8 files? might be an awful idea. (DISABLED FOR NOW)
    dx8_list = [f[:-9] for f in file_handler.list_pcf_files() if '_dx80' in f.lower()]
    dx8_list = [f for f in dx8_list if f != 'particles/explosion']

    for mod_file in mods_dir.glob('*.pcf'):
        mod_base = "particles/" + str(mod_file.stem)
        if mod_base in dx8_list:
            dx8_path = mod_file.parent / f"{mod_file.stem}_dx80.pcf"
            print(f"Creating dx8 copy: {dx8_path}")
            try:
                shutil.copy2(mod_file, dx8_path)
            except Exception as e:
                print(f"Error creating dx8 copy for {mod_file}: {e}")

def check_compressed_size(pcf: PCFFile):
    # check the size of the compressed pcf to make sure it fits
    compressed_path = folder_setup.get_temp_path("temp_size_check.pcf")
    test_pcf = copy.deepcopy(pcf)
    compressed = remove_duplicate_elements(test_pcf)
    compressed.encode(compressed_path)
    size = os.path.getsize(compressed_path)
    os.remove(compressed_path)

    return size


def save_merged_pcf(pcf: PCFFile, output_path: Path) -> bool:
    try:
        # save uncompressed version
        pcf.encode(output_path)
        uncompressed_size = os.path.getsize(output_path)
        print(f"\nSaved uncompressed file ({uncompressed_size:,} bytes): {output_path}")

        return True

    except Exception as e:
        print(f"Error saving merged PCF: {str(e)}")

        return False


def should_exclude_file(filename: str, excluded_patterns: List[str]) -> bool:
    return any(pattern in filename.lower() for pattern in excluded_patterns)


class ParticleMerger:
    def __init__(self, file_handler: FileHandler, vpk_handler: VPKHandler, progress_callback=None):
        self.file_handler = file_handler
        self.vpk_handler = vpk_handler
        self.progress_callback = progress_callback

        # excluded patterns for special handling
        self.excluded_patterns = ['dx80', 'dx90', 'default', 'unusual', 'test', '_high', '_slow',
                                  'smoke_blackbillow', "level_fx", "_dev"]

        print("\nInitializing ParticleMerger...")
        print(f"Mod folder: {folder_setup.mods_dir}")
        # create_dx8_copies(file_handler, folder_setup.mods_particle_dir)

        # process mod files
        self.mod_files = []
        self.excluded_mod_files = []

        # collect and categorize mod files
        for f in folder_setup.mods_particle_dir.glob('*.pcf'):
            if 'particles/' not in f.name:
                normalized_path = f'particles/{f.name}'
            else:
                normalized_path = f.name

            if should_exclude_file(normalized_path, self.excluded_patterns):
                self.excluded_mod_files.append(normalized_path)
            else:
                self.mod_files.append(normalized_path)

        print(f"Found {len(self.mod_files)} mod PCF files for merging")
        print(f"Found {len(self.excluded_mod_files)} excluded mod PCF files for direct compression")

        # process game files
        game_file_tuples = []
        for file in file_handler.list_pcf_files():
            if should_exclude_file(file, self.excluded_patterns):
                continue

            entry_info = vpk_handler.get_file_entry(file)
            if not entry_info:
                continue

            _, _, entry = entry_info
            game_file_tuples.append((entry.archive_index, file))

        # sort by archive index first, then by filepath
        game_file_tuples.sort(key=lambda x: (x[0], x[1]))
        self.game_files = [file for _, file in game_file_tuples]
        print(f"Found {len(self.game_files)} game PCF files")

        self.total_files = len(self.game_files) + len(self.mod_files) + len(self.excluded_mod_files)
        self.processed_files = 0

        # update initial progress
        if self.progress_callback:
            self.progress_callback(0, f"Found {self.total_files} files to process")

        # track overlapping files
        self.overlapping_files = []
        self.missing_game_files = []

        for game_file in self.game_files:
            if game_file in self.mod_files:
                self.overlapping_files.append(game_file)
            else:
                self.missing_game_files.append(game_file)

        print(f"Found {len(self.overlapping_files)} overlapping files")
        print(f"After removing overlapping files, {len(self.missing_game_files)} game files remain")

        self.ignore_list: Set[str] = set()
        self.merged_files: Dict[str, List[str]] = {}

    def process_excluded_files(self):
        print("\nMoving special mod files to output...")
        for file_path in self.excluded_mod_files:
            base_name = Path(file_path).name
            self.update_progress(f"Moving special file {base_name}")

            source_path = folder_setup.mods_particle_dir / base_name
            output_path = folder_setup.output_dir / base_name

            try:
                shutil.copy2(source_path, output_path)
                print(f"Moved special file: {base_name}")
                self.processed_files += 1
            except Exception as e:
                print(f"Error moving special file {base_name}: {e}")

    def update_progress(self, message=""):
        if self.progress_callback:
            progress = (self.processed_files / self.total_files) * 100
            self.progress_callback(progress, message)

    def get_sorted_game_files(self):
        file_order = []
        for file in self.game_files:
            entry_info = self.vpk_handler.get_file_entry(file)
            if entry_info:
                _, _, entry = entry_info
                file_order.append((file, entry.archive_index, entry.entry_length))

        return sorted(file_order, key=lambda x: x[1])

    def merge_particles(self):
        print("\nStarting particle merge process...")

        # process excluded files first
        self.process_excluded_files()

        # game files first, then mod files
        files_to_process = []

        # extract game files to temporary location
        print("\nExtracting game files for processing...")
        for game_file in self.missing_game_files:
            game_file_name = Path(game_file).name
            if self.file_handler.vpk.extract_file(game_file, str(folder_setup.get_game_files_path(game_file_name))):
                files_to_process.append(game_file)
                self.processed_files += 1
                self.update_progress(f"Extracted {game_file_name}")
            else:
                print(f"Failed to extract {game_file}")

        # add non-excluded mod files
        files_to_process.extend(self.mod_files)
        print(f"\nTotal files to process for merging: {len(files_to_process)}")

        output_number = 0
        current_idx = 0

        while current_idx < len(files_to_process):
            current_output = Path(self.get_sorted_game_files()[output_number][0]).name
            current_output_max_size = self.get_sorted_game_files()[output_number][2]

            successful_merges = []
            file_name = files_to_process[current_idx]
            base_name = Path(file_name).name
            self.update_progress(f"Processing {base_name}")

            if file_name in self.mod_files:
                source_path = folder_setup.mods_particle_dir / base_name
            else:
                source_path = folder_setup.game_files_dir / base_name

            potential_size = check_compressed_size(PCFFile(source_path).decode())
            if potential_size > current_output_max_size:
                output_number += 1
                continue

            successful_merges.append(source_path)
            current_pcf = PCFFile(source_path).decode()
            next_idx = current_idx + 1

            while next_idx < len(files_to_process):
                file_name = files_to_process[next_idx]
                base_name = Path(file_name).name
                if file_name in self.mod_files:
                    source_path = folder_setup.mods_particle_dir / base_name
                else:
                    source_path = folder_setup.game_files_dir / base_name

                print(f"Processing file {next_idx + 1}/{len(files_to_process)}")
                next_pcf = PCFFile(source_path).decode()

                try:
                    merged_pcf = merge_pcf_files(current_pcf, next_pcf)
                    potential_size = check_compressed_size(merged_pcf)

                    if potential_size <= current_output_max_size:
                        current_pcf = merged_pcf
                        successful_merges.append(source_path)
                        next_idx += 1
                        self.processed_files += 1
                        self.update_progress(f"Processed {base_name}")
                    else:
                        break
                except Exception as e:
                    print(f"Error merging file {file_name}: {e}")
                    break

            if len(successful_merges) > 0:
                output_path = folder_setup.output_dir / current_output
                out_merge = PCFFile(successful_merges[0]).decode()
                for merge in successful_merges[1:]:
                    out_merge = merge_pcf_files(out_merge, PCFFile(merge).decode())
                out_merge.encode(output_path)
                current_idx += len(successful_merges)
                output_number += 1

        return self.merged_files

    def process(self):
        print("\n=== Starting Particle File Processing ===")
        print("----------------------------------------")
        self.merge_particles()

        print("\n=== Merge Process Complete ===")


import os
import copy
from pathlib import Path
from typing import List, Set, Dict
from models.pcf_file import PCFFile
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.pcf_merge import merge_pcf_files
from operations.pcf_compress import remove_duplicate_elements
from core.folder_setup import folder_setup


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


class ParticleMerger:
    def __init__(self, file_handler: FileHandler, vpk_handler: VPKHandler):
        self.file_handler = file_handler
        self.vpk_handler = vpk_handler

        print("\nInitializing ParticleMerger...")
        print(f"Mod folder: {folder_setup.mods_dir}")

        # get mod files and normalize path for filtering
        self.mod_files = []
        for f in folder_setup.mods_particle_dir.glob('*.pcf'):
            if 'particles/' not in f.name:
                normalized_path = f'particles/{f.name}'
            else:
                normalized_path = f.name
            self.mod_files.append(normalized_path)
        print(f"Found {len(self.mod_files)} mod PCF files")

        # create a list of (archive_index, filepath) tuples for game files
        if 'particles/explosion.pcf' in self.mod_files:
            excluded_patterns = ['dx80', 'dx90', 'default', 'unusual', 'test', '_high']
        else:
            excluded_patterns = ['dx80', 'dx90', 'default', 'unusual', 'test', '_high', 'explosion']

        game_file_tuples = []

        for file in file_handler.list_pcf_files():
            if any(pattern in file.lower() for pattern in excluded_patterns):
                continue

            entry_info = vpk_handler.get_file_entry(file)
            if not entry_info:
                continue

            _, _, entry = entry_info

            game_file_tuples.append((entry.archive_index, file))

        # Sort by archive index first, then by filepath
        game_file_tuples.sort(key=lambda x: (x[0], x[1]))

        # just the filepaths pls
        self.game_files = [file for _, file in game_file_tuples]
        print(f"Found {len(self.game_files)} game PCF files")

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

        # game files first, then mod files
        files_to_process = []

        # extract game files to temporary location
        print("\nExtracting game files for processing...")
        for game_file in self.missing_game_files:
            game_file_name = Path(game_file).name
            if self.file_handler.vpk.extract_file(game_file, str(folder_setup.get_game_files_path(game_file_name))):
                files_to_process.append(game_file)
            else:
                print(f"Failed to extract {game_file}")

        # mod files
        files_to_process.extend(self.mod_files)
        print(f"\nTotal files to process: {len(files_to_process)}")

        output_number = 0
        current_idx = 0

        while current_idx < len(files_to_process):
            print(f"\nStarting new file at index {current_idx}")
            current_output = Path(self.get_sorted_game_files()[output_number][0]).name
            current_output_max_size = self.get_sorted_game_files()[output_number][2]
            print(f"Size limit for file {output_number}: {current_output_max_size:,} bytes")

            # keep track of successfully processed files
            successful_merges = []

            # process first file
            file_name = files_to_process[current_idx]
            base_name = Path(file_name).name
            if file_name in self.mod_files:
                source_path = folder_setup.mods_particle_dir / base_name
            else:
                source_path = folder_setup.game_files_dir / base_name

            # double check if even the first file is too large
            potential_size = check_compressed_size(PCFFile(source_path).decode())
            if potential_size > current_output_max_size:
                print(f"\nWARNING: Single file exceeds size limit ({potential_size:,} > {current_output_max_size:,} bytes)")
                print("Moving to next file...")
                output_number += 1
                continue

            successful_merges.append(source_path)
            current_pcf = PCFFile(source_path).decode()
            next_idx = current_idx + 1

            while next_idx < len(files_to_process):
                # try merging next file
                file_name = files_to_process[next_idx]
                base_name = Path(file_name).name
                if file_name in self.mod_files:
                    source_path = folder_setup.mods_particle_dir / base_name
                else:
                    source_path = folder_setup.game_files_dir / base_name

                print(f"Processing file {next_idx + 1}/{len(files_to_process)}: {source_path}")
                next_pcf = PCFFile(source_path).decode()

                # try merging with current PCF
                try:
                    merged_pcf = merge_pcf_files(current_pcf, next_pcf)
                    potential_size = check_compressed_size(merged_pcf)

                    if potential_size <= current_output_max_size:
                        # merge was successful, update state
                        current_pcf = merged_pcf
                        successful_merges.append(source_path)
                        next_idx += 1
                    else:
                        print(f"\nFile would exceed size limit ({potential_size:,} > {current_output_max_size:,} bytes)")
                        break
                except Exception as e:
                    print(f"Error merging file {file_name}: {e}")
                    break

            # save the last successful merge state
            if len(successful_merges) > 0:
                output_path = folder_setup.output_dir / current_output
                out_merge = PCFFile(successful_merges[0]).decode()
                for merge in successful_merges[1:]:
                    out_merge = merge_pcf_files(out_merge, PCFFile(merge).decode())
                out_merge.encode(output_path)
                current_idx += len(successful_merges)
                output_number += 1

        return self.merged_files

    def process(self) -> Dict[str, List[str]]:
        print("\n=== Starting Particle File Processing ===")
        print("----------------------------------------")

        merged_results = self.merge_particles()

        print("\n=== Merge Process Complete ===")

        return merged_results

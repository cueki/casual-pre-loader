import os
from pathlib import Path
from typing import List, Set, Dict
from models.pcf_file import PCFFile
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.pcf_merge import merge_pcf_files
from operations.pcf_compress import remove_duplicate_elements
import copy


def check_compressed_size(pcf: PCFFile):
    compressed_path = Path("temp_size_check.pcf")

    test_pcf = copy.deepcopy(pcf)
    compressed = remove_duplicate_elements(test_pcf)

    compressed.encode(compressed_path)
    size = os.path.getsize(compressed_path)

    os.remove(compressed_path)

    return size


def save_merged_pcf(pcf: PCFFile, output_path: Path) -> bool:
    try:
        # create output directory if it doesn't exist
        output_path.parent.mkdir(exist_ok=True)

        # save uncompressed version
        pcf.encode(output_path)
        uncompressed_size = os.path.getsize(output_path)
        print(f"\nSaved uncompressed file ({uncompressed_size:,} bytes): {output_path}")

        return True

    except Exception as e:
        print(f"Error saving merged PCF: {str(e)}")
        return False


class ParticleMerger:
    def __init__(self, file_handler: FileHandler, vpk_handler: VPKHandler, mod_folder: str):
        self.file_handler = file_handler
        self.vpk_handler = vpk_handler
        self.mod_folder = Path(mod_folder)
        self.BATCH_SIZE = 1

        print("\nInitializing ParticleMerger...")
        print(f"Mod folder: {self.mod_folder}")

        # Get all game files first
        excluded_patterns = ['dx80', 'dx90', 'default', 'unusual', 'test', '_high']
        self.game_files = set(
            file for file in file_handler.list_pcf_files()
            if not any(pattern in file.lower() for pattern in excluded_patterns)
        )
        print(f"Found {len(self.game_files)} game PCF files")

        # Get mod files and normalize their paths
        self.mod_files = set()
        for f in self.mod_folder.glob('*.pcf'):
            if 'particles/' not in f.name:
                normalized_path = f'particles/{f.name}'
            else:
                normalized_path = f.name
            self.mod_files.add(normalized_path)
        print(f"Found {len(self.mod_files)} mod PCF files")

        # Store overlapping files separately
        self.overlapping_files = self.mod_files.intersection(self.game_files)
        # Remove overlapping files from game files
        self.game_files = self.game_files - self.overlapping_files
        print(f"Found {len(self.overlapping_files)} overlapping files")
        print(f"After removing overlapping files, {len(self.game_files)} game files remain")

        self.ignore_list: Set[str] = set()
        self.merged_files: Dict[str, List[str]] = {}

    def get_sorted_game_files(self):
        file_sizes = []
        for file in self.game_files.union(self.overlapping_files):
            entry_info = self.vpk_handler.get_file_entry(file)
            if entry_info:
                _, _, entry = entry_info
                file_sizes.append((file, entry.entry_length))

        return sorted(file_sizes, key=lambda x: x[1], reverse=True)

    def get_size_limit(self, batch_number: int) -> int:
        if batch_number >= len(self.get_sorted_game_files()):
            return 0

        return self.get_sorted_game_files()[batch_number][1]

    def get_file_size(self, file_info) -> int:
        try:
            if isinstance(file_info, tuple):
                # for game files
                return os.path.getsize(file_info[1])
            else:
                # for mod files
                base_name = Path(file_info).name
                mod_path = self.mod_folder / base_name
                return os.path.getsize(mod_path)
        except (OSError, IOError) as e:
            print(f"Error getting file size for {file_info}: {e}")
            return 0

    def process_file_batch(self, files_to_process: List[any], start_idx: int):
        processed_files = []
        # this is to ensure that the final batch gets returned if number of files is not divisible by the batch size
        end_idx = min(start_idx + self.BATCH_SIZE, len(files_to_process))
        current_pcf = None

        try:
            for idx in range(start_idx, end_idx):
                file_info = files_to_process[idx]
                # we store the temp game files as tuples
                if isinstance(file_info, tuple):
                    game_file, temp_path = file_info
                    source_path = temp_path
                    file_name = game_file
                # these are the mod files
                else:
                    file_name = file_info
                    base_name = Path(file_name).name
                    source_path = self.mod_folder / base_name

                print(f"Processing file {idx + 1}/{len(files_to_process)}: {file_name}")
                source_pcf = PCFFile(source_path).decode()

                # merge all the files in the batch
                if current_pcf is None:
                    current_pcf = source_pcf
                else:
                    current_pcf = merge_pcf_files(current_pcf, source_pcf)

                # keep track of what we have done
                processed_files.append(file_name)

            return current_pcf, processed_files, end_idx

        except Exception as e:
            print(f"Error processing batch: {e}")
            raise

    def merge_particles(self):
        print("\nStarting particle merge process...")

        # prepare files to process
        files_to_process = list(self.mod_files)

        # extract game files to temporary location
        temp_game_files = []
        temp_dir = Path("temp_game_files")
        temp_dir.mkdir(exist_ok=True)

        print("\nExtracting game files for processing...")
        for game_file in self.game_files:
            temp_path = temp_dir / Path(game_file).name
            if self.file_handler.vpk.extract_file(game_file, str(temp_path)):
                temp_game_files.append((game_file, temp_path))
            else:
                print(f"Failed to extract {game_file}")

        # this is the list of all the files
        files_to_process.extend(temp_game_files)
        print(f"\nTotal files to process: {len(files_to_process)}")
        files_to_process.sort(key=self.get_file_size, reverse=True)
        output_number = 1
        current_idx = 0

        while current_idx < len(files_to_process):
            print(f"\nStarting new file at index {current_idx}")
            # this is a really stupid way to get the name of the file we hope to replace lol
            current_output = Path(self.get_sorted_game_files()[output_number - 1][0]).name
            max_size = self.get_size_limit(output_number - 1)
            print(f"Size limit for file {output_number}: {max_size:,} bytes")

            # keep track of successfully processed files
            successful_merges = []

            # start with first file
            current_pcf, first_batch, next_idx = self.process_file_batch(files_to_process, current_idx)

            # double check if even the first file is too large (should probably kill the process)
            potential_size = check_compressed_size(current_pcf)
            if potential_size > max_size:
                print(f"\nWARNING: Single file exceeds size limit ({potential_size:,} > {max_size:,} bytes)")
                print("Moving to next file...")
                current_idx = next_idx
                continue

            successful_merges.extend(first_batch)

            while next_idx < len(files_to_process):
                # try merging next batch
                test_pcf, test_batch, test_idx = self.process_file_batch(files_to_process, next_idx)

                # try merging with current batch
                merged_pcf = merge_pcf_files(current_pcf, test_pcf)
                potential_size = check_compressed_size(merged_pcf)

                if potential_size <= max_size:
                    # merge was successful, update state
                    current_pcf = merged_pcf
                    successful_merges.extend(test_batch)
                    next_idx = test_idx
                else:
                    print(f"\nBatch would exceed size limit ({potential_size:,} > {max_size:,} bytes)")
                    print("Rolling back and rebuilding from successful merges...")

                    # rebuild PCF from successful merges
                    rebuilt_pcf = None
                    for i in range(0, len(successful_merges)):
                        file_info = files_to_process[current_idx + i]

                        # handle both mod files and game files
                        if isinstance(file_info, tuple):
                            game_file, temp_path = file_info
                            source_path = temp_path
                        else:
                            base_name = Path(file_info).name
                            source_path = self.mod_folder / base_name

                        source_pcf = PCFFile(source_path).decode()

                        if rebuilt_pcf is None:
                            rebuilt_pcf = source_pcf
                        else:
                            rebuilt_pcf = merge_pcf_files(rebuilt_pcf, source_pcf)

                    current_pcf = rebuilt_pcf
                    break

            # save the current file
            output_path = Path(f"output/{current_output}")
            if save_merged_pcf(current_pcf, output_path):
                print(f"\nSaved file {output_number}")
                current_idx += len(successful_merges)
                output_number += 1
            else:
                print(f"Failed to save batch {output_number}, skipping...")
                current_idx = next_idx

        # clean up temporary files
        for _, temp_path in temp_game_files:
            os.remove(temp_path)

        if temp_dir.exists():
            temp_dir.rmdir()

        return self.merged_files

    def process(self) -> Dict[str, List[str]]:
        print("\n=== Starting Particle File Processing ===")
        print("----------------------------------------")

        merged_results = self.merge_particles()

        print("\n=== Merge Process Complete ===")

        return merged_results

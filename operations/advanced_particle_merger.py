from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from valve_parsers import PCFFile
from operations.pcf_rebuild import (load_particle_system_map, get_pcf_element_names, extract_elements,
                                    rebuild_particle_files)
from operations.pcf_merge import merge_pcf_files
from core.folder_setup import folder_setup
from core.constants import PARTICLE_SPLITS


def sequential_merge(pcf_files: List[PCFFile]):
    if not pcf_files:
        return None
    result = pcf_files[0]
    for pcf in pcf_files[1:]:
        try:
            result = merge_pcf_files(result, pcf)
        except ValueError as e:
            print(f"Warning: Skipping PCF file due to merge error: {e}")
            continue
    return result


def default_max_size_for_mod_merge(pcf_files: List[Path]) -> int:
    # this is just for simplicity’s sake, might change this later
    file_sizes = [(i, Path(file).stat().st_size) for i, file in enumerate(pcf_files)]
    return max(file_sizes, key=lambda x: x[1])[0]


def find_duplicate_elements(pcf_files: List[PCFFile]) -> Dict[str, List[int]]:
    element_sources = defaultdict(list)
    for i, pcf in enumerate(pcf_files):
        for element_name in get_pcf_element_names(pcf):
            element_sources[element_name].append(i)
    return {elem: sources for elem, sources in element_sources.items() if len(sources) > 1}


def save_split_files(merged_pcf: PCFFile, out_dir: Path, split_filters: dict) -> None:
    mod_elements = get_pcf_element_names(merged_pcf)
    split_elements = {}  # {split_name: set(elements)}
    unmatched_elements = set(mod_elements)

    # apply filter to elements
    for split_name, filter_func in split_filters.items():
        if filter_func == "**EVERYTHING_ELSE**":
            if unmatched_elements:
                split_elements[split_name] = unmatched_elements
        else:
            matched = {elem for elem in mod_elements if filter_func(elem)}
            if matched:
                split_elements[split_name] = matched
                unmatched_elements -= matched

    # save splits to actual_particles/
    for split_name, elements in split_elements.items():
        split_pcf = extract_elements(merged_pcf, elements)
        output_path = out_dir / "actual_particles" / split_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        split_pcf.encode(output_path)


class AdvancedParticleMerger:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.particle_map = load_particle_system_map(folder_setup.install_dir / "particle_system_map.json")
        self.vpk_groups = defaultdict(lambda: defaultdict(list))  # {vpk_name: {particle_file: [paths]}}

    def update_progress(self, progress, message: str):
        if self.progress_callback:
            self.progress_callback(progress, message)

    def preprocess_vpk(self, vpk_path: Path) -> None:
        vpk_folder_name = vpk_path.stem
        out_dir = folder_setup.particles_dir / vpk_folder_name

        # lazy copy whatever
        excluded_patterns = ['dx80', 'dx90']
        particles_filter = [f for f in Path(out_dir / "particles").glob("*.pcf")
                            if not any(pattern in str(f).lower() for pattern in excluded_patterns)]

        # group files by their target particle file
        for particle in particles_filter:
            for particle_file_target, elements_to_extract, source_pcf in (
                    rebuild_particle_files(particle, self.particle_map)):
                output_path = folder_setup.get_output_path(
                    f"{len(self.vpk_groups[vpk_folder_name][particle_file_target])}_{particle_file_target}")
                extract_elements(source_pcf, elements_to_extract).encode(output_path)
                self.vpk_groups[vpk_folder_name][particle_file_target].append(output_path)

        self.process_vpk_group(vpk_folder_name, out_dir)

    def process_vpk_group(self, vpk_name: str, out_dir: Path) -> None:
        splits_config = PARTICLE_SPLITS

        for particle_group, group_files in self.vpk_groups[vpk_name].items():
            pcf_files = [PCFFile(particle).decode() for particle in group_files]
            duplicates = find_duplicate_elements(pcf_files)

            if duplicates:
                choice = default_max_size_for_mod_merge(group_files)
                chosen_pcf = pcf_files[choice]
                elements_we_have = get_pcf_element_names(chosen_pcf)
            else:
                result = sequential_merge(pcf_files)
                elements_we_have = get_pcf_element_names(result)

            elements_we_still_need = set()
            for element in self.particle_map[f'particles/{particle_group}']:
                if element not in elements_we_have:
                    elements_we_still_need.add(element)

            if elements_we_still_need:
                game_file_path = folder_setup.temp_to_be_referenced_dir / particle_group
                game_file_in = PCFFile(game_file_path).decode()
                game_elements = extract_elements(game_file_in, elements_we_still_need)

                if duplicates:
                    try:
                        result = merge_pcf_files(chosen_pcf, game_elements)
                    except ValueError as e:
                        print(f"Warning: Failed to merge with game elements: {e}")
                        result = chosen_pcf
                else:
                    pcf_files.append(game_elements)
                    result = sequential_merge(pcf_files)
            else:
                result = chosen_pcf if duplicates else result

            if particle_group in splits_config:
                save_split_files(result, out_dir, splits_config[particle_group])
            else:
                actual_particles = Path(out_dir / "actual_particles" / particle_group)
                actual_particles.parent.mkdir(parents=True, exist_ok=True)
                result.encode(actual_particles)

        for file in folder_setup.temp_to_be_processed_dir.iterdir():
            file.unlink()

from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from parsers.pcf_file import PCFFile
from operations.pcf_rebuild import (
    load_particle_system_map,
    get_pcf_element_names,
    extract_elements,
    rebuild_particle_files
)
from operations.pcf_merge import merge_pcf_files
from core.folder_setup import folder_setup


def sequential_merge(pcf_files: List[PCFFile]):
    if not pcf_files:
        return None
    result = pcf_files[0]
    for pcf in pcf_files[1:]:
        result = merge_pcf_files(result, pcf)
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


class AdvancedParticleMerger:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.particle_map = load_particle_system_map(folder_setup.project_dir / "particle_system_map.json")
        self.vpk_groups = defaultdict(lambda: defaultdict(list))  # {vpk_name: {particle_file: [paths]}}

    def update_progress(self, progress: float, message: str):
        if self.progress_callback:
            self.progress_callback(progress, message)

    def preprocess_vpk(self, vpk_path: Path) -> None:
        vpk_folder_name = vpk_path.stem
        out_dir = folder_setup.user_mods_dir / vpk_folder_name

        # group files by their target particle file
        for particle in Path(out_dir /"particles").iterdir():
            print(particle)
            for particle_file_target, elements_to_extract, source_pcf in (
                    rebuild_particle_files(particle, self.particle_map)):
                output_path = folder_setup.get_output_path(
                    f"{len(self.vpk_groups[vpk_folder_name][particle_file_target])}_{particle_file_target}")
                extract_elements(source_pcf, elements_to_extract).encode(output_path)
                self.vpk_groups[vpk_folder_name][particle_file_target].append(output_path)

        self.process_vpk_group(vpk_folder_name, out_dir)

    def process_vpk_group(self, vpk_name: str, out_dir: Path) -> None:
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
                game_file_path = folder_setup.game_files_dir / particle_group
                game_file_in = PCFFile(game_file_path).decode()
                game_file_out = folder_setup.get_output_path(f"game_{particle_group}")
                extract_elements(game_file_in, elements_we_still_need).encode(game_file_out)

                if duplicates:
                    game_elements = PCFFile(game_file_out).decode()
                    result = merge_pcf_files(chosen_pcf, game_elements)
                else:
                    group_files.append(game_file_out)
                    pcf_files = [PCFFile(particle).decode() for particle in group_files]
                    result = sequential_merge(pcf_files)
            else:
                result = chosen_pcf if duplicates else result

            actual_particles = Path(out_dir / "actual_particles" / particle_group)
            actual_particles.parent.mkdir(parents=True, exist_ok=True)
            result.encode(actual_particles)

        for file in folder_setup.output_dir.iterdir():
            file.unlink()

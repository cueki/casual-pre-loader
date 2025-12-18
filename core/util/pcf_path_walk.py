import logging
from pathlib import Path

from valve_parsers import PCFFile

from core.constants import PARTICLE_SPLITS
from core.folder_setup import folder_setup
from core.operations.pcf_merge import merge_pcf_files
from core.operations.pcf_rebuild import (
    extract_elements,
    get_pcf_element_names,
    load_particle_system_map,
)
from core.util.file import copy

log = logging.getLogger()


def get_vmt_dependencies(vmt_path: Path) -> list[Path] | None:
    try:
        with open(vmt_path, 'r', encoding='utf-8') as f:
            lines = []
            for line in f:
                # skip commented lines
                if not line.strip().startswith('//'):
                    lines.append(line.lower())

            # join non-commented lines
            content = ''.join(lines)

        # this texture_paths_list should contain all the possible vtf files from a vmt that are mapped to these texture_params
        # this may need to be updated in the future to handle more possible paths
        texture_params = ['$basetexture', '$detail', '$ramptexture', '$normalmap', '$normalmap2']
        texture_paths_list = []

        # simple parsing for texture path
        for texture_param in texture_params:
            start_pos = 0

            while True:
                if texture_param in content:
                    # find the texture_params
                    pos = content.find(texture_param, start_pos)
                    if pos == -1:  # no more occurrences
                        break

                    param_end = pos + len(texture_param)
                    if param_end < len(content):
                        # check if the parameter is followed by whitespace or quote
                        if not (content[param_end].isspace() or content[param_end] in ['"', "'"]):
                            start_pos = pos + 1
                            continue

                    # find the end of the line
                    line_end = content.find('\n', pos)
                    comment_pos = content.find('//', pos)

                    # if there's a comment before the end of line, use that as the line end
                    if comment_pos != -1 and (comment_pos < line_end or line_end == -1):
                        line_end = comment_pos

                    # just in case no newline at end of file
                    if line_end == -1:
                        line_end = len(content)

                    # spec ops: the line
                    line = content[pos:line_end]

                    # check if the line ends with a quote
                    if line.rstrip().endswith('"') or line.rstrip().endswith("'"):
                        # if it does, find the matching opening quote
                        quote_char = line.rstrip()[-1]
                        value_end = line.rstrip().rfind(quote_char)
                        value_start = line.rfind(quote_char, 0, value_end - 1)
                        if value_start != -1:
                            texture_path = line[value_start + 1:value_end].strip()
                            # check if path already has an extension
                            if texture_path.endswith('.vtf'):
                                texture_paths_list.append(Path(texture_path))
                                texture_paths_list.append(Path(texture_path[:-4] + '.vmt'))
                            elif texture_path.endswith('.vmt'):
                                texture_paths_list.append(Path(texture_path[:-4] + '.vtf'))
                                texture_paths_list.append(Path(texture_path))
                            else:
                                texture_paths_list.append(Path(texture_path + '.vtf'))
                                texture_paths_list.append(Path(texture_path + '.vmt'))
                    else:
                        # look for tab or space after the parameter
                        param_end = pos + len(texture_param)
                        # skip initial whitespace after parameter name
                        while param_end < len(line) and line[param_end].isspace():
                            param_end += 1
                        # find the value - everything after whitespace until end of line
                        value_start = param_end
                        texture_path = line[value_start:].strip()
                        # check if path already has an extension
                        if texture_path.endswith('.vtf'):
                            texture_paths_list.append(Path(texture_path))
                            texture_paths_list.append(Path(texture_path[:-4] + '.vmt'))
                        elif texture_path.endswith('.vmt'):
                            texture_paths_list.append(Path(texture_path[:-4] + '.vtf'))
                            texture_paths_list.append(Path(texture_path))
                        else:
                            texture_paths_list.append(Path(texture_path + '.vtf'))
                            texture_paths_list.append(Path(texture_path + '.vmt'))

                    start_pos = line_end
                else:
                    break

        return texture_paths_list

    except Exception:
        log.exception(f"Error parsing VMT file {vmt_path}")
        return None


def get_mod_particles() -> tuple[dict[str, list[str]], list[str]]:
    # returns a tuple of (mod_particles dict, sorted list of all particle names)
    mod_particles = {}
    all_particles = set()

    if not folder_setup.particles_dir.exists():
        return mod_particles, []

    for vpk_dir in folder_setup.particles_dir.iterdir():
        if vpk_dir.is_dir():
            particle_dir = vpk_dir / "actual_particles"
            if particle_dir.exists():
                particles = [pcf.stem for pcf in particle_dir.glob("*.pcf")]
                mod_particles[vpk_dir.name] = particles
                all_particles.update(particles)

    return mod_particles, sorted(list(all_particles))


def apply_particle_selections(selections: dict) -> bool:
    # particle mod installer
    required_materials = set()

    # process each mod that has selected particles
    used_mods = set(selections.values())
    for mod_name in used_mods:
        mod_dir = folder_setup.particles_dir / mod_name

        # copy selected particles
        source_particles_dir = mod_dir / "actual_particles"
        if source_particles_dir.exists():
            for particle_file, selected_mod in selections.items():
                if selected_mod == mod_name:
                    source_file = source_particles_dir / f"{particle_file}.pcf"
                    if source_file.exists():
                        # copy particle file to to_be_patched
                        copy(source_file, folder_setup.temp_to_be_patched_dir / f"{particle_file}.pcf")
                        # get particle file mats from attrib
                        pcf = PCFFile(source_file).decode()
                        system_defs = pcf.get_elements_by_type('DmeParticleSystemDefinition')
                        for element in system_defs:
                            material_value = pcf.get_attribute_value(element, 'material')
                            if material_value and isinstance(material_value, bytes):
                                material_path = material_value.decode('ascii')
                                # ignore vgui/white
                                if material_path == 'vgui/white':
                                    continue
                                if material_path.endswith('.vmt'):
                                    required_materials.add(material_path)
                                else:
                                    required_materials.add(material_path + ".vmt")

    for mod_name in used_mods:
        mod_dir = folder_setup.particles_dir / mod_name
        # process each required material
        for material_path in required_materials:
            full_material_path = mod_dir / 'materials' / material_path.replace('\\', '/')
            if full_material_path.exists():
                material_destination = folder_setup.temp_to_be_vpk_dir / Path(full_material_path).relative_to(mod_dir)
                copy(full_material_path, material_destination)
                texture_paths = get_vmt_dependencies(full_material_path)
                if texture_paths:
                    for texture_path in texture_paths:
                        full_texture_path = mod_dir / 'materials' / str(texture_path).replace('\\', '/')
                        if full_texture_path.exists():
                            texture_destination = folder_setup.temp_to_be_vpk_dir / Path(full_texture_path).relative_to(mod_dir)
                            copy(full_texture_path, texture_destination)

    # merge split files back into original files
    for original_file, split_defs in PARTICLE_SPLITS.items():
        split_files_in_temp = []

        # check which split files exist in to_be_patched
        for split_name in split_defs.keys():
            split_path = folder_setup.temp_to_be_patched_dir / split_name
            if split_path.exists():
                split_files_in_temp.append(split_path)

        # if we have splits for this original file, merge them
        if split_files_in_temp:
            pcf_parts = [PCFFile(split_file).decode() for split_file in split_files_in_temp]

            if len(pcf_parts) > 1:
                merged = pcf_parts[0]
                for pcf in pcf_parts[1:]:
                    merged = merge_pcf_files(merged, pcf)
            else:
                merged = pcf_parts[0]

            output_path = folder_setup.temp_to_be_patched_dir / original_file
            merged.encode(output_path)

            for split_file in split_files_in_temp:
                split_file.unlink()

    # fill in missing vanilla elements for reconstructed split files
    particle_map = load_particle_system_map(folder_setup.particle_system_map_file)

    for original_file in PARTICLE_SPLITS.keys():
        merged_file = folder_setup.temp_to_be_patched_dir / original_file

        if merged_file.exists():
            merged_pcf = PCFFile(merged_file).decode()
            elements_we_have = get_pcf_element_names(merged_pcf)

            elements_we_still_need = set()
            for element in particle_map[f'particles/{original_file}']:
                if element not in elements_we_have:
                    elements_we_still_need.add(element)

            if elements_we_still_need:
                vanilla_file = folder_setup.temp_to_be_referenced_dir / original_file
                if vanilla_file.exists():
                    vanilla_pcf = PCFFile(vanilla_file).decode()
                    vanilla_elements = extract_elements(vanilla_pcf, elements_we_still_need)
                    complete_pcf = merge_pcf_files(merged_pcf, vanilla_elements)
                    complete_pcf.encode(merged_file)

    return len(selections) > 0

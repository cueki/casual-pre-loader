import logging
from collections import defaultdict
from functools import reduce
from pathlib import Path

from valve_parsers import PCFFile

from core.config import config
from core.constants import PARTICLE_SPLITS, VMT_TEXTURE_PARAMS
from core.operations.mdl_relocate import resolve_ci
from core.operations.pcf_merge import merge_pcf_files
from core.operations.pcf_rebuild import (
    extract_elements,
    get_pcf_element_names,
    load_particle_system_map,
)
from core.util import keyvalues
from core.util.file import copy

log = logging.getLogger()


def _texture_candidates(texture_path: str) -> list[Path]:
    # a param value may or may not carry an extension so return both the vtf and vmt it could mean
    stem = texture_path.replace('\\', '/').strip().lstrip('/')
    if stem.lower().endswith(('.vtf', '.vmt')):
        stem = stem[:-4]
    if not stem:
        return []
    return [Path(stem + '.vtf'), Path(stem + '.vmt')]


def get_vmt_dependencies(vmt_path: Path, materials_root: Path | None = None, _seen: set[Path] | None = None) -> list[Path] | None:
    # collect the texture/material paths (relative to materials/) a VMT references.
    seen = _seen if _seen is not None else set()
    seen.add(vmt_path.resolve())

    try:
        kv = keyvalues.load(vmt_path)
    except Exception:
        log.exception(f"Error parsing VMT file {vmt_path}")
        return None

    deps: list[Path] = []
    for node in keyvalues.walk(kv):
        key = node.key.lower()
        if key in VMT_TEXTURE_PARAMS:
            deps.extend(_texture_candidates(node.value))
        elif key == 'include':
            # patch includes are written from the game root: "materials/models/.../foo.vmt"
            include = node.value.replace('\\', '/').lstrip('/')
            if include.lower().startswith('materials/'):
                include = include[len('materials/'):]
            if not include:
                continue
            deps.append(Path(include))
            if materials_root is not None:
                included = resolve_ci(materials_root, include)
                if included is not None and included.resolve() not in seen:
                    deps.extend(get_vmt_dependencies(included, materials_root, seen) or [])

    return deps


def _pcf_materials(pcf_path: Path) -> set[str]:
    # vmt paths (relative to materials/) used by every particle system in a pcf
    pcf = PCFFile(pcf_path).decode()
    materials = set()
    for element in pcf.get_elements_by_type('DmeParticleSystemDefinition'):
        value = pcf.get_attribute_value(element, 'material')
        if not value or not isinstance(value, bytes):
            continue
        material = value.decode('ascii').replace('\\', '/')
        if material.lower() == 'vgui/white':
            continue
        if not material.lower().endswith('.vmt'):
            material += '.vmt'
        materials.add(material)
    return materials


def _copy_selected_pcfs(selections: dict[str, str]) -> dict[str, list[str]]:
    # copy each picked pcf to to_be_patched and return material -> mods whose picked pcfs use it,
    # in selection order so the first pick wins
    material_users: dict[str, list[str]] = defaultdict(list)
    for particle_file, mod_name in selections.items():
        source = config.particles_dir / mod_name / 'actual_particles' / f'{particle_file}.pcf'
        if not source.exists():
            continue
        copy(source, config.temp_to_be_patched_dir / source.name)
        for material in sorted(_pcf_materials(source)):
            users = material_users[material.lower()]
            if mod_name not in users:
                users.append(mod_name)
    return material_users


def _copy_materials(material_users: dict[str, list[str]]) -> None:
    # a material only comes from a mod whose picked pcf actually uses it. copying it from every selected mod
    # that shipped one let packs with shared texture names (e.g. square/square2.vtf) overwrite each other
    to_copy: dict[str, tuple[Path, Path]] = {}  # lowercased dest -> (source, dest relative to the mod dir)
    for material, mods in material_users.items():
        for mod_name in mods:
            mod_dir = config.particles_dir / mod_name
            materials_root = mod_dir / 'materials'
            # pcf and vmt references don't always match the on-disk case, resolve like the engine does on windows
            vmt = resolve_ci(materials_root, material)
            if vmt is None:
                # this mod relies on the vanilla material, a later mod might ship it
                continue

            deps = (resolve_ci(materials_root, str(dep)) for dep in get_vmt_dependencies(vmt, materials_root) or [])
            for source in (vmt, *(dep for dep in deps if dep is not None)):
                rel = source.relative_to(mod_dir)
                to_copy.setdefault(str(rel).lower(), (source, rel))
            break

    for source, rel in to_copy.values():
        copy(source, config.temp_to_be_vpk_dir / rel)


def _merge_split_pcfs() -> None:
    # stitch split files (e.g. item_fx_unusuals + item_fx_gameplay) back into the pcf the game loads
    for original_file, split_defs in PARTICLE_SPLITS.items():
        split_paths = [path for name in split_defs if (path := config.temp_to_be_patched_dir / name).exists()]
        if not split_paths:
            continue

        merged = reduce(merge_pcf_files, (PCFFile(path).decode() for path in split_paths))
        merged.encode(config.temp_to_be_patched_dir / original_file)
        for path in split_paths:
            path.unlink()


def _fill_missing_vanilla_elements() -> None:
    # a merged split file only has the systems the user picked, copy the rest back from vanilla
    particle_map = load_particle_system_map(config.particle_system_map_file)
    for original_file in PARTICLE_SPLITS:
        merged_file = config.temp_to_be_patched_dir / original_file
        vanilla_file = config.temp_to_be_referenced_dir / original_file
        if not merged_file.exists() or not vanilla_file.exists():
            continue

        merged = PCFFile(merged_file).decode()
        missing = set(particle_map[f'particles/{original_file}']) - set(get_pcf_element_names(merged))
        if missing:
            vanilla_elements = extract_elements(PCFFile(vanilla_file).decode(), missing)
            merge_pcf_files(merged, vanilla_elements).encode(merged_file)


def apply_particle_selections(selections: dict[str, str]) -> bool:
    # selections maps pcf name -> the mod it's taken from
    material_users = _copy_selected_pcfs(selections)
    _copy_materials(material_users)
    _merge_split_pcfs()
    _fill_missing_vanilla_elements()
    return len(selections) > 0

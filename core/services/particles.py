import logging

from core.constants import PARTICLE_GROUP_MAPPING

log = logging.getLogger()


def expand_group_selections(
    selections: dict[str, str],
    mod_particles_cache: dict[str, list],
    simple_mode: bool
) -> dict[str, str]:
    """
    Expand particle group selections to individual particles.
    In simple mode, converts group names to individual particle files.
    In advanced mode, returns selections as-is.

    Args:
        selections: Dict mapping particle/group name to mod name
        mod_particles_cache: Dict mapping mod name to list of particles it contains
        simple_mode: Whether we're in simple (grouped) mode

    Returns:
        Dict mapping individual particle names to mod names
    """

    if not simple_mode:
        return selections

    expanded = {}
    for column_name, mod_name in selections.items():
        # if this is a group name, expand it to individual particles
        if column_name in PARTICLE_GROUP_MAPPING:
            for particle_file in PARTICLE_GROUP_MAPPING[column_name]:
                particle_name = particle_file.replace('.pcf', '')
                # only include if the mod actually has this particle
                if particle_name in mod_particles_cache.get(mod_name, []):
                    expanded[particle_name] = mod_name
        else:
            # already an individual particle
            expanded[column_name] = mod_name

    return expanded


def calculate_particle_availability(
    mod: str,
    column_name: str,
    simple_mode: bool,
    mod_particles: set[str],
    saved_selections: dict[str, str]
) -> tuple[bool, bool]:
    """
    Calculate whether a particle/group checkbox should be enabled and checked.

    Args:
        mod: The mod name
        column_name: The particle or group name
        simple_mode: Whether we're in simple (grouped) mode
        mod_particles: Set of particles this mod contains (without .pcf extension)
        saved_selections: Previously saved selections dict

    Returns:
        Tuple of (should_enable, should_check)
    """

    if simple_mode and column_name in PARTICLE_GROUP_MAPPING:
        # in simple mode with a group, check if mod has ANY particle from the group
        group_particles = PARTICLE_GROUP_MAPPING[column_name]
        should_enable = any(
            p.replace('.pcf', '') in mod_particles
            for p in group_particles
        )
        should_check = should_enable and any(
            saved_selections.get(p.replace('.pcf', '')) == mod
            for p in group_particles
        )
    else:
        # advanced mode or individual particle
        should_enable = column_name in mod_particles
        should_check = (
            should_enable and
            column_name in saved_selections and
            saved_selections[column_name] == mod
        )

    return should_enable, should_check

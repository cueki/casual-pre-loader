from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from core.constants import Sourcemods
from core.util.sourcemod import get_sourcemod


@dataclass
class Profile:
    name: str
    game_path: Path
    sourcemod: Sourcemods = Sourcemods.DEFAULT
    id: UUID = field(default_factory=uuid4)
    addon_selections: list[str] = field(default_factory=list)
    matrix_selections: dict = field(default_factory=dict)
    matrix_selections_simple: dict = field(default_factory=dict)
    simple_particle_mode: bool = True
    show_console_on_startup: bool = True
    disable_paint_colors: bool = False
    fix_mdl_paths: bool = True
    skip_quickprecache: bool = False

    @classmethod
    def from_dict(cls, profile: Mapping[str, Any]) -> 'Profile':
        profile = dict(profile)

        if 'id' in profile and not isinstance(profile['id'], UUID):
            profile['id'] = UUID(profile['id'])

        if 'game_path' in profile: # deserialize Path objects
            profile['game_path'] = Path(profile['game_path'])

        # profiles now specify which sourcemod they are relevant to (technically a migration)
        profile['sourcemod'] = get_sourcemod(profile.pop('game_target', profile.get('sourcemod')))

        return cls(**profile)

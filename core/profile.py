import uuid
from dataclasses import dataclass, field


@dataclass
class Profile:
    id: str
    name: str
    game_path: str
    game_target: str = "Team Fortress 2"
    addon_selections: list[str] = field(default_factory=list)
    matrix_selections: dict = field(default_factory=dict)
    matrix_selections_simple: dict = field(default_factory=dict)
    simple_particle_mode: bool = True
    show_console_on_startup: bool = True
    disable_paint_colors: bool = False
    fix_mdl_paths: bool = True
    skip_quickprecache: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "game_path": self.game_path,
            "game_target": self.game_target,
            "addon_selections": self.addon_selections,
            "matrix_selections": self.matrix_selections,
            "matrix_selections_simple": self.matrix_selections_simple,
            "simple_particle_mode": self.simple_particle_mode,
            "show_console_on_startup": self.show_console_on_startup,
            "disable_paint_colors": self.disable_paint_colors,
            "fix_mdl_paths": self.fix_mdl_paths,
            "skip_quickprecache": self.skip_quickprecache,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "TF2"),
            game_path=data.get("game_path", ""),
            game_target=data.get("game_target", "Team Fortress 2"),
            addon_selections=data.get("addon_selections", []),
            matrix_selections=data.get("matrix_selections", {}),
            matrix_selections_simple=data.get("matrix_selections_simple", {}),
            simple_particle_mode=data.get("simple_particle_mode", True),
            show_console_on_startup=data.get("show_console_on_startup", True),
            disable_paint_colors=data.get("disable_paint_colors", False),
            fix_mdl_paths=data.get("fix_mdl_paths", True),
            skip_quickprecache=data.get("skip_quickprecache", False),
        )

    @classmethod
    def create(cls, name: str, game_path: str, game_target: str = "Team Fortress 2") -> "Profile":
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            game_path=game_path,
            game_target=game_target,
        )

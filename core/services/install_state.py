import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Callable

from core.constants import BACKUP_MAINMENU_FOLDER, CUSTOM_VPK_NAME
from core.folder_setup import folder_setup
from core.util.vpk import get_vpk_name
from core.version import VERSION

log = logging.getLogger()

INSTALL_STATE_SCHEMA = 1
INSTALL_RECIPE_VERSION = 1
CONTENT_HASH_CHUNK_SIZE = 1024 * 1024


def make_request_header(
    selected_addons: list[str],
    particle_selections: dict[str, str],
    *,
    disable_paint_colors: bool,
    show_console_on_startup: bool,
    fix_mdl_paths: bool,
    skip_quickprecache: bool,
    game_target: str,
) -> dict:
    return {
        "recipe": INSTALL_RECIPE_VERSION,
        "app_version": VERSION,
        "game_target": game_target,
        "selected_addons": list(selected_addons),
        "particle_selections": dict(sorted(particle_selections.items())),
        "options": {
            "disable_paint_colors": disable_paint_colors,
            "show_console_on_startup": show_console_on_startup,
            "fix_mdl_paths": fix_mdl_paths,
            "skip_quickprecache": skip_quickprecache,
        },
    }


def _file_entry(path: Path, label: str) -> list:
    try:
        stat = path.stat()
    except OSError:
        return [label, "missing"]
    return [label, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def _content_file_entry(path: Path, label: str) -> list:
    """Capture portable file identity for application-bundled inputs."""
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as file:
            while chunk := file.read(CONTENT_HASH_CHUNK_SIZE):
                digest.update(chunk)
                size += len(chunk)
    except OSError:
        return [label, "missing"]
    return [label, size, digest.hexdigest()]


def _tree_entries(
    root: Path,
    label: str,
    include: Callable[[Path], bool] | None = None,
    file_entry: Callable[[Path, str], list] = _file_entry,
) -> list[list]:
    if not root.is_dir():
        return [[label, "missing"]]

    entries = [[f"{label}/", "directory"]]
    paths = sorted(root.rglob("*"), key=lambda path: path.as_posix().casefold())
    for path in paths:
        if not path.is_file() or (include is not None and not include(path)):
            continue
        relative = path.relative_to(root).as_posix()
        entries.append(file_entry(path, f"{label}/{relative}"))
    return entries


def capture_source_state(
    selected_addons: list[str],
    particle_selections: dict[str, str],
) -> list[list]:
    entries = []
    for index, addon_name in enumerate(selected_addons):
        addon_dir = folder_setup.addons_dir / addon_name
        entries.extend(
            _tree_entries(
                addon_dir,
                f"addons/{index}/{addon_name}",
                lambda path: path.name != "sound.cache",
            )
        )

    for mod_name in sorted(set(particle_selections.values())):
        particle_mod_dir = folder_setup.particles_dir / mod_name
        entries.extend(
            _tree_entries(
                particle_mod_dir,
                f"particles/{mod_name}",
                lambda path: path.name != "sound.cache",
            )
        )
    return entries


def _managed_hud_names(custom_dir: Path) -> set[str]:
    result = set()
    if not custom_dir.is_dir():
        return result

    for item in custom_dir.iterdir():
        mod_json = item / "mod.json"
        if not item.is_dir() or not mod_json.is_file():
            continue
        try:
            with mod_json.open("r", encoding="utf-8") as file:
                metadata = json.load(file)
            if metadata.get("type", "").lower() == "hud" and metadata.get("preloader_installed", False):
                result.add(item.name)
        except (OSError, json.JSONDecodeError):
            continue
    return result


def _is_managed_custom_path(path: Path, custom_dir: Path, managed_huds: set[str]) -> bool:
    relative = path.relative_to(custom_dir)
    top_name = relative.parts[0]
    top_name_lower = top_name.lower()
    preloader_prefix = CUSTOM_VPK_NAME.removesuffix(".vpk").lower()

    return (
        top_name in managed_huds
        or top_name == BACKUP_MAINMENU_FOLDER
        or top_name_lower.startswith(preloader_prefix)
        or top_name_lower in {"_quickprecache.vpk", "quickprecache.vpk"}
    )


def capture_external_custom_state(custom_dir: Path) -> list[list]:
    if not custom_dir.is_dir():
        return [["custom/", "missing"]]

    managed_huds = _managed_hud_names(custom_dir)

    def include(path: Path) -> bool:
        return (
            not path.name.lower().endswith(".sound.cache")
            and not _is_managed_custom_path(path, custom_dir, managed_huds)
        )

    return _tree_entries(custom_dir, "custom", include)


def capture_managed_outputs(tf_path: Path | str) -> list[list]:
    tf_path = Path(tf_path)
    custom_dir = tf_path / "custom"
    entries = [
        _file_entry(tf_path / "gameinfo.txt", "gameinfo.txt"),
        _file_entry(tf_path / get_vpk_name(tf_path), get_vpk_name(tf_path)),
    ]

    if custom_dir.is_dir():
        managed_huds = _managed_hud_names(custom_dir)
        for path in sorted(custom_dir.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if (
                path.is_file()
                and not path.name.lower().endswith(".sound.cache")
                and _is_managed_custom_path(path, custom_dir, managed_huds)
            ):
                entries.append(_file_entry(path, f"custom/{path.relative_to(custom_dir).as_posix()}"))

    models_dir = tf_path / "models"
    if models_dir.is_dir():
        model_paths = list(models_dir.glob("precache.mdl")) + list(models_dir.glob("precache_*.mdl"))
        for path in sorted(set(model_paths), key=lambda item: item.name.casefold()):
            entries.append(_file_entry(path, f"models/{path.name}"))

    return sorted(entries, key=lambda entry: entry[0].casefold())


def capture_precache_outputs(tf_path: Path | str) -> list[list]:
    tf_path = Path(tf_path)
    custom_dir = tf_path / "custom"
    entries = [
        _file_entry(custom_dir / "_QuickPrecache.vpk", "custom/_QuickPrecache.vpk"),
        _file_entry(custom_dir / "QuickPrecache.vpk", "custom/QuickPrecache.vpk"),
    ]

    models_dir = tf_path / "models"
    model_paths = list(models_dir.glob("precache.mdl")) + list(models_dir.glob("precache_*.mdl"))
    for path in sorted(set(model_paths), key=lambda item: item.name.casefold()):
        entries.append(_file_entry(path, f"models/{path.name}"))

    return sorted(entries, key=lambda entry: entry[0].casefold())


def capture_direct_game_inputs(
    selected_addons: list[str],
    particle_selections: dict[str, str],
    disable_paint_colors: bool,
) -> list[list]:
    entries = [
        ["disable_paint_colors", disable_paint_colors],
        ["particle_selections", [list(item) for item in sorted(particle_selections.items())]],
    ]

    for index, addon_name in enumerate(selected_addons):
        addon_dir = folder_setup.addons_dir / addon_name

        def include_direct_addon_file(path: Path) -> bool:
            relative = path.relative_to(addon_dir).as_posix().casefold()
            return path.suffix.casefold() == ".pcf" or (
                relative.startswith("materials/skybox/")
                and path.suffix.casefold() == ".vmt"
            )

        entries.extend(
            _tree_entries(
                addon_dir,
                f"direct_addons/{index}/{addon_name}",
                include_direct_addon_file,
            )[1:]
        )

    for particle_name, mod_name in sorted(particle_selections.items()):
        source_path = (
            folder_setup.particles_dir
            / mod_name
            / "actual_particles"
            / f"{particle_name}.pcf"
        )
        entries.append(
            _file_entry(
                source_path,
                f"selected_particles/{particle_name}/{mod_name}.pcf",
            )
        )

    entries.extend(
        _tree_entries(
            folder_setup.install_dir / "backup" / "particles",
            "bundled_backup/particles",
            lambda path: path.suffix.casefold() == ".pcf",
            _content_file_entry,
        )
    )
    entries.extend(
        _tree_entries(
            folder_setup.install_dir / "backup" / "materials" / "skybox",
            "bundled_backup/materials/skybox",
            lambda path: path.suffix.casefold() == ".vmt",
            _content_file_entry,
        )
    )
    entries.extend(
        _tree_entries(
            folder_setup.backup_dir / "particles",
            "runtime_backup/particles",
            lambda path: path.suffix.casefold() == ".pcf",
        )
    )
    entries.append(
        _content_file_entry(
            folder_setup.particle_system_map_file,
            "particle_system_map.json",
        )
    )
    return entries


def capture_direct_game_output(tf_path: Path | str) -> list[list]:
    tf_path = Path(tf_path)
    vpk_name = get_vpk_name(tf_path)
    vpk_prefix = vpk_name.removesuffix("_dir.vpk")
    vpk_paths = sorted(
        tf_path.glob(f"{vpk_prefix}_*.vpk"),
        key=lambda path: path.name.casefold(),
    )
    if not vpk_paths:
        return [_file_entry(tf_path / vpk_name, vpk_name)]
    return [_file_entry(path, path.name) for path in vpk_paths]


class InstallStateStore:
    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def _target_key(tf_path: Path | str) -> str:
        normalized = os.path.normcase(os.path.abspath(str(tf_path)))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _empty_state() -> dict:
        return {"schema": INSTALL_STATE_SCHEMA, "targets": {}}

    def _load(self) -> dict:
        if not self.path.is_file():
            return self._empty_state()
        try:
            with self.path.open("r", encoding="utf-8") as file:
                state = json.load(file)
            if (
                isinstance(state, dict)
                and state.get("schema") == INSTALL_STATE_SCHEMA
                and isinstance(state.get("targets"), dict)
            ):
                return state
        except (OSError, json.JSONDecodeError):
            log.exception("Failed to load install state; a full install will be used")
        return self._empty_state()

    def _write(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        temp_path.replace(self.path)

    def evaluate(
        self,
        tf_path: Path | str,
        request_header: dict,
        selected_addons: list[str],
        particle_selections: dict[str, str],
    ) -> tuple[bool, str]:
        target = self._load()["targets"].get(self._target_key(tf_path))
        if target is None:
            return False, "no_previous_state"
        if target.get("request") != request_header:
            return False, "request_changed"
        if target.get("sources") != capture_source_state(selected_addons, particle_selections):
            return False, "source_files_changed"

        custom_dir = Path(tf_path) / "custom"
        if target.get("external_custom") != capture_external_custom_state(custom_dir):
            return False, "external_custom_changed"
        if target.get("outputs") != capture_managed_outputs(tf_path):
            return False, "managed_outputs_changed"
        if request_header.get("game_target") == "Team Fortress 2":
            if target.get("direct_game_inputs") != capture_direct_game_inputs(
                selected_addons,
                particle_selections,
                request_header["options"]["disable_paint_colors"],
            ):
                return False, "direct_game_inputs_changed"
            if target.get("direct_game_output") != capture_direct_game_output(tf_path):
                return False, "direct_game_output_changed"
        return True, "up_to_date"

    def reusable_external_custom_paths(
        self,
        tf_path: Path | str,
        request_header: dict,
    ) -> set[str]:
        """Return external custom files already finalized by this recipe."""
        target = self._load()["targets"].get(self._target_key(tf_path))
        if target is None:
            return set()

        previous_request = target.get("request")
        if not isinstance(previous_request, dict):
            return set()
        compatibility_keys = ("recipe", "app_version", "game_target")
        if any(previous_request.get(key) != request_header.get(key) for key in compatibility_keys):
            return set()

        saved_entries = {
            tuple(entry)
            for entry in target.get("external_custom", [])
            if isinstance(entry, list) and len(entry) == 4
        }
        current_entries = {
            tuple(entry)
            for entry in capture_external_custom_state(Path(tf_path) / "custom")
            if len(entry) == 4
        }

        reusable = set()
        for entry in saved_entries & current_entries:
            label = entry[0]
            if isinstance(label, str) and label.startswith("custom/"):
                reusable.add(label.removeprefix("custom/"))
        return reusable

    def can_reuse_precache(
        self,
        tf_path: Path | str,
        request_header: dict,
        model_list: set[str],
    ) -> bool:
        target = self._load()["targets"].get(self._target_key(tf_path))
        if target is None:
            return False

        previous_request = target.get("request")
        if not isinstance(previous_request, dict):
            return False
        compatibility_keys = ("recipe", "app_version", "game_target")
        if any(previous_request.get(key) != request_header.get(key) for key in compatibility_keys):
            return False

        return (
            target.get("precache_models") == sorted(model_list)
            and target.get("precache_outputs") == capture_precache_outputs(tf_path)
        )

    def can_reuse_direct_game_files(
        self,
        tf_path: Path | str,
        request_header: dict,
        selected_addons: list[str],
        particle_selections: dict[str, str],
        disable_paint_colors: bool,
    ) -> bool:
        target = self._load()["targets"].get(self._target_key(tf_path))
        if target is None:
            return False

        previous_request = target.get("request")
        if not isinstance(previous_request, dict):
            return False
        compatibility_keys = ("recipe", "app_version", "game_target")
        if any(previous_request.get(key) != request_header.get(key) for key in compatibility_keys):
            return False

        return (
            target.get("direct_game_inputs")
            == capture_direct_game_inputs(
                selected_addons,
                particle_selections,
                disable_paint_colors,
            )
            and target.get("direct_game_output") == capture_direct_game_output(tf_path)
        )

    def save_current(
        self,
        tf_path: Path | str,
        request_header: dict,
        selected_addons: list[str],
        particle_selections: dict[str, str],
        precache_models: set[str] | None = None,
    ) -> None:
        state = self._load()
        is_tf2 = request_header.get("game_target") == "Team Fortress 2"
        state["targets"][self._target_key(tf_path)] = {
            "request": request_header,
            "sources": capture_source_state(selected_addons, particle_selections),
            "external_custom": capture_external_custom_state(Path(tf_path) / "custom"),
            "outputs": capture_managed_outputs(tf_path),
            "precache_models": sorted(precache_models) if precache_models is not None else None,
            "precache_outputs": (
                capture_precache_outputs(tf_path) if precache_models is not None else None
            ),
            "direct_game_inputs": (
                capture_direct_game_inputs(
                    selected_addons,
                    particle_selections,
                    request_header["options"]["disable_paint_colors"],
                )
                if is_tf2
                else None
            ),
            "direct_game_output": capture_direct_game_output(tf_path) if is_tf2 else None,
        }
        self._write(state)

    def clear(self, tf_path: Path | str) -> None:
        state = self._load()
        if state["targets"].pop(self._target_key(tf_path), None) is not None:
            self._write(state)

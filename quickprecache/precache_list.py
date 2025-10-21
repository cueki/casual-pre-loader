from pathlib import Path
from typing import Set, List
from core.constants import QUICKPRECACHE_FILE_SUFFIXES, QUICKPRECACHE_MODEL_LIST
from valve_parsers import VPKFile


def make_precache_list(game_path: str) -> Set[str]:
    # get list of files to precache from custom
    model_list = set()
    custom_folder = Path(game_path) / "tf" / "custom"

    if custom_folder.is_dir():
        for file in custom_folder.iterdir():
            if file.is_dir() and "disabled" not in file.name:
                model_list.update(manage_folder(file))
            elif file.is_file() and file.name.endswith(".vpk"):
                model_list.update(manage_vpk(file))

    # filter out cosmetics and other non-gameplay models
    exclusions = ["decompiled ", "competitive_badge", "gameplay_cosmetic", "player/items/", "workshop/player/items/"]
    return {model for model in model_list if not any(exclusion in model for exclusion in exclusions)}


def _should_quickprecache(file_path: str) -> bool:
    file_path_lower = file_path.lower()
    return any(keyword in file_path_lower for keyword in QUICKPRECACHE_MODEL_LIST)


def _process_file_to_model_path(file_path: str) -> str:
    for suffix in QUICKPRECACHE_FILE_SUFFIXES:
        if file_path.endswith(suffix):
            return file_path[:-(len(suffix))] + ".mdl"
    return file_path


def manage_folder(folder_path: Path) -> Set[str]:
    model_set = set()

    for file_path in folder_path.glob("**/*"):
        if not file_path.is_file():
            continue

        relative_path = str(file_path.relative_to(folder_path))

        if not _should_quickprecache(relative_path):
            continue

        if any(relative_path.endswith(suffix) for suffix in QUICKPRECACHE_FILE_SUFFIXES):
            model_path = Path(_process_file_to_model_path(relative_path)).as_posix().lower()
            model_set.add(model_path)

    return model_set


def manage_vpk(vpk_path: Path) -> Set[str]:
    # extract model paths from a VPK file
    model_set = set()
    failed_vpks = []

    try:
        vpk_file = VPKFile(str(vpk_path))

        # find all files in the models directory in the vpk
        model_files = vpk_file.find_files("models/")

        for file_path in model_files:
            if not _should_quickprecache(file_path):
                continue

            # check if file has a quickprecache suffix
            if any(file_path.endswith(suffix) for suffix in QUICKPRECACHE_FILE_SUFFIXES):
                if file_path.startswith("models/"):
                    # remove "models/" prefix and convert to model path
                    relative_path = file_path[7:]
                    model_path = _process_file_to_model_path(relative_path).lower()
                    model_set.add(model_path)

    except Exception as e:
        print(f"Failed to process VPK {vpk_path}: {e}")
        failed_vpks.append(str(vpk_path))

    return model_set
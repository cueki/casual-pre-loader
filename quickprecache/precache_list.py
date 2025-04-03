from pathlib import Path
from typing import Set, List
from core.constants import QUICKPRECACHE_FILE_SUFFIXES
from core.parsers.vpk_file import VPKFile


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

    # filter for "decompiled " and "competitive_badge"
    return {model for model in model_list if "decompiled " not in model and "competitive_badge" not in model}


def manage_folder(folder_path: Path) -> List[str]:
    model_list = []

    for file_path in folder_path.glob("**/*"):
        # we quickprecache these because they won't stay loaded between map changes
        if (not ("prop" in str(file_path).lower()
                or "flag" in str(file_path).lower())
                or "models/bots" in str(file_path).lower()
                or "ammo_box" in str(file_path).lower()
                or "ammopack" in str(file_path).lower()
                or "medkit" in str(file_path).lower()):
            continue

        if file_path.is_file():
            entry = str(file_path.relative_to(folder_path))

            for suffix in QUICKPRECACHE_FILE_SUFFIXES:
                if entry.endswith(suffix):
                    # replace the suffix with .mdl
                    model_path = Path(entry).with_suffix('.mdl').as_posix().lower()
                    model_list.append(model_path)
                    break

    return model_list


def manage_vpk(vpk_path: Path) -> List[str]:
    # extract model paths from a VPK file (using my vpk handler)
    model_list = []
    failed_vpks = []

    try:
        vpk_file = VPKFile(str(vpk_path))
        vpk_file.parse_directory()

        # find all files in the models directory in the vpk
        model_files = vpk_file.find_files("models/")

        for file_path in model_files:
            # we quickprecache these because they won't stay loaded between map changes
            if not ("prop" in str(file_path).lower()
                    or "flag" in str(file_path).lower()
                    or "models/bots" in str(file_path).lower()
                    or "ammo_box" in str(file_path).lower()
                    or "ammopack" in str(file_path).lower()
                    or "medkit" in str(file_path).lower()):
                continue

            for suffix in QUICKPRECACHE_FILE_SUFFIXES:
                if file_path.endswith(suffix):
                    # extract the model path, removing the models/ prefix
                    if file_path.startswith("models/"):
                        model_path = file_path[7:].lower()
                        # normalize to MDL format
                        model_path = model_path[:-(len(suffix))] + ".mdl"
                        model_list.append(model_path)
                    break

    except Exception as e:
        print(f"Failed to process VPK {vpk_path}: {e}")
        failed_vpks.append(str(vpk_path))

    return model_list
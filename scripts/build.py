import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from sys import stderr

# add parent directory to path to import from core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.constants import BUILD_DIRS, BUILD_FILES
from core.version import VERSION

log = logging.getLogger()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build script')
    parser.add_argument('--target_dir', help='Target directory to deploy the application')
    return parser.parse_args()


def ignore_studio_folder(directory, contents):
    ignored = []
    rel_dir = Path(directory).relative_to(Path(directory).anchor)
    if 'quickprecache' in rel_dir.parts and 'studio' in contents:
        ignored.append('studio')
    return ignored


def copy_project_files(source_dir, target_dir):
    log.info(f"Copying project files from {source_dir} to {target_dir}...")

    # copy directories
    for dir_name in BUILD_DIRS:
        source_path = Path(source_dir) / dir_name
        target_path = Path(target_dir) / dir_name

        if source_path.exists():
            log.info(f"Copying directory: {dir_name}")
            # exclude quickprecache/studio folder (only needed on Linux, not in Windows releases)
            if dir_name == 'core':
                shutil.copytree(source_path, target_path, dirs_exist_ok=True,
                               ignore=ignore_studio_folder)
            else:
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            log.warning(f"Missing {dir_name}")

    # copy individual files
    for file_name in BUILD_FILES:
        source_path = Path(source_dir) / file_name
        target_path = Path(target_dir) / file_name

        if source_path.exists():
            log.info(f"Copying file: {file_name}")
            shutil.copy2(source_path, target_path)
        else:
            log.warning(f"Missing {file_name}")


def confirm_version():
    response = input(f"\n=== Building version: {VERSION} ===\nIs this the correct version? (y/n): ").strip().lower()
    if response != 'y':
        log.info("Build cancelled. Update VERSION in core/version.py and try again.")
        sys.exit(1)


def main():
    args = parse_arguments()

    try:
        from rich.logging import RichHandler

        log.addHandler(RichHandler())
    except ModuleNotFoundError:
        log.addHandler(logging.StreamHandler())

    confirm_version()
    # get project root (parent of scripts/ directory)
    source_dir = Path(__file__).resolve().parent.parent
    target_dir = Path(args.target_dir)
    target_dir.mkdir(exist_ok=True, parents=True)
    copy_project_files(source_dir, target_dir)

    runme_source = Path(source_dir) / "scripts" / "RUNME.bat"
    if runme_source.exists():
        runme_target = target_dir.parent / "RUNME.bat"
        log.info(f"Copying RUNME.bat to {runme_target}")
        shutil.copy2(runme_source, runme_target)
    else:
        log.warning("RUNME.bat not found")

    log.info(f"Build completed successfully to {target_dir}")
    log.info('feathers wuz here')


if __name__ == "__main__":
    main()

import os
import sys
import shutil
import argparse
from pathlib import Path

# add parent directory to path to import from core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.constants import BUILD_DIRS, BUILD_FILES
from core.version import VERSION


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
    print(f"Copying project files from {source_dir} to {target_dir}...")

    # copy directories
    for dir_name in BUILD_DIRS:
        source_path = Path(source_dir) / dir_name
        target_path = Path(target_dir) / dir_name

        if source_path.exists():
            print(f"Copying directory: {dir_name}")
            # exclude quickprecache/studio folder (only needed on Linux, not in Windows releases)
            if dir_name == 'core':
                shutil.copytree(source_path, target_path, dirs_exist_ok=True,
                               ignore=ignore_studio_folder)
            else:
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            print(f"Warning: Missing {dir_name}")

    # copy individual files
    for file_name in BUILD_FILES:
        source_path = Path(source_dir) / file_name
        target_path = Path(target_dir) / file_name

        if source_path.exists():
            print(f"Copying file: {file_name}")
            shutil.copy2(source_path, target_path)
        else:
            print(f"Warning: Missing {file_name}")


def confirm_version():
    print(f"\n=== Building version: {VERSION} ===\n")
    response = input("Is this the correct version? (y/n): ").strip().lower()
    if response != 'y':
        print("Build cancelled. Update VERSION in core/version.py and try again.")
        sys.exit(1)


def main():
    args = parse_arguments()
    confirm_version()
    # get project root (parent of scripts/ directory)
    source_dir = Path(__file__).resolve().parent.parent
    target_dir = Path(args.target_dir)
    target_dir.mkdir(exist_ok=True, parents=True)
    copy_project_files(source_dir, target_dir)

    runme_source = Path(source_dir) / "scripts" / "RUNME.bat"
    if runme_source.exists():
        runme_target = target_dir.parent / "RUNME.bat"
        print(f"Copying RUNME.bat to {runme_target}")
        shutil.copy2(runme_source, runme_target)
    else:
        print("Warning: RUNME.bat not found")

    print(f"Build completed successfully to {target_dir}")
    print('feathers wuz here')


if __name__ == "__main__":
    main()

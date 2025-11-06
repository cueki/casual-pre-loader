import os
import shutil
import argparse
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build script')
    parser.add_argument('--target_dir', help='Target directory to deploy the application')
    return parser.parse_args()


def copy_project_files(source_dir, target_dir):
    print(f"Copying project files from {source_dir} to {target_dir}...")

    # list of directories to copy
    dirs_to_copy = [
        'core',
        'core/handlers',
        'gui',
        'operations',
        'backup',
        'backup/cfg',
        'backup/cfg/w',
    ]

    # list of files to copy
    files_to_copy = [
        'main.py',
        'particle_system_map.json',
        'mod_urls.json',
        'LICENSE',
        'README.md',
        'requirements.txt'
    ]

    # copy directories
    for dir_name in dirs_to_copy:
        source_path = Path(source_dir) / dir_name
        target_path = Path(target_dir) / dir_name

        if source_path.exists():
            print(f"Copying directory: {dir_name}")
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            print(f"Warning: Missing {dir_name}")

    # copy quickprecache but exclude studio/ folder (only needed on Linux)
    quickprecache_source = Path(source_dir) / 'quickprecache'
    quickprecache_target = Path(target_dir) / 'quickprecache'
    if quickprecache_source.exists():
        shutil.copytree(
            quickprecache_source,
            quickprecache_target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('studio')
        )

    # copy individual files
    for file_name in files_to_copy:
        source_path = Path(source_dir) / file_name
        target_path = Path(target_dir) / file_name

        if source_path.exists():
            print(f"Copying file: {file_name}")
            shutil.copy2(source_path, target_path)
        else:
            print(f"Warning: Missing {file_name}")


def main():
    args = parse_arguments()
    source_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = Path(args.target_dir)
    target_dir.mkdir(exist_ok=True, parents=True)
    copy_project_files(source_dir, target_dir)

    runme_source = Path(source_dir) / "RUNME.bat"
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

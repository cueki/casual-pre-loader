import os
import shutil
import zipfile
import argparse
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build script')
    parser.add_argument('--target_dir', help='Target directory to deploy the application')
    parser.add_argument('--user-mods-zip', help='Path to user_mods.zip file', default='mods.zip')
    return parser.parse_args()


def copy_project_files(source_dir, target_dir):
    print(f"Copying project files from {source_dir} to {target_dir}...")

    # list of directories to copy
    dirs_to_copy = [
        'core',
        'core/handlers',
        'core/parsers',
        'gui',
        'operations',
        'backup',
        'backup/cfg',
        'backup/cfg/w',
        'quickprecache'
    ]

    # list of files to copy
    files_to_copy = [
        'app.py',
        'particle_system_map.json',
        'mod_urls.json',
        'LICENSE',
        'README.md'
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

    # copy individual files
    for file_name in files_to_copy:
        source_path = Path(source_dir) / file_name
        target_path = Path(target_dir) / file_name

        if source_path.exists():
            print(f"Copying file: {file_name}")
            shutil.copy2(source_path, target_path)
        else:
            print(f"Warning: Missing {file_name}")


def zip_mods_directory(source_dir, target_dir):
    mods_dir = Path(source_dir) / "mods"
    zip_path = Path(target_dir) / "mods.zip"

    if not mods_dir.exists():
        print(f"Warning: Mods directory {mods_dir} not found")
        return

    print(f"Creating {zip_path} from {mods_dir}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(mods_dir):
            for file in files:
                file_path = os.path.join(root, file)
                archive_name = os.path.relpath(file_path, mods_dir)
                zipf.write(file_path, archive_name)

    print(f"Successfully created {zip_path}")


def main():
    args = parse_arguments()

    source_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = Path(args.target_dir)

    # copy project files
    target_dir.mkdir(exist_ok=True, parents=True)
    copy_project_files(source_dir, target_dir)
    zip_mods_directory(source_dir, target_dir)

    print(f"Build completed successfully to {target_dir}")
    print('feathers wuz here')


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import os
import sys
import shutil
import zipfile
import argparse
from pathlib import Path
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build script')
    parser.add_argument('--target_dir', help='Target directory to deploy the application')
    parser.add_argument('--user-mods-zip', help='Path to user_mods.zip file', default='user_mods.zip')
    return parser.parse_args()


def copy_project_files(source_dir, target_dir):
    print(f"Copying project files from {source_dir} to {target_dir}...")

    # list of directories to copy
    dirs_to_copy = [
        'core',
        'gui',
        'handlers',
        'operations',
        'parsers',
        'tools',
        'addons',
        'backup'
    ]

    # list of files to copy
    files_to_copy = [
        'app.py',
        'particle_system_map.json',
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


def extract_user_mods(zip_path, target_dir):
    zip_file = Path(zip_path)
    if not zip_file.exists():
        print(f"Warning: {zip_file} not found")
        return False

    target_user_mods = Path(target_dir) / 'user_mods'
    target_user_mods.mkdir(exist_ok=True, parents=True)

    print(f"Extracting {zip_file} to {target_user_mods}...")
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(target_user_mods)
        return True
    except Exception as e:
        print(f"Error extracting user_mods.zip: {e}")
        return False


def main():
    args = parse_arguments()

    source_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = Path(args.target_dir)
    user_mods_zip = Path(args.user_mods_zip)

    # copy project files
    target_dir.mkdir(exist_ok=True, parents=True)
    copy_project_files(source_dir, target_dir)

    # extract user_mods.zip
    if Path(user_mods_zip).exists():
        extract_user_mods(user_mods_zip, target_dir)

    print(f"Build completed successfully to {target_dir}")


if __name__ == "__main__":
    main()
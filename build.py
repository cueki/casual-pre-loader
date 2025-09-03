import os
import shutil
import zipfile
import argparse
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build script')
    parser.add_argument('--target_dir', help='Target directory to deploy the application')
    parser.add_argument('--user-mods-zip', help='Path to mods.zip file', default='mods.zip')
    parser.add_argument('--skip-mods-zip', action='store_true', help='Skip creating mods.zip file')
    parser.add_argument('--build-variant', choices=['full', 'light', 'both'], default='full', 
                        help='Build variant: full (with mods.zip), light (without mods.zip), or both')
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
        'quickprecache'
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


def build_variant(source_dir, target_dir, include_mods_zip=True, variant_name=""):
    if variant_name:
        variant_dir = target_dir / variant_name
        app_dir = variant_dir / "casual-preloader"
    else:
        variant_dir = target_dir
        app_dir = variant_dir
    
    app_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"Building {variant_name or 'default'} variant...")
    copy_project_files(source_dir, app_dir)
    
    if include_mods_zip:
        zip_mods_directory(source_dir, app_dir)
        print(f"{variant_name or 'Build'} includes mods.zip")
    else:
        print(f"{variant_name or 'Build'} excludes mods.zip")

    if variant_name:
        shutil.copy2("RUNME.bat", variant_dir)
        shutil.copy2("READ_THIS.txt", variant_dir)
    
    return app_dir


def main():
    args = parse_arguments()

    source_dir = os.path.dirname(os.path.abspath(__file__))
    base_target_dir = Path(args.target_dir)

    if args.build_variant == 'both':
        full_dir = build_variant(source_dir, base_target_dir, True, "casual-preloader-full")
        light_dir = build_variant(source_dir, base_target_dir, False, "casual-preloader-light")
        print(f"Both variants built successfully:")
        print(f"  Full:  {full_dir}")
        print(f"  Light: {light_dir}")
    else:
        include_mods = args.build_variant == 'full' and not args.skip_mods_zip
        build_variant(source_dir, base_target_dir, include_mods)
        print(f"Build completed successfully to {base_target_dir}")
    
    print('feathers wuz here')


if __name__ == "__main__":
    main()
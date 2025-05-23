import zipfile
from pathlib import Path
from typing import Tuple

def initial_setup(*packages_to_extract: Tuple[Path, Path]):
    for zip_path, extract_dir in packages_to_extract:
        if zip_path.exists():
            try:
                extract_dir.mkdir(parents=True, exist_ok=True)

                print(f"Extracting {zip_path.name} to {extract_dir}...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                print(f"Extracted {zip_path.name} successfully")
            except Exception as e:
                print(f"Error extracting {zip_path}: {e}")

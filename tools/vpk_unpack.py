from pathlib import Path
from typing import List, Optional
from handlers.vpk_handler import VPKHandler
from core.folder_setup import folder_setup


class VPKExtractor:
    def __init__(self, vpk_handler: VPKHandler):
        self.vpk = vpk_handler

    def extract_files(self, patterns: Optional[List[str]] = None) -> List[str]:
        if patterns is None:
            patterns = ["particles/*", "materials/*", "effects/*", "models/*"]

        extracted_files = []

        for pattern in patterns:
            matching_files = self.vpk.find_files(pattern)

            for file_path in matching_files:

                relative_path = Path(file_path)
                if relative_path.suffix == '.pcf':
                    # PCF files go directly to mods/particles
                    output_path = folder_setup.get_mods_path(relative_path)
                else:
                    # everything else goes to mods/everything_else/materials etc
                    output_path = folder_setup.get_mods_path("everything_else" / relative_path)

                # ensure the output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                print(output_path)
                # extract the file
                if self.vpk.extract_file(file_path, str(output_path)):
                    extracted_files.append(str(output_path))
                else:
                    print(f"Failed to extract: {file_path}")

        return extracted_files

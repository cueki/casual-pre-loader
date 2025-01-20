from pathlib import Path
from typing import List, Optional
from handlers.vpk_handler import VPKHandler


class VPKExtractor:
    def __init__(self, vpk_handler: VPKHandler, output_base: str = "mods"):
        self.vpk = vpk_handler
        self.output_base = Path(output_base)

    def extract_files(self, patterns: Optional[List[str]] = None) -> List[str]:
        if patterns is None:
            patterns = ["particles/*.pcf", "materials/"]

        extracted_files = []

        for pattern in patterns:
            matching_files = self.vpk.find_files(pattern)

            for file_path in matching_files:
                # create the full output path
                relative_path = Path(file_path)
                output_path = self.output_base / relative_path

                # ensure the output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # extract the file
                if self.vpk.extract_file(file_path, str(output_path)):
                    extracted_files.append(str(output_path))
                else:
                    print(f"Failed to extract: {file_path}")

        return extracted_files
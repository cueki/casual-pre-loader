import itertools
import logging
import tempfile
from pathlib import Path
from typing import Set

from core.folder_setup import folder_setup
from core.quickprecache.precache_list import make_precache_list
from core.quickprecache.r_rootlod import check_root_lod
from core.quickprecache.studio_mdl import StudioMDL

log = logging.getLogger()


def handle_string(input_str: str) -> str:
    # strip and remove quotes
    input_str = input_str.strip()
    input_str = input_str.replace('"', '')

    # remove models/ prefix if present
    if input_str.startswith("models/"):
        input_str = input_str[7:]

    # remove comments
    if "//" in input_str:
        input_str = input_str[:input_str.index("//")].strip()

    # add .mdl extension if missing
    if not input_str.endswith(".mdl"):
        input_str += ".mdl"

    return input_str


def load_list_from_file(list_file: str) -> Set[str]:
    # load the model list from a file
    model_list = set()

    try:
        with open(list_file, 'r') as f:
            for line in f:
                line = line.strip()

                # skip empty lines and comments
                if not line or line.startswith("//"):
                    continue

                model = handle_string(line)
                if model:
                    model_list.add(model)
                    log.info(f"Added model: {model}")
    except Exception:
        log.exception(f"Error loading model list from {list_file}")

    return model_list


def get_model_name(model: str) -> str:
    # get
    return f'$modelname "{model}.mdl"\n'


def get_include_model(include: str) -> str:
    # deez
    return f'$includemodel "{include}"\n'


def get_precache_string_builder(index: int) -> str:
    # nuts
    return get_model_name(f"precache_{index}")


class QuickPrecache:
    # maximum size for QC file content (in chars)
    MAX_SPLIT_SIZE = 2048

    def __init__(self, game_path: str, debug: bool = False, progress_callback=None):
        # debug keeps temp files
        self.game_path = game_path
        self.debug = debug
        self.model_list = set()
        self.failed_vpks = []
        self.builder_index = 0
        self.studio_mdl = None
        self.temp_files = []
        self.progress_callback = progress_callback
        self.compiled_count = 0
        self.total_compiles = 0

    def update_progress(self, message: str):
        if self.progress_callback and self.total_compiles > 0:
            progress_range = 10
            start_progress = 85
            progress_percent = (self.compiled_count / self.total_compiles) * progress_range
            current_progress = start_progress + int(progress_percent)
            self.progress_callback(current_progress, message)

    def flush_files(self) -> int:
        # remove any previously created precache model files
        models_folder = Path(self.game_path) / "tf" / "models"
        count = 0

        if models_folder.exists():
            for file in models_folder.glob("*"):
                if (file.name == "precache.mdl" or
                        (file.name.startswith("precache_") and file.name.endswith(".mdl"))):
                    file.unlink()
                    count += 1

        return count

    def save_list_to_file(self, output_file: str) -> bool:
        # save the current model list to a file
        try:
            with open(output_file, 'w') as f:
                for model in sorted(self.model_list):
                    f.write(f"{model}\n")
            return True
        except Exception:
            log.exception(f"Error saving model list to {output_file}")
            return False

    def make_precache_sub_list(self, strings: Set[str]) -> None:
        # create subdivided QC files for the model list
        builder = get_precache_string_builder(self.builder_index)
        passed_strings = set()
        estimated_builders = max(1, len(strings) // 10)  # rough estimate
        self.total_compiles = estimated_builders + 1
        self.compiled_count = 0

        # cycle through strings until all are processed
        for s in itertools.cycle(strings):
            if s in passed_strings:
                continue

            include_line = get_include_model(s)

            # check if adding this line would exceed max size
            if len(builder) + len(include_line) <= self.MAX_SPLIT_SIZE:
                builder += include_line
                passed_strings.add(s)
            else:
                # current builder is full, save it and start a new one
                self.make_precache_sub_list_file(f"precache_{self.builder_index}.qc", builder)
                self.builder_index += 1
                builder = get_precache_string_builder(self.builder_index)

            # check if all strings have been processed
            if len(strings) == len(passed_strings):
                # save the last builder
                self.make_precache_sub_list_file(f"precache_{self.builder_index}.qc", builder)
                self.builder_index += 1
                self.total_compiles = self.builder_index + 1
                break

    def make_precache_sub_list_file(self, filename: str, data: str) -> bool:
        # create a QC file and compile it with StudioMDL
        try:
            # create a temporary file
            folder_setup.temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.qc',
                delete=False,
                dir=folder_setup.temp_dir
            )

            # save the original filename for reference
            temp_path = Path(temp_file.name)

            # write the QC content
            temp_file.write(data)
            temp_file.close()
            if not self.debug:
                self.temp_files.append(temp_path)

            # compile with StudioMDL
            self.update_progress(f"Compiling precache models ({self.compiled_count + 1}/{self.total_compiles})...")
            success = self.studio_mdl.make_model(str(temp_path))

            self.compiled_count += 1
            self.update_progress(f"Compiling precache models ({self.compiled_count}/{self.total_compiles})...")

            return success
        except Exception:
            log.exception(f"Error creating QC file {filename}")
            return False

    def make_precache_list_file(self) -> bool:
        # create the main precache.qc file that includes all subfiles
        try:
            # create the main QC file
            folder_setup.temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.qc',
                delete=False,
                dir=folder_setup.temp_dir
            )

            temp_path = Path(temp_file.name)

            # write the model name and includes
            temp_file.write(get_model_name("precache"))
            for i in range(self.builder_index):
                temp_file.write(get_include_model(f"precache_{i}.mdl"))

            temp_file.close()
            if not self.debug:
                self.temp_files.append(temp_path)

            # compile the main file
            self.update_progress(f"Compiling final precache model ({self.compiled_count + 1}/{self.total_compiles})...")
            result = self.studio_mdl.make_model(str(temp_path))
            self.compiled_count += 1
            self.update_progress("QuickPrecache complete!")

            return result
        except Exception:
            log.exception("Error creating main precache QC file")
            return False

    def cleanup(self) -> None:
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                log.exception(f"Error removing temporary file {temp_file}")

    def run(self, auto: bool = False, list_file: str = "", flush: bool = False) -> bool:
        # main process
        try:
            # step 1: flush old files
            files_removed = self.flush_files()

            if flush:
                log.info("Flush completed. Exiting as requested.")
                log.info(f"Removed {files_removed} existing precache files")
                return True

            # initialize StudioMDL only when we actually need to compile
            # TODO: add warning here?
            self.studio_mdl = StudioMDL(self.game_path)

            # step 2: check config (is this actually needed)?
            check_root_lod(self.game_path)

            # step 3: get the model list
            if auto:
                log.info("Auto-scanning for models...")
                self.model_list = make_precache_list(self.game_path)

                # save the list if requested
                if list_file:
                    self.save_list_to_file(list_file)
            else:
                # use provided list file
                if not list_file:
                    list_file = "precachelist.txt"

                log.info(f"Loading model list from {list_file}")
                self.model_list = load_list_from_file(list_file)

            # display the model list
            log.info(f"Found {len(self.model_list)} models to precache:")
            for model in sorted(self.model_list):
                log.info(f"{model}")

            # step 4: create QC files and compile them
            self.make_precache_sub_list(self.model_list)
            self.make_precache_list_file()

            # step 5: report any failed VPKs
            if self.failed_vpks:
                log.warning("Failed to load invalid vpk(s):")
                for vpk_path in self.failed_vpks:
                    log.warning(f"{vpk_path}")

            return True
        except Exception:
            log.exception("Error in precache process")
            return False
        finally:
            if not self.debug:
                self.cleanup()

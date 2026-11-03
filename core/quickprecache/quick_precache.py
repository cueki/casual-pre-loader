import logging
import tempfile
from pathlib import Path

from more_itertools import constrained_batches

from core.config import config
from core.quickprecache.precache_list import make_precache_list
from core.quickprecache.r_rootlod import check_root_lod
from core.quickprecache.studio_mdl import StudioMDL
from core.util import NoopProgressCallback, ProgressCallback

log = logging.getLogger(__name__)


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


def load_list_from_file(list_file: str) -> set[str]:
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
    # room reserved in each chunk for its $modelname header
    HEADER_RESERVE = len(get_precache_string_builder(9999))

    def __init__(self, game_path: Path, debug: bool = False, progress_callback: ProgressCallback = NoopProgressCallback):
        # debug keeps temp files
        self.game_path: Path = game_path
        self.debug = debug
        self.model_list = set()
        self.failed_vpks = []
        self.failed_compiles = []
        self.builder_index = 0
        self.studio_mdl = None
        self.temp_files = []
        self.progress_callback = progress_callback
        self.compiled_count = 0
        self.total_compiles = 0

    def update_progress(self, message: str):
        if self.total_compiles > 0:
            progress_range = 10
            start_progress = 85
            progress_percent = (self.compiled_count / self.total_compiles) * progress_range
            current_progress = start_progress + int(progress_percent)
            self.progress_callback(current_progress, message)

    def flush_files(self) -> int:
        # remove any previously created precache model files
        models_folder = self.game_path / "tf" / "models"
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

    def split_into_builders(self, strings: set[str]) -> list[str]:
        # pack the $includemodel lines into chunks that fit within MAX_SPLIT_SIZE
        lines = [get_include_model(s) for s in sorted(strings)]
        batches = constrained_batches(lines, self.MAX_SPLIT_SIZE - self.HEADER_RESERVE, strict=True)
        return ["".join(batch) for batch in batches]

    def make_precache_sub_list(self, strings: set[str]) -> None:
        # create subdivided QC files for the model list
        # split first so the real total is known before the first progress message
        bodies = self.split_into_builders(strings)

        # + 1 for the main precache.mdl from make_precache_list_file
        self.total_compiles = len(bodies) + 1
        self.compiled_count = 0

        # the chunk index names both the file and its $modelname, so get both
        for index, body in enumerate(bodies, start=self.builder_index):
            filename = f"precache_{index}.qc"
            if not self.make_precache_sub_list_file(filename, get_precache_string_builder(index) + body):
                self.failed_compiles.append(filename)

        self.builder_index += len(bodies)

    def _write_temp_qc(self, data: str) -> Path:
        # write QC content to a temp file for StudioMDL
        config.temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.qc',
            delete=False,
            dir=config.temp_dir
        ) as temp_file:
            temp_file.write(data)
            temp_path = Path(temp_file.name)

        if not self.debug:
            self.temp_files.append(temp_path)

        return temp_path

    def make_precache_sub_list_file(self, filename: str, data: str) -> bool:
        # create a QC file and compile it with StudioMDL
        try:
            temp_path = self._write_temp_qc(data)

            self.update_progress(f"Compiling precache models ({self.compiled_count + 1}/{self.total_compiles})...")
            success = self.studio_mdl.make_model(temp_path)

            self.compiled_count += 1
            self.update_progress(f"Compiling precache models ({self.compiled_count}/{self.total_compiles})...")

            return success
        except Exception:
            log.exception(f"Error creating QC file {filename}")
            return False

    def make_precache_list_file(self) -> bool:
        # create the main precache.qc file that includes all subfiles
        try:
            # write the model name and includes
            data = get_model_name("precache")
            for i in range(self.builder_index):
                data += get_include_model(f"precache_{i}.mdl")

            temp_path = self._write_temp_qc(data)

            # compile the main file
            self.update_progress(f"Compiling final precache model ({self.compiled_count + 1}/{self.total_compiles})...")
            result = self.studio_mdl.make_model(temp_path)
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

            # step 5: report any failures
            if self.failed_compiles:
                log.warning("Failed to compile precache model(s):")
                for filename in self.failed_compiles:
                    log.warning(f"{filename}")

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

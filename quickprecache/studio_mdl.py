import subprocess
import platform
from pathlib import Path
from enum import Enum


class StudioMDLVersion(Enum):
    MISSING = ""
    STUDIOMDL32 = "bin/studiomdl.exe"
    NEKOMDL = "bin/nekomdl.exe"


class StudioMDL:
    def __init__(self, game_path: str):
        self.game_path = Path(game_path)
        self.studio_mdl_version = self._get_studio_mdl_version()

        if self.studio_mdl_version == StudioMDLVersion.MISSING:
            raise RuntimeError(
                "StudioMDL.exe not found, you probably installed the mod wrong.\n"
                "!!! IF YOU ARE ON LINUX, YOU NEED THE NEKOMDL OR STUDOMDL FROM A WINDOWS VERSION OF THE GAME !!!"
            )

    def _get_studio_mdl_version(self) -> StudioMDLVersion:
        # detect which version of StudioMDL is available
        # first we do NekoMDL
        if self._check_studio_mdl_version(StudioMDLVersion.NEKOMDL):
            return StudioMDLVersion.NEKOMDL

        # then we check for StudioMDL
        if self._check_studio_mdl_version(StudioMDLVersion.STUDIOMDL32):
            return StudioMDLVersion.STUDIOMDL32

        return StudioMDLVersion.MISSING

    def _check_studio_mdl_version(self, version: StudioMDLVersion) -> bool:
        if version == StudioMDLVersion.MISSING:
            return False

        studio_mdl_file = self.game_path / version.value
        if studio_mdl_file.exists():
            print(f"{version.value} found.")
            return True
        return False

    def make_model(self, qc_file: str) -> bool:
        # compile a QC file using StudioMDL
        if self.studio_mdl_version == StudioMDLVersion.MISSING:
            return False

        exe_path = str(self.game_path / self.studio_mdl_version.value)
        tf_path = str(Path(self.game_path) / 'tf')

        # use wine on not windows
        if platform.system() != "Windows":
            # for wine, use shell=True and use Z:path maybe ???
            cmd_str = f'wine "{exe_path}" -game "Z:{tf_path}" -nop4 -verbose "Z:{qc_file}"'
            print(f"Executing with wine: {cmd_str}")
            process = subprocess.Popen(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        else:
            # for windows, use a list of arguments
            cmd_args = [
                exe_path,
                "-game", tf_path,
                "-nop4",
                "-verbose",
                qc_file
            ]
            print(f"Executing: {' '.join(cmd_args)}")
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.strip())

        return_code = process.poll()
        return return_code == 0

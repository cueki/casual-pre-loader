import logging
import shutil
import subprocess
from pathlib import Path
from sys import platform

log = logging.getLogger()


class VTFHandler:
    def __init__(self, working_dir="temp/vtf_files"):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.vtf_cmd_path = Path("vtfedit/VTFCmd.exe").absolute()

        self.vtf_available = self.vtf_cmd_path.exists()
        if not self.vtf_available:
            log.warning("VTFCmd.exe not found at vtfedit/VTFCmd.exe. VTF operations will be disabled.")

    def _run_vtf_command(self, args):
        cmd_path = str(self.vtf_cmd_path)
        if platform != "win32":
            full_cmd = ["wine", cmd_path] + args
        else:
            full_cmd = [cmd_path] + args

        try:
            result = subprocess.run(
                full_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            log.exception("Error executing VTFCmd")
            return False, f"Error executing VTFCmd: {e.stderr}"

    def convert_vtf_to_png(self, vtf_file, relative_to="materials"):
        # temp directory with a flat structure because VTFCmd is dumb
        vtf_path = Path(vtf_file)

        # get relative path for final output
        rel_path = vtf_path.relative_to(Path(vtf_path.parts[0]) / relative_to)
        temp_vtf = self.working_dir / vtf_path.name
        shutil.copy2(vtf_path, temp_vtf)

        # convert to PNG
        args = [
            "-file", str(temp_vtf),
            "-output", ".",
            "-exportformat", "png"
        ]

        success, _ = self._run_vtf_command(args)
        if not success:
            return None

        # get the generated PNG
        temp_png = self.working_dir / f"{temp_vtf.stem}.png"
        final_dir = self.working_dir / relative_to / rel_path.parent
        final_dir.mkdir(parents=True, exist_ok=True)

        # move PNG to final location
        final_png = final_dir / f"{vtf_path.stem}.png"
        shutil.move(temp_png, final_png)

        return final_png

    def convert_png_to_vtf(self, png_file, img_format="rgba8888"):
        png_path = Path(png_file)
        out_dir = self.working_dir

        args = [
            "-file", str(png_path),
            "-output", ".",
            "-format", img_format
        ]

        success, message = self._run_vtf_command(args)
        if success:
            return Path(out_dir) / f"{png_path.stem}.vtf"
        return None

import platform
import subprocess
from pathlib import Path


class VTFHandler:
    def __init__(self, working_dir="temp/vtf_files"):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.vtf_cmd_path = Path("vtfedit/VTFCmd.exe").absolute()

        if not self.vtf_cmd_path.exists():
            raise RuntimeError("VTFCmd.exe not found. Make sure it exists at vtfedit/bin/VTFCmd.exe")

    def _run_vtf_command(self, args):
        cmd_path = str(self.vtf_cmd_path)
        if platform.system() != "Windows":
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
            return False, f"Error executing VTFCmd: {e.stderr}"

    def convert_vtf_to_png(self, vtf_file, output_dir=None):
        vtf_path = Path(vtf_file)
        out_dir = output_dir or self.working_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        args = [
            "-file", str(vtf_path),
            "-output", str(out_dir),
            "-exportformat", "png"
        ]

        success, message = self._run_vtf_command(args)
        if success:
            return Path(out_dir) / f"{vtf_path.stem}.png"
        return None

    def convert_png_to_vtf(self, png_file, output_dir=None, img_format="rgba8888"):
        png_path = Path(png_file)
        out_dir = output_dir or self.working_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        args = [
            "-file", str(png_path),
            "-output", str(out_dir),
            "-format", img_format
        ]

        success, message = self._run_vtf_command(args)
        if success:
            return Path(out_dir) / f"{png_path.stem}.vtf"
        return None

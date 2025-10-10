import platform
import zipfile
import requests
import tempfile
import shutil
from pathlib import Path
from packaging import version
from typing import Optional, Dict, Any
from core.folder_setup import folder_setup
from core.version import VERSION


class AutoUpdater:
    GITHUB_REPO = "cueki/casual-pre-loader"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    def __init__(self):
        self.install_dir = folder_setup.install_dir

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        try:
            print(f"Install dir: {self.install_dir}")

            response = requests.get(self.GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")

            if version.parse(latest_version) > version.parse(VERSION):
                return {
                    "version": latest_version,
                    "tag_name": release_data["tag_name"],
                    "body": release_data.get("body", ""),
                    "assets": release_data["assets"]
                }
            return None
        
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None

    @staticmethod
    def find_update_asset(assets: list) -> Optional[str]:
        for asset in assets:
            name = asset["name"].lower()
            if "casual-preloader" in name and name.endswith(".zip"):
                return asset["browser_download_url"]
        
        return None

    @staticmethod
    def download_file(url: str, dest_path: Path) -> bool:
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True

        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    def _use_windows_updater(self, zip_path: Path, updater_path: Path):
        import subprocess
        import os

        # rename cuz python will delete temp files on close
        zip_in_install = self.install_dir / "update.zip"
        shutil.copy2(zip_path, zip_in_install)

        # rename updater to avoid file lock issues
        renamed_updater = self.install_dir / "core" / f"updater_old.bat"
        shutil.copy2(updater_path, renamed_updater)

        # launch renamed updater process with our PID so it can kill us
        subprocess.Popen([
            str(renamed_updater),
            str(zip_in_install),
            str(self.install_dir.parent),
            str(os.getpid())
        ], creationflags=subprocess.CREATE_NEW_CONSOLE)

        return True

    def extract_update_zip(self, zip_path: Path) -> bool:
        try:
            if platform.system() == "Windows":
                updater_path = self.install_dir / "core" / "updater.bat"
                if updater_path.exists():
                    return self._use_windows_updater(zip_path, updater_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                temp_extract_dir = self.install_dir / "temp_update"
                temp_extract_dir.mkdir(exist_ok=True)
                zip_ref.extractall(temp_extract_dir)
                
                # nested app folder (casual-preloader-light/casual-preloader)
                app_folder = None
                for item in temp_extract_dir.rglob("*"):
                    if item.is_dir() and item.name == "casual-preloader":
                        app_folder = item
                        break
                
                if app_folder and app_folder.exists():
                    for item in app_folder.iterdir():
                        dest = self.install_dir / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                else:
                    raise FileNotFoundError

                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            
            return True
        
        except Exception as e:
            print(f"Error extracting update: {e}")
            return False
    
    def update_application(self, update_url: str) -> bool:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            print("Downloading application update...")
            if not AutoUpdater.download_file(update_url, tmp_path):
                return False
            
            print("Extracting update...")
            success = self.extract_update_zip(tmp_path)
            
            tmp_path.unlink()
            return success
        
        except Exception as e:
            print(f"Error updating application: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            return False

    def perform_update(self) -> Dict[str, Any]:
        result = {
            "update_available": False,
            "app_updated": False,
            "version": None,
            "error": None
        }
        
        try:
            update_info = self.check_for_updates()
            if not update_info:
                return result
            
            result["update_available"] = True
            result["version"] = update_info["version"]

            app_update_url = AutoUpdater.find_update_asset(update_info["assets"])
            if app_update_url:
                result["app_updated"] = self.update_application(app_update_url)
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


def check_for_updates_sync() -> Optional[Dict[str, Any]]:
    updater = AutoUpdater()
    return updater.check_for_updates()


def perform_update_sync() -> Dict[str, Any]:
    updater = AutoUpdater()
    return updater.perform_update()

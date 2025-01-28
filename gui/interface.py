import zipfile
import random
import vpk
from pathlib import Path
from typing import Set, List
from PyQt6.QtCore import QObject, pyqtSignal
from core.constants import CUSTOM_VPK_NAMES
from core.folder_setup import folder_setup
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from operations.game_type import replace_game_type
from tools.backup_manager import BackupManager
from tools.pcf_squish import ParticleMerger


class ParticleOperations(QObject):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)
    phase_signal = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.total_phases = 3
        self.current_phase = 0

    def update_phase(self, phase_name: str):
        self.current_phase += 1
        progress = (self.current_phase / self.total_phases) * 100
        self.phase_signal.emit(phase_name)
        self.progress_signal.emit(int(progress), phase_name)

    def update_phase_progress(self, progress, message):
        # calculate overall progress based on current phase
        phase_size = 100 / self.total_phases
        overall_progress = (self.current_phase * phase_size) + (progress * phase_size / 100)
        self.progress_signal.emit(int(overall_progress), message)

    def install_preset(self, tf_path: str, preset_name: str, selected_files: Set[str], selected_addons: List[str]):
        try:
            self.current_phase = 0
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(tf_path)

            if not backup_manager.create_initial_backup():
                self.error_signal.emit("Failed to create/verify backup")
                return

            if not backup_manager.prepare_working_copy():
                self.error_signal.emit("Failed to prepare working copy")
                return

            # extract preset based on selection
            preset_path = Path("presets") / f"{preset_name}.zip"
            with zipfile.ZipFile(preset_path, 'r') as zip_ref:
                all_files = zip_ref.namelist()

                if not selected_files:  # "none" state - skip PCF files
                    selected_paths = [
                        path for path in all_files
                        if not path.endswith('.pcf')
                    ]
                else:  # "default" or "custom" state
                    selected_paths = [
                        path for path in all_files
                        if path.endswith('.pcf') and path.split('/')[-1] in selected_files
                           or not path.endswith('.pcf')
                    ]

                for file in selected_paths:
                    zip_ref.extract(file, folder_setup.mods_dir)

            # extract selected addons
            for addon_name in selected_addons:
                addon_path = Path("addons") / f"{addon_name}.zip"
                if addon_path.exists():
                    with zipfile.ZipFile(addon_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            zip_ref.extract(file, folder_setup.mods_everything_else_dir)

            working_vpk_path = backup_manager.get_working_vpk_path()
            vpk_handler = VPKHandler(str(working_vpk_path))
            file_handler = FileHandler(vpk_handler)

            # phase 1: ParticleMerger
            self.phase_signal.emit("Merge Particles...")
            particle_merger = ParticleMerger(file_handler, vpk_handler, lambda p, m: self.update_phase_progress(p, m))
            particle_merger.process()

            # phase 2: Clean Particle Roots
            self.update_phase("Cleaning Up Particle Roots")
            excluded_patterns = ['dx80', 'dx90', 'default', 'unusual', 'test', '_high', '_slow',
                                  'smoke_blackbillow', "level_fx", "_dev", "dxhr_fx", "drg_engineer", "drg_bison",
                                  "halloween", "crit", "speech"]
            # "dxhr_fx", "drg_engineer", "drg_bison", "halloween", "crit", "taunt_fx", "speech" dx81??? idk

            pcf_files = [f for f in file_handler.list_pcf_files()
                         if not any(pattern in f.lower() for pattern in excluded_patterns)]
            for i, file in enumerate(pcf_files):
                base_name = Path(file).name
                progress = (i / len(pcf_files)) * 100
                self.update_phase_progress(progress, f"Processing {Path(file).name}")
                file_handler.process_file(
                    base_name,
                    pcf_empty_root_processor(),
                    create_backup=False
                )

            # phase 3: Mod Processing
            self.update_phase("Mod Processing")
            squished_files = list(folder_setup.output_dir.glob('*.pcf'))
            for i, squished_pcf in enumerate(squished_files):
                base_name = squished_pcf.name
                progress = (i / len(squished_files)) * 100
                self.update_phase_progress(progress, f"Sending Client Info...")
                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(squished_pcf)),
                    create_backup=False
                )

            # deployment
            self.update_phase_progress(100, f"Sending Client Info...")
            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to deploy to game directory")
                return

            # handle custom folder
            if folder_setup.mods_everything_else_dir.exists():
                replace_game_type(Path(tf_path) / 'gameinfo.txt', uninstall=False)
                custom_dir = Path(tf_path) / 'custom'
                custom_dir.mkdir(exist_ok=True)

                for custom_vpk in CUSTOM_VPK_NAMES:
                    vpk_path = custom_dir / custom_vpk
                    cache_path = custom_dir / (custom_vpk + ".sound.cache")
                    if vpk_path.exists():
                        vpk_path.unlink()
                    if cache_path.exists():
                        cache_path.unlink()

                new_pak = vpk.new(str(folder_setup.mods_everything_else_dir))
                new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

            self.progress_signal.emit(100, "Installation complete")
            self.success_signal.emit("Preset installed successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred: {str(e)}")
        finally:
            folder_setup.cleanup_temp_folders()
            self.current_phase = 0
            self.progress_signal.emit(0, "")
            self.operation_finished.emit()

    def restore_backup(self, tf_path: str):
        try:
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(tf_path)

            if not backup_manager.prepare_working_copy():
                self.error_signal.emit("Failed to prepare working copy")
                return

            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to restore backup")
                return

            replace_game_type(Path(tf_path) / 'gameinfo.txt', uninstall=True)
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)

            for custom_vpk in CUSTOM_VPK_NAMES:
                vpk_path = custom_dir / custom_vpk
                cache_path = custom_dir / (custom_vpk + ".sound.cache")
                if vpk_path.exists():
                    vpk_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()

            self.success_signal.emit("Backup restored successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred while restoring backup: {str(e)}")
        finally:
            folder_setup.cleanup_temp_folders()
            self.operation_finished.emit()
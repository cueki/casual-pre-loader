import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile
from pathlib import Path
import random
import threading
import vpk
from core.constants import CUSTOM_VPK_NAMES
from core.folder_setup import folder_setup
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from operations.game_type import replace_game_type
from tools.backup_manager import BackupManager
from tools.pcf_squish import ParticleMerger


class ProgressRedirector:
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        self.queue.put(("message", text))

    def flush(self):
        pass


class ParticleManagerGUI:
    def __init__(self, root):
        self.restore_button = None
        self.install_button = None
        self.browse_button = None
        self.presets_listbox = None
        self.progress_bar = None
        self.status_label = None

        self.root = root
        self.root.title("cukei's custom casual particle pre-loader :)")
        self.root.geometry("800x370")

        # variables
        self.tf_path = tk.StringVar()
        self.selected_preset = tk.StringVar()
        self.processing = False

        self.create_widgets()
        self.load_presets()

        self.current_phase = ""
        self.total_phases = 4  # ParticleMerger, Empty Root, Mod Processing, Deployment
        self.current_phase_number = 0


    def create_widgets(self):
        # main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # top section (directory + presets)
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", padx=5, pady=5)

        # tf directory Selection
        tf_frame = ttk.LabelFrame(top_frame, text="tf/ Directory", padding="5")
        tf_frame.pack(fill="x", padx=5, pady=5)

        ttk.Entry(tf_frame, textvariable=self.tf_path, width=80).pack(side="left", padx=5)
        self.browse_button = ttk.Button(tf_frame, text="Browse", command=self.browse_tf_dir)
        self.browse_button.pack(side="left", padx=5)

        # presets Selection
        presets_frame = ttk.LabelFrame(main_frame, text="Available Presets", padding="5")
        presets_frame.pack(fill="x", padx=5, pady=5)

        self.presets_listbox = tk.Listbox(presets_frame, selectmode=tk.SINGLE, height=5)
        self.presets_listbox.pack(fill="x", padx=5, pady=5)

        # buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        self.install_button = ttk.Button(button_frame, text="Install Selected Preset",
                                       command=self.start_install_thread)
        self.install_button.pack(side="left", padx=5)

        self.restore_button = ttk.Button(button_frame, text="Restore Backup",
                                       command=self.start_restore_thread)
        self.restore_button.pack(side="left", padx=5)

        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        self.status_label = ttk.Label(progress_frame, text="")
        self.status_label.pack(fill="x", padx=5)

    def update_progress(self, progress, message=""):
        def update():
            # Calculate overall progress based on current phase
            overall_progress = ((self.current_phase_number * 100) + progress) / self.total_phases
            self.progress_bar['value'] = overall_progress
            status_text = f"Phase {self.current_phase_number + 1}/{self.total_phases}: {self.current_phase}\n{message}"
            self.status_label['text'] = status_text
            self.root.update_idletasks()

        self.root.after(0, update)

    def update_phase(self, phase_name):
        self.current_phase = phase_name
        self.current_phase_number += 1
        self.update_progress(0, f"Starting {phase_name}")

    def set_processing_state(self, processing: bool):
        # enable/disable buttons and update progress bar based on processing state
        self.processing = processing
        state = "disabled" if processing else "normal"
        self.browse_button.configure(state=state)
        self.install_button.configure(state=state)
        self.restore_button.configure(state=state)
        self.presets_listbox.configure(state=state)

    def start_install_thread(self):
        if not self.validate_inputs():
            return

        self.set_processing_state(True)
        thread = threading.Thread(target=self.install_preset)
        thread.daemon = True
        thread.start()

    def start_restore_thread(self):
        if not self.tf_path.get():
            messagebox.showerror("Error", "Please select tf/ directory!")
            return

        self.set_processing_state(True)
        thread = threading.Thread(target=self.restore_backup)
        thread.daemon = True
        thread.start()

    def browse_tf_dir(self):
        directory = filedialog.askdirectory(title="Select tf/ Directory")
        if directory:
            self.tf_path.set(directory)

    def load_presets(self):
        presets_dir = Path("presets")
        if not presets_dir.exists():
            messagebox.showerror("Error", "Presets directory not found!")
            return

        self.presets_listbox.delete(0, tk.END)
        for preset in presets_dir.glob("*.zip"):
            self.presets_listbox.insert(tk.END, preset.stem)

    def validate_inputs(self):
        if not self.tf_path.get():
            messagebox.showerror("Error", "Please select tf/ directory!")
            return False

        if not Path(self.tf_path.get()).exists():
            messagebox.showerror("Error", "Selected TF2 directory does not exist!")
            return False

        selection = self.presets_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a preset!")
            return False

        return True

    def install_preset(self):
        try:
            self.current_phase_number = 0
            self.current_phase = "Initialization"
            self.update_progress(0, "Starting installation...")

            # initialize backup manager with selected tf directory
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(self.tf_path.get())

            # create initial backup if it doesn't exist
            if not backup_manager.create_initial_backup():
                self.root.after(0, messagebox.showerror, "Error", "Failed to create/verify backup")
                return

            # prepare fresh working copy from backup
            if not backup_manager.prepare_working_copy():
                self.root.after(0, messagebox.showerror, "Error", "Failed to prepare working copy")
                return

            # extract selected preset
            selected_preset = self.presets_listbox.get(self.presets_listbox.curselection())
            preset_path = Path("presets") / f"{selected_preset}.zip"

            output_dir = folder_setup.mods_dir
            with zipfile.ZipFile(preset_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)

            working_vpk_path = backup_manager.get_working_vpk_path()

            # initialize handlers
            vpk_handler = VPKHandler(str(working_vpk_path))
            file_handler = FileHandler(vpk_handler)

            # phase 1: ParticleMerger
            self.update_phase("Squishing Particle Files")
            particle_merger = ParticleMerger(file_handler, vpk_handler, progress_callback=self.update_progress)
            particle_merger.process()

            # phase 2:
            self.update_phase("Cleaning Up Particle Roots")
            excluded_patterns = ['dx80', 'default', 'unusual', 'test']
            pcf_files = [f for f in file_handler.list_pcf_files()
                         if not any(pattern in f.lower() for pattern in excluded_patterns)]

            for i, file in enumerate(pcf_files):
                base_name = Path(file).name
                progress = (i / len(pcf_files)) * 100
                self.update_progress(progress, f"Processing {base_name}")
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
                self.update_progress(progress, f"Processing {base_name}")

                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(squished_pcf)),
                    create_backup=False
                )

            # phase 4: Final Deployment
            self.update_phase("Deployment")
            if not backup_manager.deploy_to_game():
                self.root.after(0, messagebox.showerror, "Error", "Failed to deploy to game directory")
                return
            self.update_progress(100, "Deployment complete")

            # handle custom folder
            if folder_setup.mods_everything_else_dir.exists():
                replace_game_type(Path(self.tf_path.get()) / 'gameinfo.txt')
                custom_dir = Path(self.tf_path.get()) / 'custom'
                custom_dir.mkdir(exist_ok=True)
                for custom_vpk in CUSTOM_VPK_NAMES:
                    if (custom_dir / custom_vpk).exists():
                        os.remove(custom_dir / custom_vpk)
                new_pak = vpk.new(str(folder_setup.mods_everything_else_dir))
                new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

            self.root.after(0, messagebox.showinfo, "Success", "Preset installed successfully!")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")
        finally:
            folder_setup.cleanup_temp_folders()
            self.root.after(0, self.set_processing_state, False)
            # Reset progress tracking
            self.current_phase_number = 0
            self.current_phase = ""
            self.root.after(0, self.update_progress, 0, "")

    def restore_backup(self):
        try:
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(self.tf_path.get())

            # make copy from backup... to do nothing with... whatever man...
            if not backup_manager.prepare_working_copy():
                self.root.after(0, messagebox.showerror, "Error", "Failed to prepare working copy")
                return

            # skip the whole process and only copy backup to game dir
            if not backup_manager.deploy_to_game():
                self.root.after(0, messagebox.showerror, "Error", "Failed to restore backup")
                return

            self.root.after(0, messagebox.showinfo, "Success", "Backup restored successfully!")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error",
                            f"An error occurred while restoring backup: {str(e)}")
        finally:
            self.root.after(0, self.set_processing_state, False)
            folder_setup.cleanup_temp_folders()


def main():
    root = tk.Tk()
    ParticleManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
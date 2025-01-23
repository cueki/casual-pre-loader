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
from gui_stuff.preset_customizer import PresetCustomizer, PresetSelectionManager
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
        self.root = root
        self.root.title("cukei's custom casual particle pre-loader :)")
        self.root.geometry("800x370")

        # Initialize selection manager
        self.selection_manager = PresetSelectionManager()

        # variables
        self.tf_path = tk.StringVar()
        self.selected_preset_files = set()
        self.processing = False

        self.create_widgets()
        self.load_presets()

        # Load last used directory if available
        self.load_last_directory()

        self.current_phase = ""
        self.total_phases = 4  # ParticleMerger, Empty Root, Mod Processing, Deployment
        self.current_phase_number = 0

        self.selected_preset_files = set()

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

        preset_controls = ttk.Frame(presets_frame)
        preset_controls.pack(fill="x", padx=5, pady=5)

        self.customize_button = ttk.Button(
            preset_controls,
            text="Customize Selected Preset",
            command=self.open_customizer,
            state="disabled"
        )
        self.customize_button.pack(side="right", padx=5)

        # Add presets listbox
        self.presets_listbox = tk.Listbox(presets_frame, selectmode=tk.SINGLE, height=5)
        self.presets_listbox.pack(fill="x", padx=5, pady=5)
        self.presets_listbox.bind('<<ListboxSelect>>', self.on_preset_select)

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

    def load_last_directory(self):
        try:
            if Path("last_directory.txt").exists():
                with open("last_directory.txt", "r") as f:
                    last_dir = f.read().strip()
                    if Path(last_dir).exists():
                        self.tf_path.set(last_dir)
        except Exception as e:
            print(f"Error loading last directory: {e}")

    def save_last_directory(self):
        try:
            with open("last_directory.txt", "w") as f:
                f.write(self.tf_path.get())
        except Exception as e:
            print(f"Error saving last directory: {e}")

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
            self.save_last_directory()

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

    def on_preset_select(self, event=None):
        selection = self.presets_listbox.curselection()
        if selection:
            selected_preset = self.presets_listbox.get(selection[0])
            self.selected_preset_files = self.selection_manager.get_selection(selected_preset)
            self.customize_button.config(state="normal")

            # Update install button text if there's a saved selection
            if self.selected_preset_files:
                self.install_button.config(text=f"Install Selected Files ({len(self.selected_preset_files)})")
            else:
                self.install_button.config(text="Install Selected Preset")
        else:
            self.customize_button.config(state="disabled")
            self.install_button.config(text="Install Selected Preset")

    def open_customizer(self):
        selection = self.presets_listbox.curselection()
        if not selection:
            return

        selected_preset = self.presets_listbox.get(selection[0])

        # Load any existing selection
        self.selected_preset_files = self.selection_manager.get_selection(selected_preset)

        # Open customizer with selection manager
        customizer = PresetCustomizer(self.root, selected_preset, self.selection_manager)
        self.root.wait_window(customizer)

        # Update install button state based on selection
        if self.selected_preset_files:
            self.install_button.config(text=f"Install Selected Files ({len(self.selected_preset_files)})")
        else:
            self.install_button.config(text="Install Selected Preset")

    def install_preset(self):
        try:
            if not self.validate_inputs():
                return

            selected_preset = self.presets_listbox.get(self.presets_listbox.curselection())

            # If we have selected files, verify with user
            if self.selected_preset_files:
                message = f"Installing {len(self.selected_preset_files)} selected files from preset '{selected_preset}'"
                if not messagebox.askyesno("Confirm Installation", f"{message}. Continue?"):
                    return
            else:
                message = f"Installing all files from preset '{selected_preset}'"
                if not messagebox.askyesno("Confirm Installation", f"{message}. Continue?"):
                    return

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

            with zipfile.ZipFile(preset_path, 'r') as zip_ref:
                if self.selected_preset_files:
                    # Extract only selected files
                    all_files = zip_ref.namelist()
                    selected_paths = [
                        path for path in all_files
                        if path.endswith('.pcf') and
                           path.split('/')[-1] in self.selected_preset_files
                    ]
                    for file in selected_paths:
                        zip_ref.extract(file, folder_setup.mods_dir)
                else:
                    # Extract all files
                    zip_ref.extractall(folder_setup.mods_dir)

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
                    if (custom_dir / Path(custom_vpk + "sound.cache")).exists():
                        os.remove(custom_dir / Path(custom_vpk + "sound.cache"))
                new_pak = vpk.new(str(folder_setup.mods_everything_else_dir))
                new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

            self.root.after(0, messagebox.showinfo, "Success", "Preset installed successfully!")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")
        finally:
            folder_setup.cleanup_temp_folders()
            self.root.after(0, self.set_processing_state, False)
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

            custom_dir = Path(self.tf_path.get()) / 'custom'
            custom_dir.mkdir(exist_ok=True)
            for custom_vpk in CUSTOM_VPK_NAMES:
                if (custom_dir / custom_vpk).exists():
                    os.remove(custom_dir / custom_vpk)
                if (custom_dir / Path(custom_vpk + "sound.cache")).exists():
                    os.remove(custom_dir / Path(custom_vpk + "sound.cache"))

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
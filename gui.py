import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import zipfile
from pathlib import Path
import random
import threading
import queue
import vpk
from core.constants import CUSTOM_VPK_NAMES
from core.folder_setup import folder_setup
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from operations.game_type import replace_game_type
from tools.backup_manager import BackupManager
from tools.pcf_squish import ParticleMerger


class ConsoleRedirector:
    def __init__(self, widget, queue):
        self.widget = widget
        self.queue = queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


class ParticleManagerGUI:
    def __init__(self, root):
        self.presets_listbox = None
        self.root = root
        self.root.title("Particle System Manager")
        self.root.geometry("800x600")

        # Variables
        self.tf_path = tk.StringVar()
        self.selected_preset = tk.StringVar()
        self.processing = False
        self.console_queue = queue.Queue()

        self.create_widgets()
        self.load_presets()

        # Start the console update loop
        self.update_console()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Top section (Directory + Presets)
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", padx=5, pady=5)

        # TF2 Directory Selection
        tf_frame = ttk.LabelFrame(top_frame, text="TF2 Directory", padding="5")
        tf_frame.pack(fill="x", padx=5, pady=5)

        ttk.Entry(tf_frame, textvariable=self.tf_path, width=50).pack(side="left", padx=5)
        self.browse_button = ttk.Button(tf_frame, text="Browse", command=self.browse_tf_dir)
        self.browse_button.pack(side="left", padx=5)

        # Presets Selection
        presets_frame = ttk.LabelFrame(main_frame, text="Available Presets", padding="5")
        presets_frame.pack(fill="x", padx=5, pady=5)

        self.presets_listbox = tk.Listbox(presets_frame, selectmode=tk.SINGLE, height=5)
        self.presets_listbox.pack(fill="x", padx=5, pady=5)

        # Console Output
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.console_output = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=15)
        self.console_output.pack(fill="both", expand=True, padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        self.install_button = ttk.Button(button_frame, text="Install Selected Preset",
                                         command=self.start_install_thread)
        self.install_button.pack(side="left", padx=5)

        self.restore_button = ttk.Button(button_frame, text="Restore Backup",
                                         command=self.start_restore_thread)
        self.restore_button.pack(side="left", padx=5)

        self.exit_button = ttk.Button(button_frame, text="Exit", command=self.root.quit)
        self.exit_button.pack(side="right", padx=5)

        # Redirect stdout to our console
        sys.stdout = ConsoleRedirector(self.console_output, self.console_queue)

    def update_console(self):
        """Update the console with any new output"""
        while True:
            try:
                text = self.console_queue.get_nowait()
                self.console_output.insert(tk.END, text)
                self.console_output.see(tk.END)
                self.console_output.update_idletasks()
            except queue.Empty:
                break
        self.root.after(100, self.update_console)

    def set_processing_state(self, processing: bool):
        """Enable/disable buttons based on processing state"""
        self.processing = processing
        state = "disabled" if processing else "normal"
        self.browse_button.configure(state=state)
        self.install_button.configure(state=state)
        self.restore_button.configure(state=state)
        self.presets_listbox.configure(state=state)

    def start_install_thread(self):
        """Start installation in a separate thread"""
        if not self.validate_inputs():
            return

        self.set_processing_state(True)
        thread = threading.Thread(target=self.install_preset)
        thread.daemon = True
        thread.start()

    def start_restore_thread(self):
        """Start restore in a separate thread"""
        if not self.tf_path.get():
            messagebox.showerror("Error", "Please select TF2 tf/ directory!")
            return

        self.set_processing_state(True)
        thread = threading.Thread(target=self.restore_backup)
        thread.daemon = True
        thread.start()

    def browse_tf_dir(self):
        directory = filedialog.askdirectory(title="Select TF2 tf/ Directory")
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
            messagebox.showerror("Error", "Please select TF2 tf/ directory!")
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
            # Initialize backup manager with selected tf directory
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(self.tf_path.get())

            # Create initial backup if it doesn't exist
            if not backup_manager.create_initial_backup():
                self.root.after(0, messagebox.showerror, "Error", "Failed to create/verify backup")
                return

            # Prepare fresh working copy from backup
            if not backup_manager.prepare_working_copy():
                self.root.after(0, messagebox.showerror, "Error", "Failed to prepare working copy")
                return

            # Extract selected preset
            selected_preset = self.presets_listbox.get(self.presets_listbox.curselection())
            preset_path = Path("presets") / f"{selected_preset}.zip"

            output_dir = folder_setup.mods_dir
            with zipfile.ZipFile(preset_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)

            working_vpk_path = backup_manager.get_working_vpk_path()

            # Initialize handlers
            vpk_handler = VPKHandler(str(working_vpk_path))
            file_handler = FileHandler(vpk_handler)

            # Process files
            ParticleMerger(file_handler, vpk_handler).process()

            excluded_patterns = ['dx80', 'default', 'unusual', 'test']
            for file in file_handler.list_pcf_files():
                if not any(pattern in file.lower() for pattern in excluded_patterns):
                    base_name = Path(file).name
                    file_handler.process_file(
                        base_name,
                        pcf_empty_root_processor(),
                        create_backup=False
                    )

            # Compress and deploy mod files
            squished_files = folder_setup.output_dir.glob('*.pcf')
            for squished_pcf in squished_files:
                base_name = squished_pcf.name
                print(f"Processing mod: {base_name}")
                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(squished_pcf)),
                    create_backup=False
                )

            if not backup_manager.deploy_to_game():
                self.root.after(0, messagebox.showerror, "Error", "Failed to deploy to game directory")
                return

            # Handle custom folder
            if folder_setup.mods_everything_else_dir.exists():
                replace_game_type(Path(self.tf_path.get()) / 'gameinfo.txt')
                custom_dir = Path(self.tf_path.get()) / 'custom'
                custom_dir.mkdir(exist_ok=True)
                for custom_vpk in CUSTOM_VPK_NAMES:
                    if (custom_dir / custom_vpk).exists():
                        os.remove(custom_dir / custom_vpk)
                new_pak = vpk.new(str(folder_setup.mods_everything_else_dir))
                new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

            folder_setup.cleanup_temp_folders()
            self.root.after(0, messagebox.showinfo, "Success", "Preset installed successfully!")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")
        finally:
            self.root.after(0, self.set_processing_state, False)

    def restore_backup(self):
        try:
            backup_manager = BackupManager(self.tf_path.get())

            # Skip the whole process and only copy backup to game dir
            if not backup_manager.deploy_to_game():
                self.root.after(0, messagebox.showerror, "Error", "Failed to restore backup")
                return

            self.root.after(0, messagebox.showinfo, "Success", "Backup restored successfully!")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error",
                            f"An error occurred while restoring backup: {str(e)}")
        finally:
            self.root.after(0, self.set_processing_state, False)


def main():
    root = tk.Tk()
    ParticleManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
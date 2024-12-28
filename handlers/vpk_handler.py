from typing import Optional, Tuple, List, Iterator
from models.vpk_file import VPKParser, VPKDirectoryEntry
from pathlib import Path
import os


class VPKHandler:
    def __init__(self, vpk_path: str):
        """Initialize VPK handler with path to VPK file"""
        # Convert to _dir.vpk path if needed
        if not vpk_path.endswith('_dir.vpk'):
            vpk_path = str(Path(vpk_path).with_suffix('')).rsplit('_', 1)[0] + '_dir.vpk'

        self.dir_path = vpk_path
        self.base_path = vpk_path[:-8]  # Remove "_dir.vpk"
        self.vpk_parser = VPKParser(vpk_path)
        self.vpk_parser.parse_directory()

    def list_extensions(self) -> List[str]:
        """Get all file extensions in the VPK"""
        return list(self.vpk_parser.directory.keys())

    def list_paths_for_extension(self, extension: str) -> List[str]:
        """Get all paths that contain files of a given extension"""
        if extension not in self.vpk_parser.directory:
            return []
        return list(self.vpk_parser.directory[extension].keys())

    def list_files(self, extension: Optional[str] = None, path: Optional[str] = None) -> List[str]:
        """
        List files in the VPK, optionally filtered by extension and/or path.
        Returns full file paths including extension.
        """
        files = []

        # If extension specified, only look in that extension's directory
        extensions = [extension] if extension else self.vpk_parser.directory.keys()

        for ext in extensions:
            if ext not in self.vpk_parser.directory:
                continue

            # If path specified, only look in that path
            paths = [path] if path else self.vpk_parser.directory[ext].keys()

            for p in paths:
                if p not in self.vpk_parser.directory[ext]:
                    continue

                for filename in self.vpk_parser.directory[ext][p]:
                    full_path = f"{p}/{filename}.{ext}" if p else f"{filename}.{ext}"
                    files.append(full_path)

        return files

    def find_files(self, pattern: str) -> List[str]:
        # Find files matching a glob pattern (e.g., '*.pcf', 'materials/*.vmt')
        all_files = self.list_files()
        return [f for f in all_files if Path(f).match(pattern)]

    def find_file_path(self, filename: str) -> Optional[str]:
        # Find the full internal VPK path for a file given just its name.
        # e.g., 'explosion.pcf' -> 'particles/explosion.pcf'

        # Extract extension from filename
        try:
            name, ext = filename.rsplit('.', 1)
        except ValueError:
            return None

        # Check if this extension exists in VPK
        if ext not in self.vpk_parser.directory:
            return None

        # Search through all paths for this file
        for path in self.vpk_parser.directory[ext]:
            if name in self.vpk_parser.directory[ext][path]:
                return f"{path}/{filename}" if path else filename

        return None

    def get_file_entry(self, filepath: str) -> Optional[Tuple[str, str, VPKDirectoryEntry]]:
        """Get VPK entry for a file given its full path"""
        try:
            # Split path into components
            path = Path(filepath)
            extension = path.suffix[1:]  # Remove the dot
            filename = path.stem
            directory = str(path.parent)

            # Clean up directory path
            if directory == '.':
                directory = ''

            # Check if file exists in VPK
            if (extension in self.vpk_parser.directory and
                    directory in self.vpk_parser.directory[extension] and
                    filename in self.vpk_parser.directory[extension][directory]):
                return extension, directory, self.vpk_parser.directory[extension][directory][filename]

        except (AttributeError, KeyError):
            pass
        return None

    def get_archive_path(self, archive_index: int) -> str:
        """Get the path to a specific VPK archive file"""
        if archive_index == 0x7fff:
            return self.dir_path
        return f"{self.base_path}_{archive_index:03d}.vpk"

    def read_from_archive(self, archive_index: int, offset: int, size: int) -> Optional[bytes]:
        """Read data from a specific VPK archive"""
        archive_path = self.get_archive_path(archive_index)
        try:
            with open(archive_path, 'rb') as f:
                f.seek(offset)
                return f.read(size)
        except (IOError, OSError) as e:
            print(f"Error reading from archive {archive_path}: {e}")
            return None

    def extract_file(self, filepath: str, output_path: str) -> bool:
        """Extract a file from the VPK to the specified output path"""
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        extension, directory, entry = entry_info

        try:
            # Read from appropriate archive
            file_data = self.read_from_archive(
                entry.archive_index,
                entry.entry_offset,
                entry.entry_length
            )

            if not file_data:
                return False

            # Write to output file
            with open(output_path, 'wb') as f:
                # Write preload data if it exists
                if entry.preload_bytes > 0 and entry.preload_data:
                    f.write(entry.preload_data)
                # Write main file data
                f.write(file_data)

            return True

        except Exception as e:
            print(f"Error extracting file: {e}")
            return False

    def patch_file(self, filepath: str, new_data: bytes, create_backup: bool = True) -> bool:
        """Patch a file in the VPK with new data"""
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        _, _, entry = entry_info

        try:
            # Verify size
            if len(new_data) > entry.entry_length:
                raise ValueError(
                    f"Modified file is larger than original "
                    f"({len(new_data)} > {entry.entry_length} bytes)"
                )

            # Get the correct VPK archive path
            archive_path = self.get_archive_path(entry.archive_index)

            # Create backup if requested
            if create_backup:
                backup_path = f"{archive_path}.backup"
                if not os.path.exists(backup_path):
                    with open(archive_path, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())

            # Write the modified data
            with open(archive_path, 'rb+') as f:
                f.seek(entry.entry_offset)
                f.write(new_data)
                # Pad with nulls if smaller
                if len(new_data) < entry.entry_length:
                    f.write(b'\x00' * (entry.entry_length - len(new_data)))

            return True

        except Exception as e:
            print(f"Error patching file: {e}")
            return False

    def iter_files(self, pattern: Optional[str] = None) -> Iterator[Tuple[str, bytes]]:
        """
        Iterate over files in the VPK, yielding (filepath, content) pairs.
        Optionally filter by glob pattern.
        """
        files = self.find_files(pattern) if pattern else self.list_files()

        for filepath in files:
            entry_info = self.get_file_entry(filepath)
            if not entry_info:
                continue

            _, _, entry = entry_info

            # Read file data from appropriate archive
            file_data = self.read_from_archive(
                entry.archive_index,
                entry.entry_offset,
                entry.entry_length
            )

            if file_data:
                # Combine preload data if it exists
                if entry.preload_bytes > 0 and entry.preload_data:
                    file_data = entry.preload_data + file_data
                yield filepath, file_data

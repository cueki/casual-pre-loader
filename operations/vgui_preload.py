from pathlib import Path
from core.parsers.vpk_file import VPKFile


def patch_mainmenuoverride(tf_path: str):
    custom_dir = Path(tf_path) / 'custom'
    if not custom_dir.exists():
        return

    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue
        # VPK files will convert to folders first before we process folders
        if (item.is_file() and
              item.suffix.lower() == ".vpk" and
              "casual_preloader" not in item.name.lower()):
            print(f"Patching VPK {item.name}")
            _process_vpk(item)

        elif item.is_dir():
            mainmenuoverride_file = item / "resource" / "ui" / "mainmenuoverride.res"
            if mainmenuoverride_file.exists():
                print(f"Patching file {item.name}")
                _add_vguipreload_string(mainmenuoverride_file)


def _add_vguipreload_string(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if "vguipreload.res" not in content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('#base "vguipreload.res"\n' + content)
            return True
    except Exception as e:
        print(e)


def _process_vpk(vpk_path):
    try:
        vpk_file = VPKFile(str(vpk_path))
        vpk_file.parse_directory()
        target_files = vpk_file.find_files("resource/ui/mainmenuoverride.res")
        # skip if no mainmenuoverride.res
        if not target_files:
            return

        custom_dir = vpk_path.parent
        vpk_name = vpk_path.stem
        extract_dir = custom_dir / vpk_name
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"Extracting {vpk_path} to {extract_dir}")

        file_list = vpk_file.list_files()
        for file_path in file_list:
            out_path = extract_dir / file_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            vpk_file.extract_file(file_path, str(out_path))

        print(f"Successfully extracted {len(file_list)} files from {vpk_path}")

        # delete the original VPK file
        vpk_path.unlink()
        print(f"Deleted original VPK: {vpk_path}")

    except Exception as e:
        print(f"Error extracting VPK {vpk_path}: {e}")
        import traceback
        traceback.print_exc()

import PyInstaller.__main__
import os
from pathlib import Path

# just a generator so I don't need two files to build

def create_executable():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collect all Python files
python_files = [
    ('app.py', '.'),
    ('core/constants.py', 'core'),
    ('core/folder_setup.py', 'core'),
    ('handlers/file_handler.py', 'handlers'),
    ('handlers/vpk_handler.py', 'handlers'),
    ('parsers/pcf_file.py', 'parsers'),
    ('parsers/vpk_file.py', 'parsers'),
    ('operations/file_processors.py', 'operations'),
    ('operations/pcf_compress.py', 'operations'),
    ('operations/pcf_merge.py', 'operations'),
    ('operations/game_type.py', 'operations'),
    ('tools/backup_manager.py', 'tools'),
    ('tools/pcf_squish.py', 'tools'),
    ('tools/vpk_unpack.py', 'tools'),
    ('gui/preset_customizer.py', 'gui'),
    ('gui/preset_descriptor.py', 'gui'),
    ('gui/interface.py', 'gui')
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=python_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cukei_particle_preload',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    with open('particle_manager.spec', 'w') as f:
        f.write(spec_content)

    PyInstaller.__main__.run([
        'particle_manager.spec',
        '--clean'
    ])


if __name__ == '__main__':
    create_executable()

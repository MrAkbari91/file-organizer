# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'src/file_organizer/gui/app.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=collect_data_files('customtkinter') + copy_metadata('customtkinter') + [
        (str(root / 'src/file_organizer/gui/assets'), 'file_organizer/gui/assets')],
    hiddenimports=['PIL.Image', 'PIL.ImageTk', 'file_organizer.gui.startup'],
    hookspath=[], hooksconfig={}, runtime_hooks=[str(root / 'packaging/runtime_streams.py')], excludes=['numpy', 'pytest', 'matplotlib'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='File Organizer Pro',
    icon=str(root / ('src/file_organizer/gui/assets/app.icns' if sys.platform == 'darwin' else 'src/file_organizer/gui/assets/app.ico')), debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='File Organizer Pro')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='File Organizer Pro.app',
                 icon=str(root / 'src/file_organizer/gui/assets/app.icns'),
                 bundle_identifier='com.dhruvakbari.fileorganizer',
                 info_plist={'NSHighResolutionCapable': True, 'CFBundleShortVersionString': '0.1.0'})

# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'assets' / 'assistant.gif'), 'assets')],
    hiddenimports=['apscheduler.triggers.interval'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
if sys.platform == 'linux':
    # TIFF is not a supported avatar format. Its optional Qt plugin requires
    # libtiff.so.5, which is absent on Ubuntu 24.04 (the OS ships libtiff.so.6).
    a.binaries = [entry for entry in a.binaries if not entry[0].endswith('/libqtiff.so')]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='DeskBuddy',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DeskBuddy')
if sys.platform == 'darwin':
    bundle = BUNDLE(
        coll, name='DeskBuddy.app', bundle_identifier='com.deskbuddy.desktop',
        info_plist={
            'CFBundleName': 'DeskBuddy',
            'CFBundleShortVersionString': '0.2.0',
            'CFBundleVersion': '2',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '13.0',
            'NSLocalNetworkUsageDescription': 'DeskBuddy connects to your chosen peer to exchange messages and reminders.',
        },
    )

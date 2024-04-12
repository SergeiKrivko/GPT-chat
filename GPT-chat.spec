# -*- mode: python ; coding: utf-8 -*-


import sys


block_cipher = None
lib_path = r"venv\Lib\site-packages" if sys.platform == 'win32' else "venv/lib/python3.11/site-packages"


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('icon.png', '.')],
    datas=[
        (os.path.abspath(f"{lib_path}/PyQtUIkit/fonts"), "PyQtUIkit/fonts"),
        (os.path.abspath("assets"), "assets")
    ],
    hiddenimports=['matplotlib.backends.backend_svg'],
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
    [],
    exclude_binaries=True,
    name='GPT-chat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GPT-chat',
)

app = BUNDLE(coll,
             name='GPT-chat.app',
             icon='icon_mac.png',
             bundle_identifier="com.sergeikrivko.gpt")

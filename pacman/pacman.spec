# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Pac-Man game.
#
# Build a self-contained, double-clickable executable that bundles the Python
# runtime, pygame, the assigned A-Maze-ing package and the default config, so
# the game can be uploaded to a public platform (Itch.io / Steam) and launched
# with no Python install on the player's machine.
#
#   pyinstaller pacman.spec            # or:  ./build.sh
#
# The result is dist/pac-man/ (one-folder build) which is what gets zipped and
# pushed to Itch.io via butler (see build.sh / itch_push.sh).

block_cipher = None

a = Analysis(
    ['pac-man.py'],
    pathex=['.'],
    binaries=[],
    # Ship a default config and the player-facing instructions next to the exe.
    datas=[
        ('config.json', '.'),
        ('INSTRUCTIONS.txt', '.'),
        ('itch.toml', '.'),
    ],
    # mazegenerator is imported lazily inside a try/except, so PyInstaller's
    # static analysis can miss it: pin it explicitly.
    hiddenimports=['mazegenerator', 'mazegenerator.mazegenerator'],
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
    name='pac-man',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # windowed game, no terminal pop-up
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pac-man',
)

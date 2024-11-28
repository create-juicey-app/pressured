# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('fonts/*', 'fonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 
        'numpy', 
        'pandas',
        'PIL._tkinter_finder',
        'matplotlib',
        'PyQt5',
        'PySide2',
        'wx',
        '_ssl',
        'doctest',
        'pdb',
        'unittest',
        'email',
        'html',
        'http',
        'xml',
        'pydoc',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    strip=True,
    upx=False,  # Disabled on Linux
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
)
# StarTools-MMDC.spec
block_cipher = None

a = Analysis(
    ['mmdc.py'],
    pathex=[],
    binaries=[],
    datas=[('startools_mmdc.ico', '.')],  
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StarTools-MMDC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='startools_mmdc.ico'
)

# PyInstaller — build de arquivo unico para Windows
# Uso: pyinstaller mowanettest.spec

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('ui', 'ui'), ('assets', 'assets')],
    hiddenimports=['webview.platforms.edgechromium'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc_data', 'test'],
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
    name='mowanettest',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)

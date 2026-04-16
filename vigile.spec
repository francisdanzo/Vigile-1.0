# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os


project_dir = Path.cwd()
block_cipher = None

datas = [
    (str(project_dir / "web" / "templates"), "web/templates"),
]

static_dir = project_dir / "web" / "static"
if static_dir.exists():
    datas.append((str(static_dir), "web/static"))

cloudflared_env = os.environ.get("VIGILE_CLOUDFLARED_PATH")
if cloudflared_env:
    cloudflared_source = Path(cloudflared_env)
elif os.name == "nt":
    cloudflared_source = project_dir / "tunnel" / "cloudflared.exe"
else:
    cloudflared_source = project_dir / "tunnel" / "cloudflared"

if not cloudflared_source.exists():
    raise SystemExit(
        "Binaire cloudflared manquant. "
        "Placez-le dans 'tunnel/' ou définissez VIGILE_CLOUDFLARED_PATH avant le build."
    )

datas.append((str(cloudflared_source), f"tunnel/{cloudflared_source.name}"))

hiddenimports = [
    "PIL.Image",
    "PIL.ImageTk",
]

a = Analysis(
    ["app.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="Vigile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Vigile",
)

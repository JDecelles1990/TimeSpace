# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for TimeSpace (--onedir, windowed, bundled Go CLI)."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()
GO_BIN = ROOT / "build" / "go_stage" / "diag_windows.exe"
ICON_PATH = ROOT / "assets" / "timespace.ico"

if not GO_BIN.exists():
    raise FileNotFoundError(
        f"Staged Go diagnostic binary not found at '{GO_BIN}'. Run '.\\build.ps1' so Stage 1 compiles it first."
    )

_EXCLUDED_QT_DLL_PREFIXES = (
    "qt6webengine",
    "qt6pdf",
    "qt6quick",
    "qt6qml",
    "qt6multimedia",
    "qt6sql",
    "qt63d",
    "qt6charts",
    "qt6designer",
    "qt6bluetooth",
    "qt6positioning",
    "qt6sensors",
    "qt6serialport",
    "qt6websockets",
    "qt6spatialaudio",
    "qt6texttospeech",
    "qt6remoteobjects",
    "qt6scxml",
    "qt6statemachine",
    "qt6httpserver",
    "qt6graphs",
    "qt6nfc",
    "qt6network",
    "qt6dbus",
    "qt6printsupport",
    "qt6help",
    "qt6test",
)

a = Analysis(
    ["run.py"],
    pathex=[str(ROOT)],
    binaries=[(str(GO_BIN), "bin")],
    datas=[(str(ICON_PATH), "assets")] if ICON_PATH.exists() else [],
    hiddenimports=[
        "pystray._win32",
        "keyboard",
        "keyboard._winkeyboard",
        "winsound",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "_tkinter",
        "unittest",
        "pydoc",
        "doctest",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtQuick3D",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DExtras",
        "PySide6.QtSql",
        "PySide6.QtNetwork",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtCharts",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtTest",
        "PySide6.QtBluetooth",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtWebSockets",
        "PySide6.QtXml",
        "PySide6.QtPrintSupport",
        "PySide6.QtDBus",
        "PySide6.QtGraphs",
        "PySide6.QtHttpServer",
        "PySide6.QtSpatialAudio",
        "PySide6.QtTextToSpeech",
    ],
    noarchive=False,
    optimize=0,
)

# Drop heavy unused Qt DLLs/plugins if pulled transitively
a.binaries = [
    entry
    for entry in a.binaries
    if not Path(entry[0]).name.lower().startswith(_EXCLUDED_QT_DLL_PREFIXES)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TimeSpace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TimeSpace",
)

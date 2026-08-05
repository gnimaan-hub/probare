# -*- mode: python ; coding: utf-8 -*-
"""Recette PyInstaller du moteur Probare.

Produit un exécutable autonome que l'application Electron embarque dans ses
ressources et lance comme sidecar. Le poste du cabinet n'a alors besoin ni de
Python ni des dépendances scientifiques.

Construction : passer par `python build_engine.py`, qui prépare la clé API
intégrée avant d'appeler PyInstaller sur ce fichier.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Modules chargés dynamiquement, qu'une analyse statique ne peut pas voir :
#  - uvicorn/anyio résolvent leurs boucles et protocoles par nom au démarrage ;
#  - encodings.idna est atteint via le résolveur réseau d'httpx (client Anthropic) ;
#  - openpyxl.cell._writer est importé par pandas au moment d'écrire un .xlsx.
# Les modules du moteur ne sont PAS collectés en bloc : `collect_submodules`
# importe réellement chaque module pour l'inspecter, ce qui entraîne ici une
# chaîne vers pywin32 et fait échouer la construction. L'analyse de PyInstaller
# suit de toute façon les imports placés en corps de fonction, dont le moteur
# fait un large usage.
hiddenimports = [
    *collect_submodules("uvicorn"),
    *collect_submodules("anyio"),
    "encodings.idna",
    "openpyxl.cell._writer",
]

# python-docx crée tout document neuf à partir d'un gabarit .docx livré dans
# ses données de paquet : sans elles, la génération des livrables Word échoue à
# l'exécution — et c'est le cœur de ce que Probare produit.
datas = collect_data_files("docx")

a = Analysis(
    ["run_engine.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Pandas déclare de nombreuses intégrations optionnelles (traçage, presse-
    # papiers, bases SQL, systèmes de fichiers distants) que le moteur n'emprunte
    # jamais : aucune n'est importée dans `probare_engine`. Sans ces exclusions,
    # PyInstaller suit ces branches et embarque torch, TensorFlow, SciPy et
    # PIL — plusieurs gigaoctets pour du code mort. `pandas.io.clipboard` tire de
    # plus win32com/pythoncom, dont l'introspection fait échouer la construction.
    excludes=[
        "tkinter", "matplotlib", "PyQt5", "PySide2", "IPython", "pytest",
        "torch", "tensorflow", "scipy", "PIL", "sqlalchemy", "fsspec",
        "win32com", "pythoncom", "pywin32",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="probare_engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Le sidecar ne doit pas ouvrir de fenêtre console derrière l'application.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Mode « onedir » plutôt que « onefile » : un binaire monofichier se dézippe
# dans un répertoire temporaire à CHAQUE démarrage, ce qui ajoute plusieurs
# secondes au lancement de l'application et fait échouer le délai d'attente du
# sidecar sur un poste lent ou sous antivirus.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="engine",
)

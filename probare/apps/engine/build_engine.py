"""Construit l'exécutable du moteur Probare.

Enchaîne trois étapes :

1. Génère `probare_engine/_cle_integree.py` à partir de la clé API disponible
   (variable d'environnement ou `.env` de la racine du dépôt), pour que
   l'application livrée fonctionne sans configuration sur le poste du cabinet.
2. Lance PyInstaller sur `probare_engine.spec`.
3. Recopie le résultat dans `apps/desktop/resources/engine/`, d'où
   electron-builder l'embarquera.

AVERTISSEMENT — la clé intégrée n'est pas un secret : elle est extractible du
binaire livré. Ce mode convient à une démonstration remise à un cabinet
identifié ; la clé doit être révoquée à la fin du test. Lancer avec
`--sans-cle` pour produire un binaire qui exigera une clé d'environnement.

Usage :
    python build_engine.py [--sans-cle]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RACINE_ENGINE = Path(__file__).resolve().parent
RACINE_PROBARE = RACINE_ENGINE.parent.parent
DEST_RESOURCES = RACINE_PROBARE / "apps" / "desktop" / "resources" / "engine"
FICHIER_CLE = RACINE_ENGINE / "probare_engine" / "_cle_integree.py"

# Un binaire construit sans ces modules démarre puis échoue seulement au moment
# de produire un livrable — vérifier leur présence ici évite de découvrir le
# manque devant le client.
MODULES_REQUIS = ("fastapi", "uvicorn", "anthropic", "pandas", "openpyxl", "docx")


def _log(message: str) -> None:
    print(f"[build-engine] {message}", flush=True)


def _echouer(message: str) -> None:
    print(f"[build-engine] ERREUR — {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def verifier_dependances() -> None:
    import importlib.util

    manquants = [m for m in MODULES_REQUIS if importlib.util.find_spec(m) is None]
    if manquants:
        _echouer(
            "modules absents de l'environnement de construction : "
            f"{', '.join(manquants)}. Installez-les avant de construire."
        )
    if importlib.util.find_spec("PyInstaller") is None:
        _echouer("PyInstaller absent. Installez-le : pip install pyinstaller")


def lire_cle() -> str | None:
    """Clé API à intégrer : environnement d'abord, puis `.env` du dépôt."""
    cle = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if cle:
        return cle
    env = RACINE_PROBARE / ".env"
    if env.exists():
        for ligne in env.read_text(encoding="utf-8").splitlines():
            nom, _, valeur = ligne.strip().partition("=")
            if nom.strip() == "ANTHROPIC_API_KEY":
                valeur = valeur.strip().strip('"').strip("'")
                if valeur:
                    return valeur
    return None


def ecrire_cle_integree(cle: str | None) -> None:
    if not cle:
        # Écrire une clé vide plutôt que rien : le module est toujours
        # importable, et cle_api n'a pas à distinguer « absent » de « vide ».
        contenu = '"""Généré par build_engine.py — aucune clé intégrée."""\nCLE_API = ""\n'
        _log("aucune clé API trouvée : le binaire en exigera une à l'exécution")
    else:
        contenu = (
            '"""Généré par build_engine.py — NE PAS VERSIONNER.\n\n'
            "Clé API intégrée à la construction pour que l'application livrée\n"
            "fonctionne sans configuration. Extractible du binaire : à révoquer\n"
            'à la fin du test.\n"""\n'
            f"CLE_API = {cle!r}\n"
        )
        _log(f"clé API intégrée (…{cle[-4:]})")
    FICHIER_CLE.write_text(contenu, encoding="utf-8")


def lancer_pyinstaller() -> None:
    _log("construction PyInstaller en cours (plusieurs minutes)…")
    resultat = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "probare_engine.spec"],
        cwd=RACINE_ENGINE,
    )
    if resultat.returncode != 0:
        _echouer(f"PyInstaller a échoué (code {resultat.returncode})")


def verifier_binaire(source: Path) -> Path:
    binaire = source / ("probare_engine.exe" if os.name == "nt" else "probare_engine")
    if not binaire.exists():
        _echouer(f"binaire attendu introuvable : {binaire}")
    return binaire


def copier_vers_resources(source: Path) -> None:
    if DEST_RESOURCES.exists():
        shutil.rmtree(DEST_RESOURCES)
    DEST_RESOURCES.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, DEST_RESOURCES)
    _log(f"moteur copié dans {DEST_RESOURCES}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Construit l'exécutable du moteur Probare")
    parser.add_argument(
        "--sans-cle", action="store_true",
        help="ne pas intégrer de clé API (le poste devra fournir ANTHROPIC_API_KEY)",
    )
    args = parser.parse_args()

    verifier_dependances()
    ecrire_cle_integree(None if args.sans_cle else lire_cle())

    try:
        lancer_pyinstaller()
        source = RACINE_ENGINE / "dist" / "engine"
        verifier_binaire(source)
        copier_vers_resources(source)
    finally:
        # La clé ne doit pas subsister en clair dans l'arbre source une fois la
        # construction terminée, réussie ou non.
        if FICHIER_CLE.exists():
            FICHIER_CLE.unlink()
            _log("fichier de clé temporaire supprimé de l'arbre source")

    _log("terminé — le moteur est prêt à être empaqueté par electron-builder")


if __name__ == "__main__":
    main()

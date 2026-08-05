"""Résolution de la clé API Claude.

Trois sources, dans cet ordre de priorité :

1. La variable d'environnement `ANTHROPIC_API_KEY` — elle prime toujours, ce
   qui permet de substituer une clé sans reconstruire l'application.
2. Un fichier `.env` : à côté de l'exécutable en production, à la racine du
   dépôt en développement. Le chemin de développement ne peut pas être déduit
   de `__file__` une fois l'application gelée (PyInstaller déplie les sources
   dans un répertoire temporaire) — d'où les deux emplacements.
3. Une clé intégrée au binaire à la construction (`_cle_integree.py`, généré
   par `build_engine.py`, jamais versionné).

La source 3 existe pour livrer une application qui fonctionne sans que le
cabinet ait à obtenir puis saisir une clé. Ce n'est PAS un secret : quiconque
dispose du binaire peut l'en extraire. Elle est acceptable pour une version de
démonstration remise à un cabinet identifié, à condition de révoquer la clé à
la fin du test. Pour une diffusion réelle, il faudra soit une saisie de clé par
le cabinet, soit un relais côté serveur qui ne distribue jamais la clé.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _est_gele() -> bool:
    """Vrai quand le moteur tourne depuis un binaire PyInstaller."""
    return getattr(sys, "frozen", False)


def _racine_executable() -> Path:
    """Répertoire de l'exécutable (gelé) ou du paquet source (développement)."""
    if _est_gele():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def chemins_env_candidats() -> list[Path]:
    """Emplacements où chercher un fichier `.env`, du plus prioritaire au moins."""
    racine = _racine_executable()
    candidats = [racine / ".env"]
    if not _est_gele():
        # Développement : apps/engine/probare_engine → remonter jusqu'à probare/
        candidats.append(Path(__file__).resolve().parents[3] / ".env")
    return candidats


def _lire_env_fichier() -> str | None:
    for chemin in chemins_env_candidats():
        if not chemin.exists():
            continue
        try:
            for ligne in chemin.read_text(encoding="utf-8").splitlines():
                ligne = ligne.strip()
                if not ligne or ligne.startswith("#") or "=" not in ligne:
                    continue
                nom, _, valeur = ligne.partition("=")
                if nom.strip() == "ANTHROPIC_API_KEY":
                    valeur = valeur.strip().strip('"').strip("'")
                    if valeur:
                        return valeur
        except OSError:
            continue
    return None


def _lire_cle_integree() -> str | None:
    try:
        from ._cle_integree import CLE_API  # type: ignore[attr-defined]
    except Exception:
        return None
    cle = str(CLE_API or "").strip()
    return cle or None


def resoudre_cle_api() -> str | None:
    """Rend la clé API disponible, ou None si aucune source n'en fournit."""
    for source in (
        lambda: (os.environ.get("ANTHROPIC_API_KEY") or "").strip() or None,
        _lire_env_fichier,
        _lire_cle_integree,
    ):
        cle = source()
        if cle:
            return cle
    return None


def installer_cle_api() -> bool:
    """Place la clé résolue dans l'environnement du processus.

    Tout le moteur lit `os.environ["ANTHROPIC_API_KEY"]` — publier la clé à cet
    endroit unique évite d'avoir à modifier chaque point d'appel, et garde la
    variable d'environnement comme seule interface interne.

    Rend True si une clé est désormais disponible.
    """
    cle = resoudre_cle_api()
    if cle:
        os.environ["ANTHROPIC_API_KEY"] = cle
        return True
    return False


def cle_disponible() -> bool:
    """Vrai si une clé API est configurée — sans jamais rendre sa valeur."""
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())

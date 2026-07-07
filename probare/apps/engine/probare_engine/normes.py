"""Référentiel de normes d'audit — ISA (défaut) ou NEP.

Les NEP françaises sont la transposition des normes ISA de l'IAASB et en
conservent la numérotation : l'équivalence est 1:1 sur les numéros utilisés
par Probare (230, 300, 315, 320, 330, 450, 500, 505, 520, 530). Le choix du
référentiel est donc un choix de RÉFÉRENCEMENT et d'affichage — il ne change
rien au processus d'audit lui-même.

Règles de fonctionnement :
- Le choix est global au cabinet, stocké dans ~/.probare/config.json.
- Il est chargé UNE FOIS au démarrage du moteur (REFERENTIEL_ACTIF) : un
  changement dans le paramétrage cabinet n'est pris en compte qu'au prochain
  démarrage de l'application, pour garantir une cohérence totale des
  livrables générés pendant une session.
- Les références déjà stockées en base (« NEP 500 » d'une ancienne session)
  sont reformatées à la lecture : aucune migration de données n'est requise.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

REFERENTIELS: dict[str, str] = {
    "isa": "ISA",
    "nep": "NEP",
}
REFERENTIEL_DEFAUT = "isa"

LIBELLES_REFERENTIEL: dict[str, str] = {
    "isa": "ISA — Normes internationales d'audit (IAASB)",
    "nep": "NEP — Normes d'exercice professionnel (référentiel français)",
}


def _config_path() -> Path:
    data_dir = Path(os.environ.get(
        "PROBARE_DATA_DIR", str(Path.home() / ".probare" / "projets")
    ))
    return data_dir.parent / "config.json"


def lire_config() -> dict:
    """Lit la configuration cabinet globale (fichier JSON local)."""
    path = _config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def ecrire_config(updates: dict) -> dict:
    """Fusionne et écrit la configuration cabinet globale."""
    config = lire_config()
    config.update(updates)
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def charger_referentiel() -> str:
    """Retourne le référentiel configuré ('isa' ou 'nep'), défaut ISA."""
    ref = str(lire_config().get("referentiel_normes", REFERENTIEL_DEFAUT)).lower()
    return ref if ref in REFERENTIELS else REFERENTIEL_DEFAUT


# Chargé une seule fois au démarrage du moteur — voir docstring du module.
REFERENTIEL_ACTIF: str = charger_referentiel()


def prefixe_actif() -> str:
    return REFERENTIELS[REFERENTIEL_ACTIF]


def norme(numero: str | int) -> str:
    """Rend une référence de norme dans le référentiel actif. norme(505) → 'ISA 505'."""
    return f"{prefixe_actif()} {numero}"


_REF_RE = re.compile(r"\b(?:NEP|ISA)\s*(\d{3})\b")


def reformater_refs(texte: str | None) -> str | None:
    """Réécrit toute référence 'NEP nnn' / 'ISA nnn' d'un texte dans le
    référentiel actif. Utilisé pour re-rendre les données stockées lors de
    sessions antérieures sous l'autre référentiel."""
    if not texte:
        return texte
    return _REF_RE.sub(lambda m: f"{prefixe_actif()} {m.group(1)}", texte)

"""Machine à états du pipeline d'audit."""
from __future__ import annotations
from typing import Literal
from ..storage.db import ProjectDB

ETATS = Literal[
    "cadrage", "ingestion", "extraction", "planification",
    "controles", "revue", "generation", "opinion"
]

TRANSITIONS_AUTORISEES: dict[str, list[str]] = {
    "cadrage":        ["ingestion"],
    "ingestion":      ["extraction"],
    "extraction":     ["planification"],
    "planification":  ["controles"],
    "controles":      ["revue"],
    "revue":          ["generation"],
    "generation":     ["opinion"],
    "opinion":        [],
}


class PipelineError(Exception):
    pass


def transition(db: ProjectDB, projet_id: str, vers: str, acteur: str = "système") -> dict:
    """Effectue une transition d'état, journalise, et renvoie le projet mis à jour."""
    projet = db.get_projet(projet_id)
    if not projet:
        raise PipelineError(f"Projet {projet_id} introuvable.")

    etat_courant = projet["etat_courant"]
    if vers not in TRANSITIONS_AUTORISEES.get(etat_courant, []):
        raise PipelineError(
            f"Transition interdite : {etat_courant} → {vers}. "
            f"Autorisées depuis {etat_courant} : {TRANSITIONS_AUTORISEES[etat_courant]}"
        )

    if vers == "generation" and db.has_open_exceptions(projet_id):
        raise PipelineError(
            "Impossible de passer en génération : il reste des exceptions ouvertes."
        )

    updated = db.update_projet(projet_id, {"etat_courant": vers})
    db.log(projet_id, "transition_etat", {
        "de": etat_courant,
        "vers": vers,
        "acteur": acteur,
    })
    return updated


def peut_transitionner(db: ProjectDB, projet_id: str, vers: str) -> tuple[bool, str]:
    """Retourne (peut, raison_si_non)."""
    projet = db.get_projet(projet_id)
    if not projet:
        return False, "Projet introuvable."
    etat_courant = projet["etat_courant"]
    if vers not in TRANSITIONS_AUTORISEES.get(etat_courant, []):
        return False, f"Transition {etat_courant} → {vers} non autorisée."
    if vers == "generation" and db.has_open_exceptions(projet_id):
        return False, "Exceptions ouvertes non tranchées."
    return True, ""

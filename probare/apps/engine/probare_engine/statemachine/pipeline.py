"""Machine à états du pipeline d'audit."""
from __future__ import annotations
from typing import Literal
from ..storage.db import ProjectDB
from ..normes import norme

# Code structuré du blocage « cumul d'anomalies > seuil » (ISA/NEP 450).
# Le frontend détecte CE code, jamais le libellé de la norme (qui dépend du
# référentiel actif du cabinet).
CODE_SEUIL_DEPASSE = "[ANOMALIES_SEUIL_DEPASSE]"

ETATS = Literal[
    "cadrage", "evaluation_ci", "ingestion",
    "planification", "travaux_substantifs", "revue", "generation", "opinion"
]

# Ordre nominal des phases — utilisé pour autoriser les retours arrière explicites.
ORDRE_ETATS: list[str] = [
    "cadrage", "evaluation_ci", "ingestion", "planification",
    "travaux_substantifs", "revue", "generation", "opinion",
]

TRANSITIONS_AUTORISEES: dict[str, list[str]] = {
    "cadrage":              ["evaluation_ci"],
    "evaluation_ci":        ["ingestion"],
    "ingestion":            ["planification"],
    "planification":        ["travaux_substantifs"],
    "travaux_substantifs":  ["revue"],
    "revue":                ["generation"],
    "generation":           ["opinion"],
    "opinion":              [],
    # Rétrocompatibilité
    "extraction":           ["planification", "travaux_substantifs"],
    "controles":            ["travaux_substantifs", "revue"],
}


class PipelineError(Exception):
    pass


def _est_retour_arriere(etat_courant: str, vers: str) -> bool:
    """Retour arrière = revenir à une phase antérieure de l'ordre nominal."""
    if etat_courant not in ORDRE_ETATS or vers not in ORDRE_ETATS:
        return False
    return ORDRE_ETATS.index(vers) < ORDRE_ETATS.index(etat_courant)


def _verifier_gardes(db: ProjectDB, projet_id: str, projet: dict, vers: str,
                     confirmer_depassement_seuil: bool = False) -> None:
    """
    Gardes déterministes par transition (progression uniquement) :
    - travaux_substantifs : seuil de signification défini (ISA/NEP 320).
    - revue               : au moins un contrôle exécuté (ISA/NEP 330).
    - generation          : exceptions tranchées + verrou ISA/NEP 450 sur le
                            cumul des anomalies non corrigées.
    """
    if vers == "travaux_substantifs":
        seuil = projet.get("seuil_signification")
        if not seuil or float(seuil) <= 0:
            raise PipelineError(
                f"Seuil de signification non défini ({norme(320)}). "
                "Calculez ou saisissez le seuil dans Planification avant de lancer les travaux."
            )

    if vers == "revue":
        resultats = db.list_resultats(projet_id)
        if not resultats:
            raise PipelineError(
                f"Aucun contrôle n'a encore été exécuté ({norme(330)}). "
                "Lancez au moins un cycle de contrôles avant de passer en revue."
            )

    if vers == "generation":
        if db.has_open_exceptions(projet_id):
            raise PipelineError(
                "Impossible de passer en génération : il reste des exceptions ouvertes."
            )
        synthese = db.synthese_anomalies(
            projet_id,
            projet.get("seuil_signification"),
            projet.get("seuil_planification"),
        )
        if synthese["depasse_seuil_signification"] and not confirmer_depassement_seuil:
            raise PipelineError(
                f"{CODE_SEUIL_DEPASSE} {norme(450)} : le cumul des anomalies non corrigées "
                f"({synthese['cumul_non_corrigees']:,.0f}) dépasse le seuil de signification "
                f"({synthese['seuil_signification']:,.0f}). "
                "Ce dépassement affecte l'opinion : enregistrez les corrections du client, "
                "ou confirmez explicitement le passage en génération en acceptant "
                "l'incidence sur l'opinion (confirmer_depassement_seuil=true)."
            )
        # ISA 240 : les tests des écritures de journal (Journal Entry Testing) sont
        # une diligence obligatoire et transversale. Ils doivent avoir été exécutés
        # (au moins un résultat porté par une référence de signal JET) avant le dossier.
        from ..controls.registry import JET_SIGNAL_REF
        refs_jet = set(JET_SIGNAL_REF.values())
        if not any(r.get("controle_ref") in refs_jet for r in db.list_resultats(projet_id)):
            raise PipelineError(
                f"Les tests des écritures de journal ({norme(240)}) n'ont pas été exécutés. "
                "Lancez l'analyse dans l'écran « Écritures de journal » avant de passer "
                "en génération : c'est une diligence obligatoire (détection du contournement "
                "des contrôles)."
            )
        # M3 (ISA 570) : la conclusion sur la continuité d'exploitation doit être
        # documentée et signée avant d'assembler le dossier.
        eval_continuite = db.get_peripherie_evaluation(projet_id, "continuite")
        if not eval_continuite or not eval_continuite.get("conclusion"):
            raise PipelineError(
                f"La conclusion sur la continuité d'exploitation ({norme(570)}) n'est pas "
                "documentée. Complétez la diligence « Continuité d'exploitation » "
                "(questionnaire, évaluation, conclusion signée) dans l'écran Diligences "
                "avant de passer en génération."
            )


def transition(
    db: ProjectDB,
    projet_id: str,
    vers: str,
    acteur: str = "système",
    confirmer_depassement_seuil: bool = False,
) -> dict:
    """Effectue une transition d'état, journalise, et renvoie le projet mis à jour.

    Deux familles de transitions :
    - progression nominale (TRANSITIONS_AUTORISEES) — soumise aux gardes ;
    - retour arrière explicite vers une phase antérieure — toujours permis mais
      journalisé comme tel (NEP 230), pour corriger un oubli sans casser la traçabilité.
    """
    projet = db.get_projet(projet_id)
    if not projet:
        raise PipelineError(f"Projet {projet_id} introuvable.")
    if projet.get("archive"):
        raise PipelineError("Dossier archivé — lecture seule. Désarchivez-le pour le modifier.")

    etat_courant = projet["etat_courant"]
    retour_arriere = _est_retour_arriere(etat_courant, vers)

    if not retour_arriere:
        if vers not in TRANSITIONS_AUTORISEES.get(etat_courant, []):
            raise PipelineError(
                f"Transition interdite : {etat_courant} → {vers}. "
                f"Autorisées depuis {etat_courant} : {TRANSITIONS_AUTORISEES.get(etat_courant, [])}"
            )
        _verifier_gardes(db, projet_id, projet, vers, confirmer_depassement_seuil)

    updated = db.update_projet(projet_id, {"etat_courant": vers})
    payload = {
        "de": etat_courant,
        "vers": vers,
        "acteur": acteur,
    }
    if retour_arriere:
        payload["retour_arriere"] = True
    if vers == "generation" and confirmer_depassement_seuil:
        payload["depassement_seuil_confirme"] = True
    db.log(projet_id, "transition_etat", payload)
    return updated


def peut_transitionner(db: ProjectDB, projet_id: str, vers: str) -> tuple[bool, str]:
    """Retourne (peut, raison_si_non)."""
    projet = db.get_projet(projet_id)
    if not projet:
        return False, "Projet introuvable."
    if projet.get("archive"):
        return False, "Dossier archivé — lecture seule."
    etat_courant = projet["etat_courant"]
    if _est_retour_arriere(etat_courant, vers):
        return True, ""
    if vers not in TRANSITIONS_AUTORISEES.get(etat_courant, []):
        return False, f"Transition {etat_courant} → {vers} non autorisée."
    try:
        _verifier_gardes(db, projet_id, projet, vers)
    except PipelineError as e:
        return False, str(e)
    return True, ""

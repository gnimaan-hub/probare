"""Matrice de couverture risque ↔ assertion ↔ procédures (M4 — ISA 315 révisée).

Calcul 100 % déterministe. On croise :
- les risques VALIDÉS par l'auditeur (cycle × assertions) ;
- les procédures disponibles pour couvrir chaque assertion d'un cycle :
    * contrôles déterministes du registre (assertions déclarées) ;
    * sondages du cycle (ISA 530) ;
    * circularisations du cycle (ISA 505).

L'objectif est de rendre visible, assertion par assertion, si un risque validé
est couvert par au moins une procédure — et de signaler les trous.
"""
from __future__ import annotations
from ..controls.registry import REGISTRE, ASSERTIONS


# Sondages et circularisations sont des procédures substantives de validation :
# elles apportent des éléments probants sur l'existence et l'évaluation des
# soldes/opérations testés (ISA 500/505/530). On les rattache à ces assertions.
ASSERTIONS_SONDAGE = ("existence", "evaluation")
ASSERTIONS_CIRCULARISATION = ("existence", "evaluation", "droits")


def _procedures_par_assertion(cycle: str, assertion: str,
                              sondages: list[dict],
                              circularisations: list[dict]) -> list[dict]:
    """Procédures couvrant (cycle, assertion), tous types confondus."""
    procedures: list[dict] = []
    for c in REGISTRE.values():
        if c.cycle == cycle and assertion in c.assertions:
            procedures.append({"type": "controle", "ref": c.ref, "libelle": c.libelle})
    if assertion in ASSERTIONS_SONDAGE:
        for s in sondages:
            if s.get("cycle") == cycle:
                procedures.append({"type": "sondage", "ref": s.get("id"),
                                   "libelle": s.get("libelle") or "Sondage"})
    if assertion in ASSERTIONS_CIRCULARISATION:
        for ci in circularisations:
            if ci.get("cycle") == cycle:
                procedures.append({"type": "circularisation", "ref": ci.get("id"),
                                   "libelle": ci.get("libelle") or ci.get("compte") or "Circularisation"})
    return procedures


def matrice_couverture(risques: list[dict],
                       sondages: list[dict],
                       circularisations: list[dict]) -> dict:
    """Construit la matrice de couverture.

    risques : risques VALIDÉS (déjà filtrés par l'appelant), chacun {cycle, assertions, ...}.
    Retourne les cellules (cycle × assertion) qui portent un risque, avec les
    procédures qui les couvrent, plus la liste des trous (assertions à risque
    sans aucune procédure).
    """
    # Regrouper les risques par (cycle, assertion). Un risque sans assertion
    # explicite est rattaché à toutes les assertions de son cycle (prudence :
    # un risque non qualifié doit être couvert sur tous les fronts).
    cellules: dict[tuple[str, str], list[dict]] = {}
    for r in risques:
        cycle = r.get("cycle") or "transversal"
        asserts = r.get("assertions") or list(ASSERTIONS.keys())
        for a in asserts:
            if a not in ASSERTIONS:
                continue
            cellules.setdefault((cycle, a), []).append(
                {"id": r.get("id"), "libelle": r.get("libelle"),
                 "niveau": r.get("niveau", "moyen")})

    lignes = []
    trous = []
    nb_couverts = 0
    for (cycle, assertion), risques_cellule in sorted(cellules.items()):
        procedures = _procedures_par_assertion(cycle, assertion, sondages, circularisations)
        couvert = len(procedures) > 0
        if couvert:
            nb_couverts += 1
        else:
            trous.append({"cycle": cycle, "assertion": assertion,
                          "assertion_libelle": ASSERTIONS.get(assertion, assertion),
                          "risques": risques_cellule})
        lignes.append({
            "cycle": cycle,
            "assertion": assertion,
            "assertion_libelle": ASSERTIONS.get(assertion, assertion),
            "risques": risques_cellule,
            "procedures": procedures,
            "nb_procedures": len(procedures),
            "couvert": couvert,
        })

    return {
        "assertions": ASSERTIONS,
        "lignes": lignes,
        "trous": trous,
        "nb_cellules": len(lignes),
        "nb_couvertes": nb_couverts,
        "nb_trous": len(trous),
        "taux_couverture": round(nb_couverts / len(lignes), 2) if lignes else None,
    }

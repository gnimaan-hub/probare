"""Calcul des seuils de signification — purement déterministe (ISA 320 / H2A)."""
from __future__ import annotations

# Taux par défaut selon la base de calcul choisie
TAUX_DEFAUT: dict[str, float] = {
    "total_bilan":      0.01,   # 1 % du total bilan
    "chiffre_affaires": 0.015,  # 1,5 % du CA
    "resultat_net":     0.05,   # 5 % du résultat
    "total_actif":      0.01,
}

LIBELLES_AGREGAT: dict[str, str] = {
    "total_bilan":      "Total bilan",
    "chiffre_affaires": "Chiffre d'affaires",
    "resultat_net":     "Résultat net",
    "total_actif":      "Total actif",
}


def taux_defaut(agregat_type: str) -> float:
    return TAUX_DEFAUT.get(agregat_type, 0.01)


def calculer_seuils(
    agregat_type: str,
    agregat_valeur: float,
    taux_signification: float,
    taux_planification: float = 0.75,
) -> dict:
    """
    Retourne les deux seuils calculés.
    Ne fait aucun appel LLM, aucune lecture de base.
    """
    seuil = abs(agregat_valeur) * taux_signification
    seuil_plan = seuil * taux_planification
    return {
        "agregat_type": agregat_type,
        "agregat_libelle": LIBELLES_AGREGAT.get(agregat_type, agregat_type),
        "agregat_valeur": round(agregat_valeur, 2),
        "taux_signification": taux_signification,
        "taux_planification": taux_planification,
        "seuil_signification": round(seuil, 2),
        "seuil_planification": round(seuil_plan, 2),
    }

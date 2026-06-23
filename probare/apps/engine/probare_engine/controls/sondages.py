"""Sondages sur pièces — NEP 530 : Sondage en audit.

Toute l'arithmétique est ici en Python. Le LLM ne calcule jamais.
Formule de Neyman simplifiée recommandée par la CNCC pour NEP 530.
"""
from __future__ import annotations
import math
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from ..provenance.models import DonneeSourcee


RowDict = dict[str, DonneeSourcee]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_amount(row: RowDict, field: str) -> float:
    d = row.get(field)
    if d is None:
        return 0.0
    try:
        return float(d.valeur) if d.valeur is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _get_str(row: RowDict, field: str) -> str:
    d = row.get(field)
    return str(d.valeur or "").strip() if d else ""


# Facteurs Z pour niveaux de confiance courants (one-tail)
_Z_FACTEURS = {
    90: 1.645,
    95: 1.960,
    99: 2.576,
}


# ─── Taille d'échantillon ─────────────────────────────────────────────────────

def calculer_taille_echantillon(
    population: int,
    taux_erreur_tolere: float = 0.05,   # e.g. 0.05 = 5 %
    niveau_confiance: int = 95,          # 90, 95 ou 99
) -> dict:
    """Formule Neyman simplifiée (NEP 530).

    n = (Z² × p × (1-p)) / e²   puis correction finie si n/N > 5 %.
    p = taux d'anomalie anticipé (conservateur = 50 % → max variance).
    """
    Z = _Z_FACTEURS.get(niveau_confiance, 1.96)
    p = 0.5  # worst-case proportion
    e = taux_erreur_tolere

    n_inf = (Z ** 2 * p * (1 - p)) / (e ** 2)
    # Correction population finie
    if population > 0:
        n = n_inf / (1 + (n_inf - 1) / population)
    else:
        n = n_inf

    n = max(1, math.ceil(n))
    # Plafond pratique : pas plus de 30 % de la population
    n = min(n, max(1, math.floor(population * 0.30))) if population > 0 else n

    return {
        "taille_recommandee": n,
        "population": population,
        "taux_erreur_tolere": taux_erreur_tolere,
        "niveau_confiance": niveau_confiance,
        "facteur_z": Z,
    }


# ─── Sélection de l'échantillon ──────────────────────────────────────────────

def selectionner_echantillon(
    rows: list[RowDict],
    prefixes: list[str],
    n: int,
    seed: int | None = None,
) -> list[dict]:
    """Sélectionne n éléments au hasard parmi les lignes correspondant aux préfixes.

    Sélection déterministe si seed fourni. Chaque élément inclut sa provenance.
    """
    candidats = []
    for i, row in enumerate(rows):
        compte = _get_str(row, "compte")
        if prefixes and not any(compte.startswith(p) for p in prefixes):
            continue
        montant = _get_amount(row, "solde") or (
            _get_amount(row, "debit") - _get_amount(row, "credit")
        )
        sources = []
        for field in ("compte", "libelle", "debit", "credit", "solde", "numero_piece", "date"):
            d = row.get(field)
            if d and d.id:
                sources.append(d.id)
        candidats.append({
            "index_original": i,
            "compte": compte,
            "libelle": _get_str(row, "libelle"),
            "montant": round(montant, 2),
            "numero_piece": _get_str(row, "numero_piece"),
            "date_piece": _get_str(row, "date"),
            "sources": list(dict.fromkeys(sources)),
        })

    rng = random.Random(seed)
    n_effectif = min(n, len(candidats))
    return rng.sample(candidats, n_effectif) if candidats else []


# ─── Projection d'erreur ─────────────────────────────────────────────────────

def projeter_erreur(
    nb_anomalies: int,
    montant_anomalies: float,
    montant_population: float,
    taille_echantillon: int,
) -> dict:
    """Projette les anomalies constatées dans l'échantillon à la population entière.

    Taux d'anomalie = nb_anomalies / taille_echantillon.
    Montant projeté = (montant_anomalies / taille_echantillon) × montant_population / 1.
    """
    taux_anomalie = nb_anomalies / taille_echantillon if taille_echantillon > 0 else 0.0
    if taille_echantillon > 0 and montant_population > 0:
        montant_projete = (montant_anomalies / taille_echantillon) * montant_population
    else:
        montant_projete = 0.0

    return {
        "taux_anomalie": round(taux_anomalie, 4),
        "montant_anomalies_echantillon": round(montant_anomalies, 2),
        "montant_projete_population": round(montant_projete, 2),
        "nb_anomalies": nb_anomalies,
        "taille_echantillon": taille_echantillon,
    }

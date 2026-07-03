"""Circularisation — NEP 505 : Confirmation externe.

Toute l'arithmétique est ici en Python. Le LLM ne calcule jamais.
"""
from __future__ import annotations
import uuid
from collections import defaultdict
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


# ─── Sélection des tiers à circulariser ──────────────────────────────────────

def proposer_tiers(
    rows: list[RowDict],
    prefixes: list[str],
    n: int = 10,
) -> list[dict]:
    """Sélectionne les N tiers avec le solde absolu le plus élevé.

    Retourne une liste triée par |solde| décroissant, avec pour chaque tiers :
    compte, libelle, solde, source_ids (provenance).
    """
    aggregats: dict[str, dict] = defaultdict(lambda: {
        "solde": 0.0, "libelle": "", "sources": []
    })

    for row in rows:
        compte = _get_str(row, "compte")
        if not any(compte.startswith(p) for p in prefixes):
            continue
        libelle = _get_str(row, "libelle") or compte
        solde = _get_amount(row, "solde") or (
            _get_amount(row, "debit") - _get_amount(row, "credit")
        )
        # Regroupe par couple (compte, libelle court)
        cle = compte
        aggregats[cle]["solde"] += solde
        if not aggregats[cle]["libelle"]:
            aggregats[cle]["libelle"] = libelle
        for field in ("compte", "solde", "debit", "credit"):
            d = row.get(field)
            if d and d.id:
                aggregats[cle]["sources"].append(d.id)

    # Trie par |solde| décroissant et prend les N premiers
    triers = sorted(
        [{"compte": k, "libelle": v["libelle"], "solde": v["solde"], "sources": list(dict.fromkeys(v["sources"]))}
         for k, v in aggregats.items()],
        key=lambda x: abs(x["solde"]),
        reverse=True,
    )
    return triers[:n]


# ─── Calcul d'écart ──────────────────────────────────────────────────────────

def calculer_ecart(
    solde_comptable: float,
    solde_confirme: float,
    seuil_reference: float | None = None,
) -> dict:
    """Calcule l'écart entre le solde comptable et le solde confirmé par le tiers.

    Le caractère significatif se réfère au seuil du dossier (seuil de planification
    de préférence) quand il est fourni ; à défaut, repli sur la règle interne
    « > 5 % ou > 100 » (héritée du MVP, très conservatrice).
    Retourne ecart (montant), ecart_pct, est_significatif, seuil_reference.
    """
    ecart = solde_comptable - solde_confirme
    ecart_pct = (ecart / solde_comptable * 100) if solde_comptable != 0 else 0.0
    if seuil_reference and seuil_reference > 0:
        est_significatif = abs(ecart) > seuil_reference
    else:
        est_significatif = abs(ecart_pct) > 5.0 or abs(ecart) > 100.0
    return {
        "ecart": round(ecart, 2),
        "ecart_pct": round(ecart_pct, 4),
        "est_significatif": est_significatif,
        "seuil_reference": seuil_reference,
    }

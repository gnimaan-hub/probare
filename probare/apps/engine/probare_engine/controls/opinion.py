"""Agrégation des anomalies et détermination du type d'opinion — NEP 450 + OPI.

Tout ici est déterministe Python. Le LLM ne calcule et ne choisit rien.
L'IA intervient uniquement pour rédiger la narrative (dans llm/claude.py).
"""
from __future__ import annotations


SEVERITE_RANG = {"critique": 3, "significative": 2, "mineure": 1}


def agreger_anomalies(
    exceptions: list[dict],
    seuil_signification: float,
) -> dict:
    """Regroupe et somme les anomalies, compare au seuil de signification.

    Retourne des données purement calculées — aucune interprétation.
    """
    tranchees = [e for e in exceptions if e.get("statut") == "tranchee"]

    nb_critiques = sum(1 for e in tranchees if e.get("severite") == "critique")
    nb_significatives = sum(1 for e in tranchees if e.get("severite") == "significative")
    nb_mineures = sum(1 for e in tranchees if e.get("severite") == "mineure")
    nb_ouvertes = sum(1 for e in exceptions if e.get("statut") == "ouverte")

    # Cumul montant : extrait la valeur numérique si présente dans description
    # On ne parse pas les descriptions (LLM a rédigé en langage naturel)
    # La somme de montants est volontairement mise à 0 ici — seul l'auditeur
    # peut la chiffrer si les exceptions ne portent pas de champ montant.
    # Si les exceptions ont un champ montant_anomalie, on l'utilise.
    cumul_montant = 0.0
    for e in tranchees:
        try:
            val = float(e.get("montant_anomalie") or 0)
        except (ValueError, TypeError):
            val = 0.0
        cumul_montant += val

    depasse_seuil = (seuil_signification > 0) and (cumul_montant >= seuil_signification)

    repartition_par_cycle: dict[str, dict] = {}
    for e in exceptions:
        cycle = e.get("controle_ref", "").split("-")[0].lower() or "inconnu"
        if cycle not in repartition_par_cycle:
            repartition_par_cycle[cycle] = {"total": 0, "critiques": 0, "significatives": 0, "mineures": 0}
        repartition_par_cycle[cycle]["total"] += 1
        sev = e.get("severite", "mineure")
        if sev == "critique":
            repartition_par_cycle[cycle]["critiques"] += 1
        elif sev == "significative":
            repartition_par_cycle[cycle]["significatives"] += 1
        else:
            repartition_par_cycle[cycle]["mineures"] += 1

    return {
        "nb_total": len(exceptions),
        "nb_tranchees": len(tranchees),
        "nb_ouvertes": nb_ouvertes,
        "nb_critiques": nb_critiques,
        "nb_significatives": nb_significatives,
        "nb_mineures": nb_mineures,
        "cumul_montant": round(cumul_montant, 2),
        "seuil_signification": seuil_signification,
        "depasse_seuil": depasse_seuil,
        "repartition_par_cycle": repartition_par_cycle,
    }


def determiner_type_opinion(agregation: dict) -> str:
    """Matrice déterministe Python — le LLM ne décide jamais du type d'opinion.

    Matrice (du plus grave au moins grave) :
    - critique (quelle que soit la somme) → refus
    - significative + dépasse seuil → reserve
    - significative + sous seuil → propre_avec_observation
    - mineure uniquement (ou aucune) → propre
    """
    nb_critiques = agregation.get("nb_critiques", 0)
    nb_significatives = agregation.get("nb_significatives", 0)
    depasse_seuil = agregation.get("depasse_seuil", False)
    nb_ouvertes = agregation.get("nb_ouvertes", 0)

    # Les exceptions ouvertes bloquent la formation d'opinion
    if nb_ouvertes > 0:
        return "incomplete"

    if nb_critiques > 0:
        return "refus"

    if nb_significatives > 0:
        if depasse_seuil:
            return "reserve"
        return "propre_avec_observation"

    return "propre"


TYPE_OPINION_LABELS = {
    "propre": "Opinion sans réserve",
    "propre_avec_observation": "Opinion sans réserve avec observation",
    "reserve": "Opinion avec réserve",
    "refus": "Refus de certifier",
    "incomplete": "Formation d'opinion impossible (exceptions ouvertes)",
}

TYPE_OPINION_COLORS = {
    "propre": "emerald",
    "propre_avec_observation": "amber",
    "reserve": "orange",
    "refus": "red",
    "incomplete": "slate",
}

"""Points de réserve QUALITATIFS et cohérence avec l'opinion (R3 — ISA 705).

Le cumul ISA 450 ne modélise que le **quantitatif** : des anomalies chiffrées,
non corrigées, comparées au seuil de signification. Or une réserve naît tout
aussi souvent d'un fait **non chiffrable** :

- une **limitation d'étendue** — impossibilité d'obtenir des éléments probants
  suffisants et appropriés (provisions non justifiées, dettes non confirmées,
  stock non observé…) ;
- une **incertitude significative** — continuité d'exploitation, litige dont
  l'issue ne peut être appréciée ;
- un **désaccord** avec la direction sur une méthode comptable ou une
  présentation, sans montant arrêté.

Le test de bout en bout a montré le défaut que ce module corrige : une opinion
« avec réserve » adossée à un cumul 450 de **zéro** — une réserve qui ne
s'appuyait sur rien de traçable dans le dossier. Un réviseur le relève
immédiatement.

Ce module ne contient QUE le vocabulaire et les règles de cohérence (fonctions
pures, aucune I/O). Le stockage est dans `storage/db.py` (table `point_reserve`),
l'exposition dans `api/routes.py`, le rendu dans `reporting/export.py`.
"""
from __future__ import annotations


# ─── Vocabulaire (ISA 705) ────────────────────────────────────────────────────

TYPE_LIMITATION = "limitation"
TYPE_INCERTITUDE = "incertitude"
TYPE_DESACCORD = "desaccord"

TYPES_POINT_RESERVE: dict[str, str] = {
    TYPE_LIMITATION: "Limitation de l'étendue des travaux",
    TYPE_INCERTITUDE: "Incertitude significative",
    TYPE_DESACCORD: "Désaccord avec la direction",
}

# Ce que le point impose, au minimum, à l'opinion. « aucun » = le point est
# documenté et suivi, mais l'auditeur juge qu'il n'affecte pas l'opinion (il
# relève alors du paragraphe d'observation).
IMPACT_AUCUN = "aucun"
IMPACT_RESERVE = "reserve"
IMPACT_DEFAVORABLE = "defavorable"
IMPACT_IMPOSSIBILITE = "impossibilite"

IMPACTS_OPINION: dict[str, str] = {
    IMPACT_AUCUN: "Sans incidence sur l'opinion (mention en observation)",
    IMPACT_RESERVE: "Réserve",
    IMPACT_DEFAVORABLE: "Opinion défavorable",
    IMPACT_IMPOSSIBILITE: "Impossibilité d'exprimer une opinion",
}

STATUT_OUVERT = "ouvert"
STATUT_LEVE = "leve"
STATUTS_POINT_RESERVE: dict[str, str] = {
    STATUT_OUVERT: "Ouvert — pèse sur l'opinion",
    STATUT_LEVE: "Levé — élément probant finalement obtenu",
}

# Type d'opinion exigé par un impact donné, et gravité relative des opinions.
_OPINION_PAR_IMPACT = {
    IMPACT_RESERVE: "avec_reserve",
    IMPACT_DEFAVORABLE: "defavorable",
    IMPACT_IMPOSSIBILITE: "impossibilite",
}

# Ordre de gravité : un type d'opinion ne peut pas être MOINS grave que ce que
# le dossier exige. Il peut l'être davantage (jugement de l'auditeur).
GRAVITE_OPINION = {
    "sans_reserve": 0,
    "avec_reserve": 1,
    "defavorable": 2,
    "impossibilite": 2,   # aussi grave qu'une opinion défavorable, nature différente
}

LABELS_TYPE_OPINION = {
    "sans_reserve": "Opinion sans réserve",
    "avec_reserve": "Opinion avec réserve",
    "defavorable": "Opinion défavorable",
    "impossibilite": "Impossibilité d'exprimer une opinion",
}


def points_ouverts(points: list[dict] | None) -> list[dict]:
    """Points qui pèsent encore sur l'opinion (les points levés sont conservés
    au dossier — ils documentent une diligence menée à son terme)."""
    return [p for p in (points or []) if (p.get("statut") or STATUT_OUVERT) == STATUT_OUVERT]


def points_impactants(points: list[dict] | None) -> list[dict]:
    """Points ouverts qui exigent autre chose qu'une opinion sans réserve."""
    return [p for p in points_ouverts(points)
            if (p.get("impact_opinion") or IMPACT_AUCUN) in _OPINION_PAR_IMPACT]


def opinion_minimale_requise(points: list[dict] | None,
                             anomalies: dict | None = None) -> str:
    """Type d'opinion le moins sévère que le dossier puisse justifier.

    Croise les deux fondements possibles d'une réserve : les points de réserve
    qualitatifs ouverts (ce module) et le cumul des anomalies non corrigées
    (ISA 450). Purement déterministe — aucun jugement LLM.
    """
    requis = "sans_reserve"
    for p in points_impactants(points):
        candidat = _OPINION_PAR_IMPACT[p["impact_opinion"]]
        if GRAVITE_OPINION[candidat] > GRAVITE_OPINION[requis]:
            requis = candidat
    if (anomalies or {}).get("depasse_seuil_signification") \
            and GRAVITE_OPINION["avec_reserve"] > GRAVITE_OPINION[requis]:
        requis = "avec_reserve"
    return requis


def incoherences_opinion(type_opinion: str | None, points: list[dict] | None,
                         anomalies: dict | None = None) -> list[str]:
    """Incohérences entre le type d'opinion retenu et ce que le dossier établit.

    Deux sens de lecture, tous deux relevés par un contrôle qualité :
    - l'opinion est **moins sévère** que ce que le dossier exige — la réserve
      due n'est pas exprimée ;
    - l'opinion est **plus sévère** sans que rien ne la justifie — c'est le cas
      constaté au test : réserve exprimée, cumul 450 nul, aucun point de réserve.
    """
    type_opinion = (type_opinion or "").strip() or None
    if not type_opinion or type_opinion not in GRAVITE_OPINION:
        return []
    anomalies = anomalies or {}
    ecarts: list[str] = []

    requis = opinion_minimale_requise(points, anomalies)
    if GRAVITE_OPINION[type_opinion] < GRAVITE_OPINION[requis]:
        motifs = [f"« {p.get('libelle')} » ({TYPES_POINT_RESERVE.get(p.get('type'), p.get('type'))})"
                  for p in points_impactants(points)]
        if anomalies.get("depasse_seuil_signification"):
            motifs.append("cumul des anomalies non corrigées supérieur au seuil de signification")
        ecarts.append(
            f"{LABELS_TYPE_OPINION[type_opinion]} alors que le dossier justifie au moins "
            f"« {LABELS_TYPE_OPINION[requis]} » : " + " ; ".join(motifs) + "."
        )

    if GRAVITE_OPINION[type_opinion] > GRAVITE_OPINION["sans_reserve"] \
            and not points_impactants(points) \
            and not anomalies.get("depasse_seuil_signification") \
            and not float(anomalies.get("cumul_non_corrigees") or 0.0):
        ecarts.append(
            f"{LABELS_TYPE_OPINION[type_opinion]} sans fondement traçable dans le dossier : "
            "aucun point de réserve qualitatif ouvert et cumul des anomalies non corrigées nul. "
            "Enregistrez le point de réserve (limitation, incertitude ou désaccord) qui la motive, "
            "ou retenez une opinion sans réserve."
        )
    return ecarts


def synthese_points_reserve(points: list[dict] | None,
                            anomalies: dict | None = None) -> dict:
    """Récapitulatif servi à côté du cumul ISA 450 : le lecteur voit d'un coup
    les deux fondements possibles d'une réserve, le chiffré et le qualitatif."""
    tous = list(points or [])
    ouverts = points_ouverts(tous)
    par_type = {t: sum(1 for p in ouverts if p.get("type") == t) for t in TYPES_POINT_RESERVE}
    montant = sum(abs(float(p.get("montant_concerne") or 0.0)) for p in ouverts)
    return {
        "nb_total": len(tous),
        "nb_ouverts": len(ouverts),
        "nb_leves": len(tous) - len(ouverts),
        "nb_impactants": len(points_impactants(tous)),
        "par_type": par_type,
        # Montant des postes CONCERNÉS par une limitation ou une incertitude :
        # ce n'est pas une anomalie chiffrée, il n'entre jamais au cumul 450.
        "montant_concerne_total": round(montant, 2),
        "opinion_minimale_requise": opinion_minimale_requise(tous, anomalies),
        "points_ouverts": [
            {"id": p.get("id"), "type": p.get("type"),
             "type_label": TYPES_POINT_RESERVE.get(p.get("type"), p.get("type")),
             "libelle": p.get("libelle"), "rubrique": p.get("rubrique"),
             "montant_concerne": p.get("montant_concerne"),
             "impact_opinion": p.get("impact_opinion")}
            for p in ouverts
        ],
    }


def valider_point(data: dict) -> None:
    """Vérifie le vocabulaire d'un point de réserve. Lève ValueError sinon."""
    if not str(data.get("libelle") or "").strip():
        raise ValueError("Le libellé du point de réserve est obligatoire.")
    type_pt = data.get("type")
    if type_pt not in TYPES_POINT_RESERVE:
        raise ValueError(f"Type de point de réserve inconnu : {type_pt}. "
                         f"Valeurs admises : {sorted(TYPES_POINT_RESERVE)}.")
    impact = data.get("impact_opinion")
    if impact not in IMPACTS_OPINION:
        raise ValueError(f"Impact sur l'opinion inconnu : {impact}. "
                         f"Valeurs admises : {sorted(IMPACTS_OPINION)}.")
    statut = data.get("statut") or STATUT_OUVERT
    if statut not in STATUTS_POINT_RESERVE:
        raise ValueError(f"Statut inconnu : {statut}. "
                         f"Valeurs admises : {sorted(STATUTS_POINT_RESERVE)}.")
    if statut == STATUT_LEVE and not str(data.get("resolution") or "").strip():
        raise ValueError("Un point de réserve levé doit documenter comment il l'a été "
                         "(élément probant finalement obtenu).")

"""Écritures d'ajustement (M1) — calculs déterministes, aucun LLM.

Une écriture d'ajustement matérialise une anomalie en langage comptable
(comptes débités / crédités). Elle suit un cycle de vie :

    proposee → acceptee_client → passee     (le client l'a comptabilisée)
            ↘ refusee                        (le client refuse la correction)

- Les écritures PASSÉES construisent la balance ajustée.
- Les écritures NON passées (proposées, acceptées, refusées) chiffrent les
  anomalies subsistantes de l'état récapitulatif ISA 450 (le « SUM »).

Tout est calculé ici en Python : équilibre, effets sur le résultat et les
capitaux propres, balance ajustée. Le LLM ne produit jamais un montant.
"""
from __future__ import annotations

TOLERANCE_EQUILIBRE = 0.01

TYPES_ANOMALIE = ("factuelle", "jugement", "extrapolee")

STATUTS = ("proposee", "acceptee_client", "passee", "refusee")

# Transitions autorisées du cycle de vie. `passee` est terminal : une écriture
# comptabilisée chez le client ne se « dé-comptabilise » pas dans le dossier.
TRANSITIONS_STATUT: dict[str, list[str]] = {
    "proposee":        ["acceptee_client", "passee", "refusee"],
    "acceptee_client": ["passee", "refusee", "proposee"],
    "refusee":         ["proposee"],
    "passee":          [],
}

LIBELLES_STATUT = {
    "proposee": "Proposée au client",
    "acceptee_client": "Acceptée par le client",
    "passee": "Passée (comptabilisée)",
    "refusee": "Refusée par le client",
}

LIBELLES_TYPE = {
    "factuelle": "Factuelle (erreur avérée)",
    "jugement": "De jugement (estimation contestée)",
    "extrapolee": "Extrapolée (projetée depuis un sondage)",
}


class AjustementError(ValueError):
    pass


def valider_lignes(lignes: list[dict]) -> tuple[float, float]:
    """Valide les lignes d'une écriture et retourne (total_debits, total_credits).

    Règles : au moins 2 lignes, comptes non vides, montants positifs ou nuls,
    chaque ligne mouvemente un seul sens, et l'écriture est équilibrée
    (partie double — c'est la définition même d'une écriture).
    """
    if not lignes or len(lignes) < 2:
        raise AjustementError("Une écriture comporte au moins deux lignes (partie double).")
    total_d, total_c = 0.0, 0.0
    for i, l in enumerate(lignes, start=1):
        compte = str(l.get("compte") or "").strip()
        if not compte or not compte[0].isdigit():
            raise AjustementError(f"Ligne {i} : numéro de compte manquant ou invalide.")
        try:
            debit = round(float(l.get("debit") or 0), 2)
            credit = round(float(l.get("credit") or 0), 2)
        except (TypeError, ValueError):
            raise AjustementError(f"Ligne {i} : montant illisible.")
        if debit < 0 or credit < 0:
            raise AjustementError(f"Ligne {i} : les montants doivent être positifs.")
        if debit > 0 and credit > 0:
            raise AjustementError(f"Ligne {i} : une ligne mouvemente un seul sens (débit OU crédit).")
        if debit == 0 and credit == 0:
            raise AjustementError(f"Ligne {i} : la ligne ne porte aucun montant.")
        total_d += debit
        total_c += credit
    if abs(total_d - total_c) > TOLERANCE_EQUILIBRE:
        raise AjustementError(
            f"Écriture déséquilibrée : débits {total_d:,.2f} ≠ crédits {total_c:,.2f}. "
            "La partie double exige l'équilibre."
        )
    return round(total_d, 2), round(total_c, 2)


def effets_ecriture(lignes: list[dict]) -> dict:
    """Effet de l'écriture sur le résultat et les capitaux propres.

    Résultat = produits (7, créditeurs) − charges (6, débitrices) :
    créditer un 7 ou créditer un 6 augmente le résultat, débiter le diminue.
    Les capitaux propres bougent avec le résultat ET avec les mouvements
    directs des comptes de classe 1 (10x-14x).
    """
    effet_resultat = 0.0
    effet_cp_direct = 0.0
    for l in lignes:
        compte = str(l.get("compte") or "")
        delta = round(float(l.get("credit") or 0) - float(l.get("debit") or 0), 2)
        if compte.startswith(("6", "7")):
            effet_resultat += delta
        elif compte.startswith(("10", "11", "12", "13", "14")):
            effet_cp_direct += delta
    return {
        "effet_resultat": round(effet_resultat, 2),
        "effet_capitaux_propres": round(effet_resultat + effet_cp_direct, 2),
    }


def synthese_ajustements(ecritures: list[dict]) -> dict:
    """État récapitulatif des ajustements (ISA 450) — le « SUM ».

    Sépare les écritures passées (corrections comptabilisées) des écritures
    non passées (anomalies subsistantes), et cumule leurs effets sur le
    résultat et les capitaux propres.
    """
    passees = [e for e in ecritures if e.get("statut") == "passee"]
    non_passees = [e for e in ecritures if e.get("statut") != "passee"]
    refusees = [e for e in ecritures if e.get("statut") == "refusee"]

    def _cumul(items: list[dict]) -> dict:
        er, ecp, montant = 0.0, 0.0, 0.0
        for e in items:
            eff = effets_ecriture(e.get("lignes") or [])
            er += eff["effet_resultat"]
            ecp += eff["effet_capitaux_propres"]
            montant += float(e.get("total_debits") or 0)
        return {"effet_resultat": round(er, 2),
                "effet_capitaux_propres": round(ecp, 2),
                "montant_total": round(montant, 2)}

    return {
        "nb_total": len(ecritures),
        "nb_passees": len(passees),
        "nb_non_passees": len(non_passees),
        "nb_refusees": len(refusees),
        "passees": _cumul(passees),
        "non_passees": _cumul(non_passees),
    }


def balance_ajustee(soldes_bruts: dict[str, tuple[float, list[str]]],
                    ecritures: list[dict]) -> dict:
    """Balance ajustée = balance importée + écritures PASSÉES.

    soldes_bruts : {compte: (solde_net_debiteur_positif, sources)} — agrégé par
    le code appelant depuis la balance importée (provenance conservée).
    Retourne les lignes par compte (brut / ajustement / ajusté) et les totaux.
    Les comptes mouvementés par un ajustement mais absents de la balance
    apparaissent avec un solde brut nul.
    """
    ajustements_par_compte: dict[str, tuple[float, list[str]]] = {}
    for e in ecritures:
        if e.get("statut") != "passee":
            continue
        for l in e.get("lignes") or []:
            compte = str(l.get("compte") or "")
            delta = round(float(l.get("debit") or 0) - float(l.get("credit") or 0), 2)
            prev, srcs = ajustements_par_compte.get(compte, (0.0, []))
            src = l.get("donnee_id")
            ajustements_par_compte[compte] = (round(prev + delta, 2),
                                              srcs + ([src] if src else []))

    comptes = sorted(set(soldes_bruts) | set(ajustements_par_compte))
    lignes = []
    total_brut, total_ajuste, total_ajustements = 0.0, 0.0, 0.0
    for compte in comptes:
        brut, sources_brut = soldes_bruts.get(compte, (0.0, []))
        ajust, sources_ajust = ajustements_par_compte.get(compte, (0.0, []))
        ajuste = round(brut + ajust, 2)
        total_brut += brut
        total_ajustements += ajust
        total_ajuste += ajuste
        lignes.append({
            "compte": compte,
            "solde_brut": round(brut, 2),
            "ajustement": round(ajust, 2),
            "solde_ajuste": ajuste,
            "sources": sources_brut + sources_ajust,
        })
    return {
        "lignes": lignes,
        "nb_comptes": len(lignes),
        "nb_comptes_ajustes": len([l for l in lignes if l["ajustement"] != 0]),
        "total_brut": round(total_brut, 2),
        "total_ajustements": round(total_ajustements, 2),
        "total_ajuste": round(total_ajuste, 2),
    }

"""Définition des types de documents et préconditions des contrôles."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TypeDoc:
    id: str
    label: str
    description: str
    requis: bool = True  # obligatoire pour les cycles qui l'utilisent
    cycle: str | None = None  # None = partagé entre cycles


# ─── Catalogue des types ─────────────────────────────────────────────────────

TYPES_DOCUMENT: dict[str, TypeDoc] = {
    "grand_livre": TypeDoc(
        id="grand_livre",
        label="Grand livre comptable",
        description="Détail de toutes les écritures comptables (mouvements, dates, numéros de pièces).",
        requis=True,
    ),
    "balance": TypeDoc(
        id="balance",
        label="Balance des comptes",
        description="Résumé par compte : total débits, total crédits, solde final.",
        requis=True,
    ),
    "releve_bancaire": TypeDoc(
        id="releve_bancaire",
        label="Relevé bancaire",
        description="Relevé de compte bancaire pour rapprochement avec le solde comptable.",
        requis=True,  # NEP 330 : diligence requise en trésorerie
        cycle="tresorerie",
    ),
    "annexe": TypeDoc(
        id="annexe",
        label="Document annexe",
        description="Tout document complémentaire : PV, contrats, confirmations, etc.",
        requis=False,
        cycle=None,
    ),
}


# ─── Documents attendus par cycle ─────────────────────────────────────────────
#
# Un grand_livre + balance uniques peuvent couvrir TOUS les cycles simultanément
# car les contrôles filtrent par préfixe de compte. L'auditeur n'a pas besoin
# d'importer un fichier par cycle — un seul grand livre global suffit.

DOCUMENTS_PAR_CYCLE: dict[str, list[dict]] = {
    "tresorerie": [
        {
            "type": "grand_livre",
            "label": "Grand livre comptable",
            "requis": True,
            "description": "Doit contenir les comptes 5xx (caisse, banque, CCP).",
        },
        {
            "type": "balance",
            "label": "Balance des comptes",
            "requis": True,
            "description": "Résumé par compte avec soldes finaux.",
        },
        {
            "type": "releve_bancaire",
            "label": "Relevé bancaire",
            "requis": True,
            "description": "Requis — rapprochement bancaire obligatoire (NEP 330, TRESOR-RAPPROCH).",
        },
    ],
    "achats": [
        {
            "type": "grand_livre",
            "label": "Grand livre comptable",
            "requis": True,
            "description": "Doit contenir les comptes 40x (fournisseurs) et 60x-63x (charges).",
        },
        {
            "type": "balance",
            "label": "Balance des comptes",
            "requis": True,
            "description": "Résumé par compte avec soldes finaux.",
        },
    ],
    "ventes": [
        {
            "type": "grand_livre",
            "label": "Grand livre comptable",
            "requis": True,
            "description": "Doit contenir les comptes 41x (clients) et 70x-73x (produits).",
        },
        {
            "type": "balance",
            "label": "Balance des comptes",
            "requis": True,
            "description": "Résumé par compte avec soldes finaux.",
        },
    ],
}


# ─── Préconditions par contrôle ───────────────────────────────────────────────
#
# Clé = controle_ref, valeur = liste des types de fichiers requis.
# Si l'un des types est absent dans les fichiers importés → contrôle ignoré.

PRECONDITIONS_CONTROLES: dict[str, list[str]] = {
    # Trésorerie
    "TRESOR-BAL-EQUIL":     ["balance"],
    "TRESOR-GL-COHER":      ["grand_livre", "balance"],
    "TRESOR-SEQ-PIECES":    ["grand_livre"],
    "TRESOR-VARIATION":     ["balance"],
    "TRESOR-RAPPROCH":      ["balance", "releve_bancaire"],
    "TRESOR-SOLDE-ANORMAL": ["balance"],
    "TRESOR-ROUND":         ["grand_livre"],
    "TRESOR-CUT-OFF":       ["grand_livre"],
    # Achats
    "ACHAT-GL-COHER":       ["grand_livre", "balance"],
    "ACHAT-SEQ-FACTURES":   ["grand_livre"],
    "ACHAT-VARIATION":      ["balance"],
    "ACHAT-SOLDE-DEBITEUR": ["balance"],
    "ACHAT-DOUBLON":        ["grand_livre"],
    "ACHAT-CONCENTRATION":  ["grand_livre"],
    "ACHAT-AVOIR":          ["grand_livre"],
    "ACHAT-ROUND":          ["grand_livre"],
    "ACHAT-CUT-OFF":        ["grand_livre"],
    # Ventes
    "VENTE-GL-COHER":       ["grand_livre", "balance"],
    "VENTE-SEQ-FACTURES":   ["grand_livre"],
    "VENTE-VARIATION":      ["balance"],
    "VENTE-SOLDE-CREDITEUR":["balance"],
    "VENTE-DOUBLON":        ["grand_livre"],
    "VENTE-CONCENTRATION":  ["grand_livre"],
    "VENTE-AVOIR":          ["grand_livre"],
    "VENTE-ROUND":          ["grand_livre"],
    "VENTE-CUT-OFF":        ["grand_livre"],
    "VENTE-CREANCES-ECHUES":["grand_livre"],
}


def types_presents(fichiers: list[dict]) -> set[str]:
    """Retourne l'ensemble des types de documents présents dans la liste de fichiers."""
    types = set()
    for f in fichiers:
        # Priorité au champ type_document (nouveau), sinon type (ancien)
        t = f.get("type_document") or f.get("type") or ""
        if t:
            types.add(t)
    return types


def preconditions_ok(controle_ref: str, types: set[str]) -> tuple[bool, str]:
    """
    Vérifie si les préconditions d'un contrôle sont satisfaites.
    Retourne (ok, message_si_non_ok).
    """
    requis = PRECONDITIONS_CONTROLES.get(controle_ref, [])
    manquants = [r for r in requis if r not in types]
    if not manquants:
        return True, ""
    labels = [TYPES_DOCUMENT.get(m, TypeDoc(m, m, "")).label for m in manquants]
    return False, f"Données manquantes : {', '.join(labels)}"


def checklist_documents(cycles: list[str], fichiers: list[dict]) -> list[dict]:
    """
    Retourne la liste de contrôle des documents attendus pour les cycles sélectionnés,
    avec le statut d'import (importé ou manquant) pour chaque type.
    """
    types = types_presents(fichiers)
    seen: dict[str, dict] = {}  # type_doc → entrée (dédupliqué)

    for cycle in cycles:
        for doc in DOCUMENTS_PAR_CYCLE.get(cycle, []):
            key = doc["type"]
            if key not in seen:
                nb = sum(1 for f in fichiers
                         if (f.get("type_document") or f.get("type")) == key)
                seen[key] = {
                    **doc,
                    "importe": key in types,
                    "nb_fichiers": nb,
                    "cycles": [],
                }
            seen[key]["cycles"].append(cycle)

    return list(seen.values())

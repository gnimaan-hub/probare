"""Tests des écritures de journal — Journal Entry Testing (D1 — ISA 240).

Diligence obligatoire sur toute mission : l'auditeur teste les écritures de
journal pour détecter le risque de contournement des contrôles par la direction
(management override). Contrairement aux contrôles par cycle, le JET s'applique à
l'INTÉGRALITÉ du grand livre, écriture par écriture.

Tout est déterministe : chaque écriture reçoit un score de risque = somme
pondérée de signaux objectifs. Le LLM ne calcule jamais ce score ; il interprète
seulement la population signalée (via le mécanisme d'exceptions habituel).
"""
from __future__ import annotations
from .engine import (
    RowDict, _get_amount, _get_str, _parse_date, _exercice_end, _is_round,
    timedelta,
)


# Libellés vides ou fourre-tout : une écriture sans justification claire est un
# signal classique de manipulation (ISA 240).
LIBELLES_GENERIQUES = {
    "", "divers", "od", "o.d.", "operation diverse", "opération diverse",
    "operations diverses", "opérations diverses", "regularisation",
    "régularisation", "regul", "régul", "a ventiler", "à ventiler",
    "ecriture", "écriture", "ajustement", "divers a ventiler", "n/a", "na",
    "cf piece", "cf pièce", "voir piece", "voir pièce", ".", "-", "xxx", "test",
}


# Signaux de risque et leur pondération. Un poids élevé = signal fort de fraude.
SIGNAUX: dict[str, dict] = {
    "desequilibre": {
        "poids": 3,
        "libelle": "Pièce déséquilibrée (débits ≠ crédits)",
    },
    "sous_seuil": {
        "poids": 3,
        "libelle": "Montant juste sous le seuil de signification (contournement possible)",
    },
    "contrepartie": {
        "poids": 2,
        "libelle": "Contrepartie inhabituelle (produit/charge en lien direct avec la trésorerie)",
    },
    "weekend": {
        "poids": 2,
        "libelle": "Écriture datée un week-end",
    },
    "cutoff_tardif": {
        "poids": 2,
        "libelle": "Écriture dans les tout derniers jours de l'exercice",
    },
    "sans_piece": {
        "poids": 1,
        "libelle": "Écriture sans numéro de pièce",
    },
    "libelle_suspect": {
        "poids": 1,
        "libelle": "Libellé absent ou générique",
    },
    "montant_rond": {
        "poids": 1,
        "libelle": "Montant rond de grande ampleur",
    },
}

# Score à partir duquel une écriture est retenue pour revue ciblée.
SEUIL_SIGNALEMENT_DEFAUT = 3
# Fenêtre « tout derniers jours » de l'exercice (jours).
JOURS_CLOTURE_TARDIVE = 3
# Fraction du seuil en deçà de laquelle un montant est jugé « juste sous le seuil ».
FRACTION_SOUS_SEUIL = 0.90


def _classes(comptes: set[str]) -> set[str]:
    return {c[0] for c in comptes if c and c[0].isdigit()}


def _contrepartie_inhabituelle(classes: set[str]) -> bool:
    """Vrai si la pièce met en relation DIRECTE un compte de résultat (produit 7
    ou charge 6) avec la trésorerie (5) SANS compte de tiers (4).

    Une vente est normalement : client (41) → produit (70) puis banque (5) →
    client (41). Un produit directement soldé par la trésorerie court-circuite le
    tiers — schéma classique de chiffre d'affaires fictif ou détourné. Idem pour
    une charge payée sans passer par un fournisseur.
    """
    a_tresorerie = "5" in classes
    a_resultat = "6" in classes or "7" in classes
    a_tiers = "4" in classes
    return a_tresorerie and a_resultat and not a_tiers


def _entry_id(numero_piece: str, index: int) -> str:
    return numero_piece if numero_piece else f"§sans-piece-{index}"


def _grouper_par_piece(rows: list[RowDict]) -> list[dict]:
    """Regroupe les lignes du grand livre en écritures (une par numéro de pièce).

    Les lignes sans numéro de pièce forment chacune une écriture singleton
    (signalée `sans_piece`)."""
    groupes: dict[str, list[RowDict]] = {}
    singletons: list[tuple[int, RowDict]] = []
    for i, row in enumerate(rows):
        p = _get_str(row, "numero_piece")
        if p:
            groupes.setdefault(p, []).append(row)
        else:
            singletons.append((i, row))

    ecritures = []
    for piece, lignes in groupes.items():
        ecritures.append({"numero_piece": piece, "lignes": lignes})
    for i, row in singletons:
        ecritures.append({"numero_piece": "", "index": i, "lignes": [row]})
    return ecritures


def _analyser_ecriture(ecriture: dict, seuil: float, fin_exercice, index: int,
                       signaler_sans_piece: bool = True) -> dict:
    """Calcule les signaux et le score d'une écriture (déterministe)."""
    lignes = ecriture["lignes"]
    numero_piece = ecriture.get("numero_piece", "")

    total_debit = round(sum(_get_amount(r, "debit") for r in lignes), 2)
    total_credit = round(sum(_get_amount(r, "credit") for r in lignes), 2)
    # Montant de l'écriture = le plus grand des deux flux (ils sont égaux si équilibrée)
    montant = max(total_debit, total_credit)
    comptes = {_get_str(r, "compte") for r in lignes if _get_str(r, "compte")}
    classes = _classes(comptes)

    libelle = ""
    for r in lignes:
        lib = _get_str(r, "libelle")
        if lib:
            libelle = lib
            break

    date_str = ""
    dt = None
    for r in lignes:
        ds = _get_str(r, "date")
        if ds:
            date_str = ds
            dt = _parse_date(ds)
            break

    signaux: list[str] = []

    # Déséquilibre : seulement si la pièce comporte plusieurs lignes (une pièce
    # correctement saisie s'équilibre). Un singleton sans contrepartie n'est pas
    # « déséquilibré » au sens comptable — il est signalé par sans_piece.
    if len(lignes) >= 2 and abs(total_debit - total_credit) > 0.01:
        signaux.append("desequilibre")

    if seuil and seuil > 0 and (FRACTION_SOUS_SEUIL * seuil) <= montant < seuil:
        signaux.append("sous_seuil")

    if len(lignes) >= 2 and _contrepartie_inhabituelle(classes):
        signaux.append("contrepartie")

    if dt is not None and dt.weekday() >= 5:
        signaux.append("weekend")

    if dt is not None and fin_exercice is not None:
        debut = fin_exercice - timedelta(days=JOURS_CLOTURE_TARDIVE - 1)
        if debut <= dt <= fin_exercice:
            signaux.append("cutoff_tardif")

    if not numero_piece and signaler_sans_piece:
        signaux.append("sans_piece")

    if libelle.strip().lower() in LIBELLES_GENERIQUES:
        signaux.append("libelle_suspect")

    if montant > 0 and _is_round(montant, 1_000_000):
        signaux.append("montant_rond")

    score = sum(SIGNAUX[s]["poids"] for s in signaux)

    # Provenance : ids des DonneeSourcee des lignes (compte + montants)
    sources = []
    for r in lignes:
        for champ in ("compte", "numero_piece", "date", "debit", "credit", "solde", "libelle"):
            d = r.get(champ)
            if d:
                sources.append(d.id)

    return {
        "cle": _entry_id(numero_piece, index),
        "numero_piece": numero_piece,
        "date_piece": date_str,
        "libelle": libelle,
        "montant": montant,
        "comptes": sorted(comptes),
        "nb_lignes": len(lignes),
        "signaux": signaux,
        "score": score,
        "sources": list(dict.fromkeys(sources)),
    }


def analyser_journal(
    rows: list[RowDict],
    seuil: float,
    exercice: str | None,
    seuil_signalement: int = SEUIL_SIGNALEMENT_DEFAUT,
) -> dict:
    """Analyse JET du grand livre complet.

    Retourne la population totale, les écritures signalées (score ≥ seuil), le
    décompte par signal et la liste triée par score décroissant.
    """
    fin_exercice = _exercice_end(exercice)
    ecritures = _grouper_par_piece(rows)

    # Garde-fou : si le grand livre ne porte quasiment aucun numéro de pièce,
    # c'est une caractéristique du fichier (export sans référence), pas une
    # anomalie de masse. On désactive alors le signal « sans_piece ».
    nb_avec_piece = sum(1 for e in ecritures if e.get("numero_piece"))
    signaler_sans_piece = (
        len(ecritures) > 0 and (nb_avec_piece / len(ecritures)) >= 0.5
    )

    analysees = [_analyser_ecriture(e, seuil, fin_exercice, i, signaler_sans_piece)
                 for i, e in enumerate(ecritures)]
    signalees = [e for e in analysees if e["score"] >= seuil_signalement]
    signalees.sort(key=lambda e: (-e["score"], -e["montant"]))

    par_signal: dict[str, int] = {}
    for e in analysees:
        for s in e["signaux"]:
            par_signal[s] = par_signal.get(s, 0) + 1

    return {
        "nb_ecritures": len(analysees),
        "nb_signalees": len(signalees),
        "seuil_signalement": seuil_signalement,
        "seuil_signification": seuil or None,
        "sans_piece_desactive": not signaler_sans_piece,
        "par_signal": par_signal,
        "signalees": signalees,
        "signaux_libelles": {k: v["libelle"] for k, v in SIGNAUX.items()},
    }

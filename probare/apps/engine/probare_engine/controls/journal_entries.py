"""Tests des écritures de journal — Journal Entry Testing (D1 — ISA 240).

Diligence obligatoire sur toute mission : l'auditeur teste les écritures de
journal pour détecter le risque de contournement des contrôles par la direction
(management override). Contrairement aux contrôles par cycle, le JET s'applique à
l'INTÉGRALITÉ du grand livre, écriture par écriture.

Tout est déterministe : chaque écriture reçoit un score de risque = somme
pondérée de signaux objectifs. Le LLM ne calcule jamais ce score ; il interprète
seulement la population signalée (via le mécanisme d'exceptions habituel).

Calibrage (D1b) — un signal qui se déclenche sur une grande partie de la
population ne désigne plus un risque : il décrit une caractéristique du fichier
ou du calendrier de l'entité. Trois mécanismes protègent la sélection :
l'identité de l'écriture (pièce + date), les jours non ouvrés déduits du grand
livre, et la neutralisation des signaux non discriminants.
"""
from __future__ import annotations
from collections import Counter
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
        "libelle": "Écriture datée un jour non ouvré de l'entité",
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

JOURS_SEMAINE = ("lundi", "mardi", "mercredi", "jeudi", "vendredi",
                 "samedi", "dimanche")
# Convention retenue quand le grand livre ne permet pas de déduire le calendrier.
JOURS_NON_OUVRES_DEFAUT = frozenset({5, 6})  # samedi, dimanche
# Population minimale d'écritures datées pour déduire le calendrier de l'entité.
POPULATION_MIN_CALENDRIER = 60
# Un jour portant moins que cette fraction de l'activité moyenne quotidienne est
# tenu pour non ouvré.
FRACTION_JOUR_NON_OUVRE = 0.20
# Au-delà de ce nombre de jours « creux », la datation du grand livre est trop
# concentrée pour que la notion de jour non ouvré ait un sens.
MAX_JOURS_NON_OUVRES = 3

# Un signal déclenché sur plus de cette part de la population ne discrimine plus
# rien : il décrit le fichier, pas un risque. Il est neutralisé et signalé.
TAUX_SIGNAL_NON_DISCRIMINANT = 0.30
# En deçà de cette population, la statistique est trop instable pour neutraliser.
POPULATION_MIN_NEUTRALISATION = 100


def _jours_non_ouvres(dates: list) -> tuple[frozenset[int], bool]:
    """Déduit du grand livre les jours de la semaine où l'entité ne travaille pas.

    Le calendrier d'exploitation n'est pas universel : la semaine ouvrée court du
    dimanche au jeudi à Djibouti, du lundi au vendredi en France. Coder
    « samedi et dimanche » signalerait 17 % d'un grand livre djiboutien (tous les
    dimanches, jours pleinement ouvrés) tout en laissant passer les vendredis.

    Le calendrier est donc lu dans les données : un jour portant une activité
    marginale au regard de la moyenne quotidienne est un jour non ouvré. Retourne
    (jours, déduit) ; `déduit` faux signale le repli sur la convention par défaut.
    """
    par_jour = Counter(d.weekday() for d in dates)
    total = sum(par_jour.values())
    if total < POPULATION_MIN_CALENDRIER:
        return JOURS_NON_OUVRES_DEFAUT, False
    plancher = FRACTION_JOUR_NON_OUVRE * total / len(JOURS_SEMAINE)
    jours = frozenset(j for j in range(len(JOURS_SEMAINE))
                      if par_jour.get(j, 0) < plancher)
    if len(jours) > MAX_JOURS_NON_OUVRES:
        return JOURS_NON_OUVRES_DEFAUT, False
    # Un ensemble vide est un résultat valable : l'entité comptabilise tous les
    # jours de la semaine, le signal ne se déclenche jamais.
    return jours, True


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


def _entry_id(numero_piece: str, date_piece: str, index: int) -> str:
    if not numero_piece:
        return f"§sans-piece-{index}"
    # La date fait partie de l'identité : un même numéro peut porter plusieurs
    # écritures à des dates différentes (numérotation réattribuée par journal).
    return f"{numero_piece}@{date_piece}" if date_piece else numero_piece


def _grouper_en_ecritures(rows: list[RowDict]) -> tuple[list[dict], int]:
    """Regroupe les lignes du grand livre en écritures.

    L'identité d'une écriture est le couple **(numéro de pièce, date)**, non le
    seul numéro de pièce : une écriture comptable porte une date unique, et les
    numéros de pièce sont fréquemment réattribués d'un journal à l'autre — les
    à-nouveaux d'ouverture, notamment, sont renumérotés à partir de 1 et
    collisionnent avec les écritures de l'exercice. Regrouper sur le seul numéro
    agglomère alors des écritures étrangères les unes aux autres et fabrique un
    déséquilibre débits/crédits sur la quasi-totalité de la population.

    La clé (pièce, date) est strictement plus fine : sur un grand livre dont la
    numérotation est fiable, elle donne le même découpage.

    Les lignes sans numéro de pièce forment chacune une écriture singleton
    (signalée `sans_piece`). Retourne (écritures, nb de numéros de pièce
    réutilisés à des dates différentes) — ce second terme documente pourquoi le
    découpage ne suit pas le seul numéro.
    """
    groupes: dict[tuple[str, str], list[RowDict]] = {}
    singletons: list[tuple[int, RowDict]] = []
    dates_par_piece: dict[str, set[str]] = {}
    for i, row in enumerate(rows):
        p = _get_str(row, "numero_piece")
        if p:
            d = _get_str(row, "date")
            groupes.setdefault((p, d), []).append(row)
            dates_par_piece.setdefault(p, set()).add(d)
        else:
            singletons.append((i, row))

    ecritures = []
    for (piece, _date), lignes in groupes.items():
        ecritures.append({"numero_piece": piece, "lignes": lignes})
    for i, row in singletons:
        ecritures.append({"numero_piece": "", "index": i, "lignes": [row]})
    reutilises = sum(1 for dates in dates_par_piece.values() if len(dates) > 1)
    return ecritures, reutilises


def _analyser_ecriture(ecriture: dict, seuil: float, fin_exercice, index: int,
                       signaler_sans_piece: bool = True,
                       jours_non_ouvres: frozenset[int] = JOURS_NON_OUVRES_DEFAUT) -> dict:
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

    if dt is not None and dt.weekday() in jours_non_ouvres:
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
        "cle": _entry_id(numero_piece, date_str, index),
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


def _signaux_non_discriminants(analysees: list[dict]) -> dict[str, float]:
    """Signaux déclenchés sur une part trop large de la population.

    Généralise le garde-fou du signal « sans pièce » : un signal qui touche près
    de tout le grand livre ne désigne pas un risque, il décrit le fichier (format
    d'export, calendrier de l'entité, identification des écritures). Le laisser
    peser noierait la sélection sous des écritures indistinctes. Le signal est
    neutralisé — mais le taux est retourné pour être versé au dossier : c'est un
    constat sur la qualité des données, pas un silence.
    """
    total = len(analysees)
    if total < POPULATION_MIN_NEUTRALISATION:
        return {}
    compte: Counter = Counter()
    for e in analysees:
        compte.update(e["signaux"])
    return {s: n / total for s, n in compte.items()
            if n / total > TAUX_SIGNAL_NON_DISCRIMINANT}


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
    ecritures, pieces_reutilisees = _grouper_en_ecritures(rows)

    # Garde-fou : si le grand livre ne porte quasiment aucun numéro de pièce,
    # c'est une caractéristique du fichier (export sans référence), pas une
    # anomalie de masse. On désactive alors le signal « sans_piece ».
    nb_avec_piece = sum(1 for e in ecritures if e.get("numero_piece"))
    signaler_sans_piece = (
        len(ecritures) > 0 and (nb_avec_piece / len(ecritures)) >= 0.5
    )

    # Calendrier d'exploitation lu dans les données (une date par écriture).
    dates = []
    for e in ecritures:
        for r in e["lignes"]:
            dt = _parse_date(_get_str(r, "date"))
            if dt is not None:
                dates.append(dt)
                break
    jours_non_ouvres, jours_deduits = _jours_non_ouvres(dates)

    analysees = [
        _analyser_ecriture(e, seuil, fin_exercice, i, signaler_sans_piece,
                           jours_non_ouvres)
        for i, e in enumerate(ecritures)
    ]

    # Neutralisation des signaux non discriminants, puis recalcul des scores.
    neutralises = _signaux_non_discriminants(analysees)
    if neutralises:
        for e in analysees:
            e["signaux"] = [s for s in e["signaux"] if s not in neutralises]
            e["score"] = sum(SIGNAUX[s]["poids"] for s in e["signaux"])

    signalees = [e for e in analysees if e["score"] >= seuil_signalement]
    signalees.sort(key=lambda e: (-e["score"], -e["montant"], e["cle"]))

    par_signal: dict[str, int] = {}
    for e in analysees:
        for s in e["signaux"]:
            par_signal[s] = par_signal.get(s, 0) + 1

    return {
        "nb_ecritures": len(analysees),
        "nb_signalees": len(signalees),
        "taux_signalement": round(len(signalees) / len(analysees), 4) if analysees else 0.0,
        "seuil_signalement": seuil_signalement,
        "seuil_signification": seuil or None,
        "sans_piece_desactive": not signaler_sans_piece,
        "signaux_neutralises": {s: round(t, 4) for s, t in neutralises.items()},
        "jours_non_ouvres": sorted(jours_non_ouvres),
        "jours_non_ouvres_libelles": [JOURS_SEMAINE[j] for j in sorted(jours_non_ouvres)],
        "jours_non_ouvres_deduits": jours_deduits,
        "numeros_piece_reutilises": pieces_reutilisees,
        "par_signal": par_signal,
        "signalees": signalees,
        "signaux_libelles": {k: v["libelle"] for k, v in SIGNAUX.items()},
    }

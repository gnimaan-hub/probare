"""Cadrage des états financiers PRÉSENTÉS avec la balance auditée (P2-a).

C'est la diligence d'audit réelle sur les états financiers : l'entité publie un
bilan et un compte de résultat ; l'auditeur doit vérifier que ces états
**se raccordent à la comptabilité auditée**, poste par poste. Sans ce
rapprochement, un dossier peut être impeccable sur la balance et l'opinion porter
sur des états qui ne lui correspondent pas.

Le pivot est la **feuille maîtresse par rubrique** (M5) : elle donne, pour chaque
rubrique d'états financiers, le montant issu de la balance ajustée. Chaque poste
présenté par le client est rattaché à une rubrique ; l'écart est calculé en
Python, et tout écart supérieur au seuil devient une exception standard —
interprétée par l'IA comme n'importe quelle autre.

Conventions de signe — le point à ne pas se tromper :

- La feuille maîtresse raisonne en **solde net débiteur positif** (convention
  interne, héritée de la balance ajustée).
- Le client, lui, publie des montants **positifs des deux côtés** du bilan.
- Le rapprochement se fait donc côté par côté : chaque poste présenté déclare son
  `cote` (actif, passif, charges, produits), et le montant attendu vaut
  `montant_ajuste × signe_du_cote`. C'est ce qui permet de traiter correctement
  les rubriques à double sens (comptes de tiers), dont le côté de présentation
  dépend du signe du solde et non du plan.

Module de calcul pur : aucune I/O, aucun appel LLM.
"""
from __future__ import annotations

import unicodedata

# Côtés de présentation d'un état financier.
COTE_ACTIF = "actif"
COTE_PASSIF = "passif"
COTE_CHARGES = "charges"
COTE_PRODUITS = "produits"

COTES: dict[str, str] = {
    COTE_ACTIF: "Bilan — Actif",
    COTE_PASSIF: "Bilan — Passif",
    COTE_CHARGES: "Compte de résultat — Charges",
    COTE_PRODUITS: "Compte de résultat — Produits",
}

COTES_BILAN = (COTE_ACTIF, COTE_PASSIF)
COTES_RESULTAT = (COTE_CHARGES, COTE_PRODUITS)

# Signe à appliquer au montant net débiteur pour obtenir le montant tel qu'il est
# PRÉSENTÉ de ce côté-là (les deux côtés du bilan se publient en positif).
_SIGNE_COTE = {COTE_ACTIF: 1, COTE_CHARGES: 1, COTE_PASSIF: -1, COTE_PRODUITS: -1}

# En deçà, l'écart relève de l'arrondi de présentation (les états sont souvent
# publiés au millier près), pas d'une anomalie.
TOLERANCE_ARRONDI = 1.0

STATUT_CONCORDANT = "concordant"
STATUT_ECART = "ecart"
STATUT_ECART_SIGNIFICATIF = "ecart_significatif"
STATUT_NON_RATTACHE = "non_rattache"
STATUT_ABSENT_DES_EF = "absent_des_ef"


def etat_du_cote(cote: str) -> str:
    """« bilan » ou « resultat » — l'état auquel appartient un côté."""
    return "bilan" if cote in COTES_BILAN else "resultat"


def _normaliser(texte: str) -> str:
    """Minuscules sans accents ni ponctuation, pour comparer des libellés."""
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", texte or "")
                           if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in sans_accents).split()).lower()


_MOTS_VIDES = {"et", "de", "des", "du", "la", "le", "les", "aux", "au", "a", "en",
               "sur", "autres", "autre", "comptes", "compte", "rattaches"}


def suggerer_rubrique(libelle: str, rubriques: list[dict], cote: str | None = None) -> str | None:
    """Rubrique la plus plausible pour un libellé de poste présenté.

    Rapprochement lexical déterministe (aucun LLM) : égalité des libellés
    normalisés, puis recouvrement de mots significatifs. Rend `None` dès que
    le résultat est ambigu — un mauvais rattachement silencieux produirait un
    écart imaginaire, ce qui est pire que pas de rattachement du tout.
    """
    cible = _normaliser(libelle)
    if not cible:
        return None
    candidates = rubriques
    if cote:
        types_admis = {
            COTE_ACTIF: {"bilan_actif", "bilan_mixte"},
            COTE_PASSIF: {"bilan_passif", "bilan_mixte"},
            COTE_CHARGES: {"resultat_charges"},
            COTE_PRODUITS: {"resultat_produits"},
        }.get(cote)
        if types_admis:
            candidates = [r for r in rubriques if r.get("type") in types_admis]

    for r in candidates:
        if _normaliser(r.get("libelle", "")) == cible:
            return r["ref"]

    mots_cible = {m for m in cible.split() if m not in _MOTS_VIDES and len(m) > 2}
    if not mots_cible:
        return None
    scores: list[tuple[float, str]] = []
    for r in candidates:
        mots_r = {m for m in _normaliser(r.get("libelle", "")).split()
                  if m not in _MOTS_VIDES and len(m) > 2}
        if not mots_r:
            continue
        commun = mots_cible & mots_r
        if not commun:
            continue
        scores.append((len(commun) / max(len(mots_cible), len(mots_r)), r["ref"]))
    if not scores:
        return None
    scores.sort(reverse=True)
    meilleur, ref = scores[0]
    if meilleur < 0.5:
        return None
    # Ambiguïté : deux rubriques également plausibles → on laisse trancher l'auditeur.
    if len(scores) > 1 and abs(scores[1][0] - meilleur) < 1e-9:
        return None
    return ref


def montant_audite_pour(rubrique: dict, cote: str) -> float:
    """Montant de la feuille maîtresse tel qu'il devrait être PRÉSENTÉ de ce côté."""
    return round(float(rubrique.get("montant_ajuste") or 0.0) * _SIGNE_COTE[cote], 2)


def _pct(ecart: float, base: float) -> float | None:
    if not base:
        return None
    return round(ecart / abs(base) * 100, 2)


def rapprocher(postes: list[dict], matrice: dict, seuil: float | None = None) -> dict:
    """Rapproche les états financiers présentés de la feuille maîtresse (M5).

    Args:
        postes: postes présentés par le client — `cote`, `libelle`, `montant`
            (tel que publié, positif), `rubrique_ref` (rattachement, facultatif).
        matrice: sortie de `leadsheets.construire_feuilles_maitresses`.
        seuil: seuil de signification. Au-delà, l'écart est significatif et
            justifie une exception.

    Returns:
        {lignes, non_rattaches, totaux, equilibre_bilan, coherence_resultat, synthese}
    """
    seuil = float(seuil or 0.0)
    rubriques = {r["ref"]: r for r in (matrice.get("rubriques") or [])}

    # ── Regroupement des postes présentés par (rubrique, côté) ──────────────
    # Un même poste publié peut agréger plusieurs rubriques, et une rubrique
    # peut être éclatée en plusieurs lignes de présentation : on compare des
    # sommes, jamais des lignes isolées.
    groupes: dict[tuple[str, str], dict] = {}
    non_rattaches: list[dict] = []
    for p in postes:
        cote = p.get("cote")
        if cote not in COTES:
            continue
        montant = round(float(p.get("montant") or 0.0), 2)
        ref = p.get("rubrique_ref")
        if not ref or ref not in rubriques:
            non_rattaches.append({
                "id": p.get("id"), "libelle": p.get("libelle"), "cote": cote,
                "montant": montant, "statut": STATUT_NON_RATTACHE,
            })
            continue
        g = groupes.setdefault((ref, cote), {"montant_presente": 0.0, "postes": []})
        g["montant_presente"] = round(g["montant_presente"] + montant, 2)
        g["postes"].append({"id": p.get("id"), "libelle": p.get("libelle"), "montant": montant})

    lignes: list[dict] = []
    for (ref, cote), g in groupes.items():
        rub = rubriques[ref]
        audite = montant_audite_pour(rub, cote)
        ecart = round(g["montant_presente"] - audite, 2)
        significatif = bool(seuil and abs(ecart) > seuil)
        if abs(ecart) <= TOLERANCE_ARRONDI:
            statut = STATUT_CONCORDANT
        elif significatif:
            statut = STATUT_ECART_SIGNIFICATIF
        else:
            statut = STATUT_ECART
        lignes.append({
            "rubrique_ref": ref,
            "rubrique_libelle": rub.get("libelle"),
            "groupe": rub.get("groupe"),
            "cote": cote,
            "cote_libelle": COTES[cote],
            "postes": g["postes"],
            "montant_presente": g["montant_presente"],
            "montant_audite": audite,
            "ecart": ecart,
            "ecart_pct": _pct(ecart, audite),
            "statut": statut,
            "sources": [f"feuille_maitresse:{ref}"],
        })

    # ── Rubriques auditées non nulles qu'aucun poste présenté ne reprend ─────
    # Un poste significatif de la balance absent des états publiés est une
    # anomalie d'exhaustivité, pas une simple omission de saisie.
    refs_rapproches = {ref for ref, _ in groupes}
    absentes: list[dict] = []
    if postes:
        for ref, rub in rubriques.items():
            if ref in refs_rapproches:
                continue
            montant = round(float(rub.get("montant_ajuste") or 0.0), 2)
            if abs(montant) <= max(TOLERANCE_ARRONDI, seuil):
                continue
            cote = _cote_naturel(rub, montant)
            absentes.append({
                "rubrique_ref": ref, "rubrique_libelle": rub.get("libelle"),
                "groupe": rub.get("groupe"), "cote": cote, "cote_libelle": COTES[cote],
                "montant_audite": montant_audite_pour(rub, cote),
                "statut": STATUT_ABSENT_DES_EF,
                "sources": [f"feuille_maitresse:{ref}"],
            })

    # ── Totaux présentés et contrôles d'ensemble ────────────────────────────
    def _total(cote: str) -> float:
        return round(sum(round(float(p.get("montant") or 0.0), 2)
                         for p in postes if p.get("cote") == cote), 2)

    actif, passif = _total(COTE_ACTIF), _total(COTE_PASSIF)
    charges, produits = _total(COTE_CHARGES), _total(COTE_PRODUITS)
    resultat_presente = round(produits - charges, 2)
    resultat_audite = round(float((matrice.get("totaux") or {}).get("resultat") or 0.0), 2)

    ecart_bilan = round(actif - passif, 2)
    ecart_resultat = round(resultat_presente - resultat_audite, 2)

    ecarts_significatifs = [l for l in lignes if l["statut"] == STATUT_ECART_SIGNIFICATIF]
    lignes.sort(key=lambda l: (l["cote"], -abs(l["ecart"])))
    absentes.sort(key=lambda l: -abs(l["montant_audite"]))

    return {
        "lignes": lignes,
        "non_rattaches": non_rattaches,
        "rubriques_absentes": absentes,
        "totaux": {
            "actif_presente": actif, "passif_presente": passif,
            "charges_presente": charges, "produits_presente": produits,
            "resultat_presente": resultat_presente,
            "resultat_audite": resultat_audite,
        },
        "equilibre_bilan": {
            "ecart": ecart_bilan,
            "equilibre": abs(ecart_bilan) <= TOLERANCE_ARRONDI,
            "applicable": bool(actif or passif),
            # Cause la plus fréquente d'un bilan présenté déséquilibré : le
            # résultat de l'exercice n'a pas été porté aux capitaux propres.
            # L'écart vaut alors exactement le résultat — le dire évite de faire
            # chercher une anomalie là où il n'y a qu'une affectation à faire.
            "explique_par_resultat": bool(
                abs(ecart_bilan) > TOLERANCE_ARRONDI and resultat_audite
                and abs(ecart_bilan - resultat_audite) <= TOLERANCE_ARRONDI),
        },
        "coherence_resultat": {
            "ecart": ecart_resultat,
            "coherent": abs(ecart_resultat) <= TOLERANCE_ARRONDI,
            "applicable": bool(charges or produits),
        },
        "synthese": {
            "nb_postes": len(postes),
            "nb_lignes": len(lignes),
            "nb_concordants": sum(1 for l in lignes if l["statut"] == STATUT_CONCORDANT),
            "nb_ecarts": sum(1 for l in lignes if l["statut"] == STATUT_ECART),
            "nb_ecarts_significatifs": len(ecarts_significatifs),
            "nb_non_rattaches": len(non_rattaches),
            "nb_absentes": len(absentes),
            "ecart_total_absolu": round(sum(abs(l["ecart"]) for l in lignes), 2),
            "seuil": seuil or None,
            "cadre": (not ecarts_significatifs and not non_rattaches and not absentes
                      and abs(ecart_bilan) <= TOLERANCE_ARRONDI
                      and abs(ecart_resultat) <= TOLERANCE_ARRONDI),
        },
    }


def _cote_naturel(rubrique: dict, montant_ajuste: float) -> str:
    """Côté de présentation attendu d'une rubrique, d'après son type — et, pour
    les rubriques à double sens, d'après le signe de son solde."""
    type_r = rubrique.get("type")
    if type_r == "bilan_actif":
        return COTE_ACTIF
    if type_r == "bilan_passif":
        return COTE_PASSIF
    if type_r == "resultat_charges":
        return COTE_CHARGES
    if type_r == "resultat_produits":
        return COTE_PRODUITS
    return COTE_ACTIF if montant_ajuste >= 0 else COTE_PASSIF


def valider_poste(poste: dict) -> None:
    """Vérifie un poste présenté avant enregistrement. Lève ValueError sinon."""
    if poste.get("cote") not in COTES:
        raise ValueError(f"Côté inconnu : {poste.get('cote')}. "
                         f"Valeurs admises : {sorted(COTES)}.")
    if not str(poste.get("libelle") or "").strip():
        raise ValueError("Le libellé du poste présenté est obligatoire.")
    try:
        float(poste.get("montant") or 0.0)
    except (TypeError, ValueError):
        raise ValueError(f"Montant illisible pour « {poste.get('libelle')} ».")

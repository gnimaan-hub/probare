"""Feuilles maîtresses par rubrique d'états financiers (M5) — 100 % Python.

Une feuille maîtresse relie un poste d'états financiers aux comptes qui le
composent, et chaque compte à ses montants : solde importé, ajustements passés,
solde audité, comparatif N-1 et variation. C'est le pivot d'un dossier d'audit :
depuis la rubrique on redescend au compte, et du compte on remonte aux travaux
(contrôles, exceptions, sondages, circularisations, écritures d'ajustement).

Aucun montant ne vient du LLM : tout est agrégé ici à partir de la balance
ajustée (elle-même bâtie sur des `DonneeSourcee`), et la provenance de chaque
ligne est conservée dans `sources`.

Convention de signe : tout est exprimé en **solde net débiteur positif**, comme
`ajustements.balance_ajustee`. Le signe de présentation (actif/charges tels
quels, passif/produits en valeur absolue) est calculé en plus, dans
`montant_presente`, sans jamais remplacer le montant brut de calcul.
"""
from __future__ import annotations

from ..rubriques import (
    Rubrique, plan_rubriques, plan_est_approxime, rubrique_du_compte,
    rubrique_as_dict, index_par_ref,
    TYPE_BILAN_ACTIF, TYPE_BILAN_PASSIF, TYPE_BILAN_MIXTE,
    TYPE_RESULTAT_CHARGES, TYPE_RESULTAT_PRODUITS, TYPE_NON_AFFECTE,
)

# En deçà de ce montant, un solde est traité comme nul (arrondis d'agrégation).
TOLERANCE_BOUCLAGE = 0.01

# Une variation n'est signalée que si elle dépasse ce taux ET le seuil fourni.
TAUX_VARIATION_NOTABLE = 0.10


def _pct(valeur: float, base: float) -> float | None:
    """Variation relative — None si la base est nulle (division impossible).

    Une rubrique nouvelle (rien en N-1) n'a pas de pourcentage de variation :
    dire « +100 % » serait un artefact, pas une information.
    """
    if abs(base) < TOLERANCE_BOUCLAGE:
        return None
    return round(valeur / abs(base), 4)


def _cycles_des_controles(refs: set[str]) -> dict[str, str]:
    """controle_ref → cycle, d'après le registre des contrôles."""
    from ..controls.registry import REGISTRE
    return {ref: REGISTRE[ref].cycle for ref in refs if ref in REGISTRE}


def _rattacher_travaux(
    rubriques_ordonnees: list[Rubrique],
    comptes_par_rubrique: dict[str, list[str]],
    travaux: dict | None,
) -> dict[str, dict]:
    """Rattache chaque travail d'audit aux rubriques qu'il concerne.

    Trois modes de rattachement, du plus précis au plus large :
    - par COMPTE pour les circularisations et les lignes d'écritures
      d'ajustement (elles portent un numéro de compte) ;
    - par PRÉFIXE pour les sondages (ils portent la population ciblée) ;
    - par CYCLE pour les résultats de contrôles et les exceptions (elles ne
      portent que la référence du contrôle, dont le registre donne le cycle).
    """
    vide = {"controles": [], "exceptions_ouvertes": [], "exceptions_tranchees": [],
            "sondages": [], "circularisations": [], "ajustements": []}
    resultat: dict[str, dict] = {r.ref: {k: [] for k in vide} for r in rubriques_ordonnees}
    if not travaux:
        return resultat

    par_compte: dict[str, str] = {}
    for ref, comptes in comptes_par_rubrique.items():
        for c in comptes:
            par_compte[c] = ref
    par_cycle: dict[str, list[str]] = {}
    for r in rubriques_ordonnees:
        for cyc in r.cycles:
            par_cycle.setdefault(cyc, []).append(r.ref)

    def _ajouter(ref_rubrique: str | None, cle: str, item: dict) -> None:
        if ref_rubrique and ref_rubrique in resultat:
            resultat[ref_rubrique][cle].append(item)

    # ── Circularisations : rattachement par compte ──────────────────────────
    for c in travaux.get("circularisations") or []:
        _ajouter(par_compte.get(str(c.get("compte") or "")), "circularisations", {
            "id": c.get("id"), "compte": c.get("compte"), "tiers": c.get("libelle"),
            "statut": c.get("statut"), "solde_comptable": c.get("solde_comptable"),
            "solde_confirme": c.get("solde_confirme"), "ecart": c.get("ecart"),
        })

    # ── Écritures d'ajustement : rattachement par compte de chaque ligne ────
    for e in travaux.get("ajustements") or []:
        refs_touchees: set[str] = set()
        for l in e.get("lignes") or []:
            ref_r = par_compte.get(str(l.get("compte") or ""))
            if ref_r:
                refs_touchees.add(ref_r)
        for ref_r in refs_touchees:
            _ajouter(ref_r, "ajustements", {
                "id": e.get("id"), "libelle": e.get("libelle"),
                "statut": e.get("statut"), "statut_libelle": e.get("statut_libelle"),
                "total_debits": e.get("total_debits"),
            })

    # ── Sondages : rattachement par préfixes de population ──────────────────
    for s in travaux.get("sondages") or []:
        prefixes = tuple(str(p) for p in (s.get("prefixes") or []) if p)
        refs_touchees = set()
        if prefixes:
            for compte, ref_r in par_compte.items():
                if compte.startswith(prefixes):
                    refs_touchees.add(ref_r)
        elif s.get("cycle"):
            refs_touchees = set(par_cycle.get(s["cycle"], []))
        for ref_r in refs_touchees:
            _ajouter(ref_r, "sondages", {
                "id": s.get("id"), "libelle": s.get("libelle"), "cycle": s.get("cycle"),
                "taille_echantillon": s.get("taille_echantillon"),
                "nb_anomalies": s.get("nb_anomalies"), "statut": s.get("statut"),
            })

    # ── Contrôles et exceptions : rattachement par cycle du contrôle ────────
    resultats = travaux.get("resultats") or []
    exceptions = travaux.get("exceptions") or []
    cycles = _cycles_des_controles(
        {str(x.get("controle_ref")) for x in [*resultats, *exceptions] if x.get("controle_ref")})

    for r in resultats:
        cyc = cycles.get(str(r.get("controle_ref")))
        for ref_r in par_cycle.get(cyc, []) if cyc else []:
            _ajouter(ref_r, "controles", {
                "controle_ref": r.get("controle_ref"), "statut": r.get("statut"),
                "valeur": r.get("valeur"),
            })

    for e in exceptions:
        cyc = cycles.get(str(e.get("controle_ref")))
        cle = "exceptions_tranchees" if e.get("statut") == "tranchee" else "exceptions_ouvertes"
        for ref_r in par_cycle.get(cyc, []) if cyc else []:
            _ajouter(ref_r, cle, {
                "id": e.get("id"), "controle_ref": e.get("controle_ref"),
                "severite": e.get("severite"), "statut": e.get("statut"),
                "description": e.get("description"),
                "montant_incidence": e.get("montant_incidence"),
                "montant_estime": e.get("montant_estime"),
            })

    return resultat


def construire_feuilles_maitresses(
    balance_ajustee: dict,
    soldes_n1: dict[str, tuple[float, list[str]]] | None = None,
    referentiel_comptable: str | None = None,
    overrides: dict[str, str] | None = None,
    libelles_comptes: dict[str, str] | None = None,
    travaux: dict | None = None,
    seuil_variation: float | None = None,
) -> dict:
    """Construit la matrice des feuilles maîtresses.

    Args:
        balance_ajustee: sortie de `ajustements.balance_ajustee` (lignes par
            compte : solde brut, ajustement, solde ajusté, sources).
        soldes_n1: {compte: (solde_net_debiteur, sources)} de l'exercice N-1.
        referentiel_comptable: code du référentiel de l'entité (plan servi).
        overrides: réaffectations décidées par l'auditeur, {compte: rubrique_ref}.
        libelles_comptes: {compte: libellé} issu de la balance importée.
        travaux: {resultats, exceptions, sondages, circularisations, ajustements}
            pour le rattachement croisé.
        seuil_variation: seuil de planification — au-delà (et au-delà de 10 %),
            la variation N/N-1 est marquée comme notable.

    Returns:
        Matrice {rubriques, groupes, totaux, bouclage, comptes_non_affectes}.
    """
    plan = plan_rubriques(referentiel_comptable)
    par_ref = index_par_ref(plan)
    overrides = {str(k): v for k, v in (overrides or {}).items() if v in par_ref}
    libelles_comptes = libelles_comptes or {}
    soldes_n1 = soldes_n1 or {}

    lignes_balance = {str(l["compte"]): l for l in (balance_ajustee.get("lignes") or [])}

    # Univers des comptes = balance N ∪ balance N-1. Un compte soldé en N mais
    # mouvementé en N-1 doit rester visible : sa disparition est en soi une
    # information d'audit (cession, apurement, reclassement).
    tous_comptes = sorted(set(lignes_balance) | {str(c) for c in soldes_n1})

    comptes_par_rubrique: dict[str, list[dict]] = {r.ref: [] for r in plan}
    comptes_non_affectes: list[dict] = []

    for compte in tous_comptes:
        ligne = lignes_balance.get(compte) or {}
        brut = round(float(ligne.get("solde_brut") or 0), 2)
        ajust = round(float(ligne.get("ajustement") or 0), 2)
        ajuste = round(float(ligne.get("solde_ajuste") or (brut + ajust)), 2)
        n1_val, n1_src = soldes_n1.get(compte, (0.0, []))
        n1_val = round(float(n1_val or 0), 2)
        variation = round(ajuste - n1_val, 2)

        ref_override = overrides.get(compte)
        rubrique = par_ref[ref_override] if ref_override else rubrique_du_compte(compte, plan)
        if rubrique is None:
            # Compte illisible (ligne de total, en-tête mal ingéré). On le garde
            # à part : l'exclure silencieusement fausserait le bouclage.
            comptes_non_affectes.append({"compte": compte, "solde_ajuste": ajuste,
                                         "motif": "numéro de compte non exploitable"})
            continue

        notable = False
        if seuil_variation and n1_val:
            taux = _pct(variation, n1_val)
            notable = abs(variation) >= float(seuil_variation) and \
                taux is not None and abs(taux) >= TAUX_VARIATION_NOTABLE

        comptes_par_rubrique[rubrique.ref].append({
            "compte": compte,
            "libelle": libelles_comptes.get(compte) or "",
            "solde_brut": brut,
            "ajustement": ajust,
            "solde_ajuste": ajuste,
            "solde_n1": n1_val,
            "variation_abs": variation,
            "variation_pct": _pct(variation, n1_val),
            "variation_notable": notable,
            "absent_n": compte not in lignes_balance,
            "sources": list(ligne.get("sources") or []) + list(n1_src or []),
            "reaffecte": bool(ref_override),
        })

    travaux_par_rubrique = _rattacher_travaux(
        list(plan),
        {ref: [c["compte"] for c in comptes] for ref, comptes in comptes_par_rubrique.items()},
        travaux,
    )

    rubriques_out: list[dict] = []
    for r in sorted(plan, key=lambda x: x.ordre):
        comptes = sorted(comptes_par_rubrique[r.ref], key=lambda c: c["compte"])
        montant_brut = round(sum(c["solde_brut"] for c in comptes), 2)
        montant_ajustements = round(sum(c["ajustement"] for c in comptes), 2)
        montant_ajuste = round(sum(c["solde_ajuste"] for c in comptes), 2)
        montant_n1 = round(sum(c["solde_n1"] for c in comptes), 2)
        variation = round(montant_ajuste - montant_n1, 2)

        # Solde anormal : le sens du solde contredit celui attendu par le plan
        # (un poste clients globalement créditeur, par exemple). Signalé, pas corrigé.
        anormal = False
        if abs(montant_ajuste) > TOLERANCE_BOUCLAGE:
            if r.sens == "debiteur" and montant_ajuste < 0:
                anormal = True
            elif r.sens == "crediteur" and montant_ajuste > 0:
                anormal = True

        t = travaux_par_rubrique.get(r.ref, {})
        rubriques_out.append({
            **rubrique_as_dict(r),
            "comptes": comptes,
            "nb_comptes": len(comptes),
            "montant_brut": montant_brut,
            "montant_ajustements": montant_ajustements,
            "montant_ajuste": montant_ajuste,
            "montant_n1": montant_n1,
            "variation_abs": variation,
            "variation_pct": _pct(variation, montant_n1),
            "montant_presente": round(montant_ajuste * r.signe_presentation, 2),
            "montant_n1_presente": round(montant_n1 * r.signe_presentation, 2),
            "sens_anormal": anormal,
            "vide": not comptes,
            "travaux": t,
            "nb_travaux": sum(len(v) for v in t.values()),
        })

    # ── Sous-totaux par grand poste (les groupes sont contigus par construction) ──
    groupes: list[dict] = []
    for rub in rubriques_out:
        if not groupes or groupes[-1]["libelle"] != rub["groupe"]:
            groupes.append({"libelle": rub["groupe"], "type": rub["type"], "refs": [],
                            "montant_ajuste": 0.0, "montant_n1": 0.0,
                            "montant_presente": 0.0, "montant_n1_presente": 0.0})
        g = groupes[-1]
        g["refs"].append(rub["ref"])
        g["montant_ajuste"] = round(g["montant_ajuste"] + rub["montant_ajuste"], 2)
        g["montant_n1"] = round(g["montant_n1"] + rub["montant_n1"], 2)
        g["montant_presente"] = round(g["montant_presente"] + rub["montant_presente"], 2)
        g["montant_n1_presente"] = round(g["montant_n1_presente"] + rub["montant_n1_presente"], 2)
    for g in groupes:
        g["variation_abs"] = round(g["montant_ajuste"] - g["montant_n1"], 2)
        g["variation_pct"] = _pct(g["variation_abs"], g["montant_n1"])

    # ── Totaux de présentation ───────────────────────────────────────────────
    def _somme(types: tuple[str, ...]) -> float:
        return round(sum(r["montant_presente"] for r in rubriques_out if r["type"] in types), 2)

    # Les comptes à double sens rejoignent l'actif ou le passif selon le signe
    # de leur solde — c'est la règle de présentation, pas un choix arbitraire.
    mixtes = [r for r in rubriques_out if r["type"] == TYPE_BILAN_MIXTE]
    actif_mixte = round(sum(r["montant_ajuste"] for r in mixtes if r["montant_ajuste"] > 0), 2)
    passif_mixte = round(sum(-r["montant_ajuste"] for r in mixtes if r["montant_ajuste"] < 0), 2)

    total_charges = _somme((TYPE_RESULTAT_CHARGES,))
    total_produits = _somme((TYPE_RESULTAT_PRODUITS,))
    totaux = {
        "actif": round(_somme((TYPE_BILAN_ACTIF,)) + actif_mixte, 2),
        "passif": round(_somme((TYPE_BILAN_PASSIF,)) + passif_mixte, 2),
        "actif_hors_mixte": _somme((TYPE_BILAN_ACTIF,)),
        "passif_hors_mixte": _somme((TYPE_BILAN_PASSIF,)),
        "double_sens_actif": actif_mixte,
        "double_sens_passif": passif_mixte,
        "charges": total_charges,
        "produits": total_produits,
        "resultat": round(total_produits - total_charges, 2),
        "non_affecte": _somme((TYPE_NON_AFFECTE,)),
    }

    # ── Contrôle de bouclage : rien n'a été perdu ni compté deux fois ────────
    total_rubriques = round(sum(r["montant_ajuste"] for r in rubriques_out), 2)
    total_hors_plan = round(sum(c["solde_ajuste"] for c in comptes_non_affectes), 2)
    total_balance = round(float(balance_ajustee.get("total_ajuste") or 0), 2)
    ecart = round(total_rubriques + total_hors_plan - total_balance, 2)

    # ── Second contrôle, indépendant : identité actif − passif = résultat ────
    # Le bouclage ci-dessus ne prouve que la cohérence interne de l'affectation
    # (Σ rubriques = Σ balance) ; il tient même si les soldes sont faux. Cette
    # identité, elle, teste la SUBSTANCE des montants : elle a détecté la
    # confusion mouvements/soldes à l'ingestion, que le bouclage laissait passer.
    # Non bloquante : elle dépend des données du client — une balance déjà
    # soldée (résultat viré en compte 12) ou un à-nouveau incomplet la rompt
    # légitimement. On la signale, on ne l'impose pas.
    ecart_bilan = round(totaux["actif"] - totaux["passif"] - totaux["resultat"], 2)
    resultat_deja_comptabilise = any(
        r["ref"] == "PA-RESULTAT" and r["nb_comptes"] and abs(r["montant_ajuste"]) > TOLERANCE_BOUCLAGE
        for r in rubriques_out)

    non_affectes_plan = [r for r in rubriques_out
                         if r["type"] == TYPE_NON_AFFECTE and r["nb_comptes"]]

    return {
        "referentiel_comptable": (referentiel_comptable or "pcgd").lower(),
        "plan_approxime": plan_est_approxime(referentiel_comptable),
        "rubriques": rubriques_out,
        "groupes": groupes,
        "totaux": totaux,
        "bouclage": {
            "total_rubriques": total_rubriques,
            "total_hors_plan": total_hors_plan,
            "total_balance": total_balance,
            "ecart": ecart,
            "boucle": abs(ecart) <= TOLERANCE_BOUCLAGE,
        },
        "equilibre_bilan": {
            "ecart": ecart_bilan,
            "equilibre": abs(ecart_bilan) <= TOLERANCE_BOUCLAGE,
            "resultat_deja_comptabilise": resultat_deja_comptabilise,
        },
        "comptes_non_affectes": comptes_non_affectes,
        "rubriques_non_affectees": [
            {"ref": r["ref"], "libelle": r["libelle"], "nb_comptes": r["nb_comptes"],
             "comptes": [c["compte"] for c in r["comptes"]],
             "montant_ajuste": r["montant_ajuste"]}
            for r in non_affectes_plan
        ],
        "nb_comptes": sum(r["nb_comptes"] for r in rubriques_out) + len(comptes_non_affectes),
        "nb_rubriques_servies": sum(1 for r in rubriques_out if r["nb_comptes"]),
        "avec_comparatif": bool(soldes_n1),
    }


def rubriques_non_vides(matrice: dict) -> list[dict]:
    """Rubriques effectivement servies — celles qui portent au moins un compte."""
    return [r for r in matrice.get("rubriques") or [] if r.get("nb_comptes")]

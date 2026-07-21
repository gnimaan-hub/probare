"""Diligences ISA de périphérie de mission (M3) — NEP/ISA 210, 220, 240, 550, 560, 570, 580, 260/265.

Même patron que le QCI (controls/qci.py) : questionnaire déclaratif en données,
score calculé par le code, synthèse rédigée par l'IA, conclusion signée par
l'auditeur. Les questions sont formulées pour que « oui » soit la réponse
favorable et que chaque « non » identifie un risque (champ risque_si_non).

Convention des références : les définitions sont écrites avec le préfixe
historique « NEP » et re-rendues dans le référentiel actif du cabinet au
chargement, comme dans controls/registry.py.
"""
from __future__ import annotations
from ..normes import reformater_refs


# Calculs déterministes des indicateurs de continuité (ISA 570) — voir plus bas.
def _somme_soldes(rows: list, prefixes: tuple[str, ...], sens: int = 1) -> tuple[float, list[str]]:
    """Somme des soldes nets (débit − crédit) des comptes commençant par `prefixes`.
    sens=-1 pour retourner le solde créditeur en positif (passif, produits)."""
    from .engine import _filter_accounts, _get_amount
    total, sources = 0.0, []
    for row in _filter_accounts(rows, prefixes):
        c = row.get("compte")
        if not c:
            continue
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        total += s * sens
        sources.append(c.id)
    return round(total, 2), sources


DILIGENCES: dict[str, dict] = {
    "acceptation": {
        "code": "acceptation",
        "libelle": "Acceptation et maintien de la mission",
        "nep_ref": "NEP 210 / NEP 220",
        "ordre": 1,
        "phase": "cadrage",
        "description": (
            "Avant d'accepter (ou de poursuivre) la mission, l'auditeur documente son "
            "indépendance, sa compétence et l'intégrité du client. Une conclusion "
            "défavorable non justifiée interdit la poursuite de la mission."
        ),
        "conclusion_requise": False,
        "lettre": None,
        "questions": [
            {"id": "ACC-01",
             "question": "Le cabinet est-il indépendant de l'entité (aucun lien financier, familial ou d'affaires avec la direction ou les actionnaires) ?",
             "risque_si_non": "Indépendance compromise — la mission ne peut être acceptée en l'état"},
            {"id": "ACC-02",
             "question": "Le cabinet dispose-t-il des compétences, du temps et des ressources nécessaires pour réaliser la mission ?",
             "risque_si_non": "Risque de travaux insuffisants ou bâclés (NEP 220)"},
            {"id": "ACC-03",
             "question": "L'intégrité du client et de ses dirigeants a-t-elle été appréciée sans élément défavorable (réputation, litiges, refus de communication) ?",
             "risque_si_non": "Risque d'association à des informations mensongères"},
            {"id": "ACC-04",
             "question": "Les honoraires sont-ils libres de toute dépendance financière excessive envers ce client (poids raisonnable dans le chiffre d'affaires du cabinet) ?",
             "risque_si_non": "Menace d'intérêt personnel sur l'objectivité"},
            {"id": "ACC-05",
             "question": "En cas de succession, le confrère précédent a-t-il été contacté et n'a-t-il signalé aucun motif de refus ?",
             "risque_si_non": "Motifs de non-acceptation potentiellement ignorés"},
            {"id": "ACC-06",
             "question": "Les termes de la mission (objet, périmètre, responsabilités, calendrier) sont-ils formalisés dans une lettre de mission signée ?",
             "risque_si_non": "Absence d'accord formalisé sur les termes de la mission (NEP 210)"},
            {"id": "ACC-07",
             "question": "Le client a-t-il donné accès sans restriction aux informations et personnes nécessaires à l'audit ?",
             "risque_si_non": "Limitation de l'étendue des travaux dès l'acceptation"},
        ],
    },
    "fraude": {
        "code": "fraude",
        "libelle": "Risque de fraude",
        "nep_ref": "NEP 240",
        "ordre": 2,
        "phase": "planification",
        "description": (
            "L'auditeur identifie et évalue le risque d'anomalies significatives "
            "résultant de fraudes (triangle de la fraude : pression, opportunité, "
            "rationalisation), conduit des entretiens tracés et en tire les "
            "conséquences sur les travaux. La synthèse alimente la cartographie des risques."
        ),
        "conclusion_requise": False,
        "lettre": None,
        "questions": [
            {"id": "FRD-01",
             "question": "Des entretiens sur le risque de fraude ont-ils été conduits avec la direction et documentés ?",
             "risque_si_non": "Diligence NEP 240 non réalisée — entretiens obligatoires"},
            {"id": "FRD-02",
             "question": "L'entité est-elle libre de pressions inhabituelles sur les résultats (covenants bancaires, objectifs de primes, attentes d'investisseurs) ?",
             "risque_si_non": "Pression — incitation à la manipulation des résultats"},
            {"id": "FRD-03",
             "question": "Les fonctions incompatibles (autorisation, enregistrement, détention des actifs) sont-elles séparées ?",
             "risque_si_non": "Opportunité — détournement possible sans détection"},
            {"id": "FRD-04",
             "question": "La direction manifeste-t-elle un engagement clair envers l'éthique et le contrôle interne (ton au sommet) ?",
             "risque_si_non": "Rationalisation — climat propice à la justification des fraudes"},
            {"id": "FRD-05",
             "question": "Les écritures de journal manuelles et de fin de période sont-elles soumises à autorisation et revue ?",
             "risque_si_non": "Risque de contournement des contrôles par la direction (top-side entries)"},
            {"id": "FRD-06",
             "question": "Les estimations comptables significatives (provisions, dépréciations) reposent-elles sur des hypothèses documentées et cohérentes d'un exercice à l'autre ?",
             "risque_si_non": "Biais de la direction dans les estimations — lissage de résultat"},
            {"id": "FRD-07",
             "question": "L'exercice est-il exempt de transactions significatives inhabituelles ou sans logique économique apparente ?",
             "risque_si_non": "Transactions atypiques potentiellement destinées à masquer une fraude"},
            {"id": "FRD-08",
             "question": "Le personnel comptable est-il stable (pas de rotation anormale ni de départs conflictuels récents) ?",
             "risque_si_non": "Rotation anormale — signal d'alerte sur le climat de contrôle"},
        ],
    },
    "parties_liees": {
        "code": "parties_liees",
        "libelle": "Parties liées",
        "nep_ref": "NEP 550",
        "ordre": 3,
        "phase": "travaux",
        "description": (
            "L'auditeur identifie les parties liées (dirigeants, actionnaires, entités "
            "sous contrôle commun), recense les transactions conclues avec elles et "
            "vérifie leur autorisation, leur substance et leur correcte présentation."
        ),
        "conclusion_requise": False,
        "lettre": None,
        "questions": [
            {"id": "PLI-01",
             "question": "La liste des parties liées (dirigeants, actionnaires, entités apparentées) a-t-elle été obtenue de la direction et recoupée avec le dossier permanent ?",
             "risque_si_non": "Parties liées non identifiées — transactions dissimulées possibles"},
            {"id": "PLI-02",
             "question": "Les transactions avec les parties liées de l'exercice ont-elles été recensées (comptes courants, ventes, achats, prêts, garanties) ?",
             "risque_si_non": "Transactions avec parties liées non détectées"},
            {"id": "PLI-03",
             "question": "Ces transactions ont-elles été conclues à des conditions normales de marché (ou l'écart est-il documenté et justifié) ?",
             "risque_si_non": "Transferts de valeur déguisés au détriment de l'entité"},
            {"id": "PLI-04",
             "question": "Les conventions réglementées ont-elles été autorisées par l'organe compétent et correctement présentées ?",
             "risque_si_non": "Conventions non autorisées — irrégularité juridique"},
            {"id": "PLI-05",
             "question": "Les soldes avec les parties liées (comptes courants d'associés notamment) sont-ils confirmés ou justifiés ?",
             "risque_si_non": "Soldes avec parties liées non validés"},
            {"id": "PLI-06",
             "question": "L'information sur les parties liées donnée en annexe est-elle complète et conforme au référentiel comptable ?",
             "risque_si_non": "Information incomplète dans les états financiers"},
        ],
    },
    "evenements_posterieurs": {
        "code": "evenements_posterieurs",
        "libelle": "Événements postérieurs à la clôture",
        "nep_ref": "NEP 560",
        "ordre": 4,
        "phase": "revue",
        "description": (
            "Entre la date de clôture et la date du rapport, l'auditeur recherche les "
            "événements qui exigent un ajustement des comptes ou une information en "
            "annexe (litiges, défaillances de clients, sinistres, décisions majeures)."
        ),
        "conclusion_requise": False,
        "lettre": None,
        "questions": [
            {"id": "EVP-01",
             "question": "Les procès-verbaux des organes de direction postérieurs à la clôture ont-ils été lus sans révéler d'événement significatif non traité ?",
             "risque_si_non": "Décisions post-clôture significatives non reflétées"},
            {"id": "EVP-02",
             "question": "La direction a-t-elle été interrogée sur les événements postérieurs (litiges nouveaux, engagements, sinistres, restructurations) ?",
             "risque_si_non": "Diligence NEP 560 non réalisée"},
            {"id": "EVP-03",
             "question": "Les encaissements post-clôture confirment-ils la recouvrabilité des créances importantes à la clôture ?",
             "risque_si_non": "Créances douteuses à la clôture non provisionnées"},
            {"id": "EVP-04",
             "question": "Les situations comptables ou relevés bancaires postérieurs à la clôture ont-ils été examinés sans anomalie de rattachement ?",
             "risque_si_non": "Écritures post-clôture rattachables à l'exercice audité"},
            {"id": "EVP-05",
             "question": "L'exercice suivant est-il exempt, à la date des travaux, d'événement compromettant la valeur d'actifs au bilan (défaillance client majeure, sinistre non assuré) ?",
             "risque_si_non": "Ajustement ou information en annexe requis"},
        ],
    },
    "continuite": {
        "code": "continuite",
        "libelle": "Continuité d'exploitation",
        "nep_ref": "NEP 570",
        "ordre": 5,
        "phase": "revue",
        "description": (
            "L'auditeur apprécie si l'entité peut poursuivre son exploitation sur les "
            "douze mois à venir. Les indicateurs financiers sont calculés par le moteur "
            "depuis la balance ; la conclusion documentée et signée est OBLIGATOIRE "
            "avant la génération du dossier."
        ),
        "conclusion_requise": True,
        "lettre": None,
        "questions": [
            {"id": "CNT-01",
             "question": "Les capitaux propres sont-ils positifs et supérieurs à la moitié du capital social ?",
             "risque_si_non": "Capitaux propres dégradés — procédure d'alerte potentielle"},
            {"id": "CNT-02",
             "question": "L'entité dégage-t-elle un résultat et une capacité d'autofinancement positifs (ou une trajectoire de retour à l'équilibre crédible) ?",
             "risque_si_non": "Pertes récurrentes — viabilité du modèle en question"},
            {"id": "CNT-03",
             "question": "La trésorerie et les financements disponibles couvrent-ils les échéances des douze prochains mois ?",
             "risque_si_non": "Risque de cessation de paiements"},
            {"id": "CNT-04",
             "question": "L'entité est-elle à jour de ses dettes fiscales et sociales (aucun moratoire ni retard significatif) ?",
             "risque_si_non": "Arriérés fiscaux/sociaux — signal de tension de trésorerie"},
            {"id": "CNT-05",
             "question": "L'entité est-elle libre de dépendance critique (client, fournisseur, financement ou dirigeant unique) menaçant l'exploitation ?",
             "risque_si_non": "Défaillance d'un tiers clé = arrêt d'activité"},
            {"id": "CNT-06",
             "question": "La direction a-t-elle formalisé une appréciation de la continuité d'exploitation sur au moins douze mois ?",
             "risque_si_non": "Appréciation de la direction absente (exigence NEP 570)"},
            {"id": "CNT-07",
             "question": "L'exercice et la période postérieure sont-ils exempts d'événements défavorables majeurs (perte de marché, litige menaçant, retrait d'agrément) ?",
             "risque_si_non": "Événements compromettant la poursuite d'activité"},
        ],
    },
    "declarations_ecrites": {
        "code": "declarations_ecrites",
        "libelle": "Déclarations écrites de la direction",
        "nep_ref": "NEP 580",
        "ordre": 6,
        "phase": "generation",
        "description": (
            "Avant la signature du rapport, l'auditeur obtient de la direction une "
            "lettre d'affirmation. L'IA rédige un projet de lettre à partir du contenu "
            "réel du dossier (exceptions tranchées, anomalies non corrigées) — "
            "l'auditeur la vérifie avant envoi au client pour signature."
        ),
        "conclusion_requise": False,
        "lettre": "affirmation",
        "questions": [
            {"id": "DEC-01",
             "question": "La direction a-t-elle confirmé sa responsabilité sur l'établissement des comptes et le contrôle interne ?",
             "risque_si_non": "Responsabilités non reconnues — fondement du rapport fragilisé"},
            {"id": "DEC-02",
             "question": "La direction a-t-elle confirmé avoir communiqué toutes les informations pertinentes et l'accès à tous les documents ?",
             "risque_si_non": "Exhaustivité des informations non affirmée"},
            {"id": "DEC-03",
             "question": "La direction a-t-elle pris position par écrit sur les anomalies non corrigées (accord ou justification du refus de correction) ?",
             "risque_si_non": "Anomalies non corrigées sans position formelle de la direction"},
            {"id": "DEC-04",
             "question": "Les déclarations couvrent-elles les points sensibles du dossier (fraude, parties liées, événements postérieurs, continuité) ?",
             "risque_si_non": "Déclarations incomplètes sur les zones à risque"},
            {"id": "DEC-05",
             "question": "La lettre d'affirmation est-elle datée du jour du rapport (ou de la date la plus rapprochée possible) et signée par les personnes compétentes ?",
             "risque_si_non": "Déclarations obsolètes ou non engageantes"},
        ],
    },
    "gouvernance": {
        "code": "gouvernance",
        "libelle": "Communication avec la gouvernance",
        "nep_ref": "NEP 260 / NEP 265",
        "ordre": 7,
        "phase": "generation",
        "description": (
            "L'auditeur communique aux organes de gouvernance l'étendue de ses travaux, "
            "les difficultés rencontrées, les anomalies relevées et les faiblesses "
            "significatives du contrôle interne. L'IA rédige un projet de lettre à "
            "partir du QCI et des exceptions du dossier."
        ),
        "conclusion_requise": False,
        "lettre": "gouvernance",
        "questions": [
            {"id": "GOU-01",
             "question": "L'étendue et le calendrier des travaux d'audit ont-ils été communiqués à la gouvernance en début de mission ?",
             "risque_si_non": "Communication initiale NEP 260 non réalisée"},
            {"id": "GOU-02",
             "question": "Les anomalies significatives relevées (corrigées et non corrigées) ont-elles été communiquées à la gouvernance ?",
             "risque_si_non": "Gouvernance non informée des anomalies (NEP 260)"},
            {"id": "GOU-03",
             "question": "Les faiblesses significatives du contrôle interne ont-elles été communiquées par écrit (NEP 265) ?",
             "risque_si_non": "Faiblesses du CI non signalées par écrit"},
            {"id": "GOU-04",
             "question": "Les difficultés importantes rencontrées pendant l'audit (accès, délais, désaccords) ont-elles été portées à la connaissance de la gouvernance ?",
             "risque_si_non": "Difficultés d'audit non communiquées"},
            {"id": "GOU-05",
             "question": "La trace écrite de ces communications (courriers, comptes rendus) est-elle conservée au dossier ?",
             "risque_si_non": "Communications non documentées (NEP 230)"},
        ],
    },
}

# Reformatage des références dans le référentiel actif du cabinet (comme registry.py).
for _d in DILIGENCES.values():
    _d["nep_ref"] = reformater_refs(_d["nep_ref"])
    _d["description"] = reformater_refs(_d["description"])
    for _q in _d["questions"]:
        _q["risque_si_non"] = reformater_refs(_q["risque_si_non"])


NIVEAUX_DILIGENCE = {
    # Barème prudent, aligné sur le QCI : « favorable » exige un score élevé
    # ET zéro réponse « non » (questionnaire déclaratif).
    "favorable":   {"seuil_min": 0.85, "label": "Favorable", "couleur": "emerald"},
    "attention":   {"seuil_min": 0.50, "label": "Point d'attention", "couleur": "amber"},
    "defavorable": {"seuil_min": 0.00, "label": "Défavorable", "couleur": "red"},
}


def calculer_niveau_diligence(reponses: list[dict]) -> dict:
    """Score déterministe d'une diligence à partir des réponses oui/non/na."""
    total = len([r for r in reponses if r.get("reponse") in ("oui", "non")])
    if total == 0:
        return {"score": 0.0, "niveau": "defavorable", "nb_oui": 0, "nb_non": 0, "nb_na": 0,
                **NIVEAUX_DILIGENCE["defavorable"]}

    nb_oui = sum(1 for r in reponses if r.get("reponse") == "oui")
    nb_non = sum(1 for r in reponses if r.get("reponse") == "non")
    nb_na = sum(1 for r in reponses if r.get("reponse") == "na")
    score = nb_oui / total

    niveau = "defavorable"
    for key, cfg in NIVEAUX_DILIGENCE.items():
        if score >= cfg["seuil_min"]:
            niveau = key
            break
    if niveau == "favorable" and nb_non > 0:
        niveau = "attention"

    return {"score": round(score, 2), "niveau": niveau,
            "nb_oui": nb_oui, "nb_non": nb_non, "nb_na": nb_na,
            **NIVEAUX_DILIGENCE[niveau]}


def indicateurs_continuite(rows_balance: list, seuil: float | None = None) -> dict:
    """Indicateurs financiers déterministes pour l'appréciation ISA 570.

    Tout est calculé depuis la balance importée (aucun chiffre LLM) :
    - capitaux propres nets (classes 10x-13x, créditeur positif) ;
    - capital social (101x) et test « CP < 1/2 capital » ;
    - résultat de l'exercice (120 créditeur − 129 débiteur, ou produits − charges) ;
    - fonds de roulement = ressources stables (1xx créditeur) − actif immobilisé (2xx) ;
    - trésorerie nette (5xx).
    Retourne aussi la liste des ids de DonneeSourcee utilisés (provenance).
    """
    sources: list[str] = []

    cp, s = _somme_soldes(rows_balance, ("10", "11", "12", "13"), sens=-1)
    sources += s
    capital, s = _somme_soldes(rows_balance, ("101",), sens=-1)
    sources += s
    resultat, s = _somme_soldes(rows_balance, ("12",), sens=-1)
    sources += s
    if resultat == 0:
        produits, s1 = _somme_soldes(rows_balance, ("7",), sens=-1)
        charges, s2 = _somme_soldes(rows_balance, ("6",), sens=1)
        if produits or charges:
            resultat = round(produits - charges, 2)
            sources += s1 + s2
    ressources_stables, s = _somme_soldes(rows_balance, ("1",), sens=-1)
    sources += s
    actif_immobilise, s = _somme_soldes(rows_balance, ("2",), sens=1)
    sources += s
    tresorerie, s = _somme_soldes(rows_balance, ("5",), sens=1)
    sources += s

    fonds_roulement = round(ressources_stables - actif_immobilise, 2)

    alertes = []
    if cp < 0:
        alertes.append("Capitaux propres négatifs.")
    elif capital > 0 and cp < capital / 2:
        alertes.append("Capitaux propres inférieurs à la moitié du capital social.")
    if resultat < 0:
        alertes.append("Résultat de l'exercice déficitaire.")
    if fonds_roulement < 0:
        alertes.append("Fonds de roulement négatif (actif immobilisé non couvert par les ressources stables).")
    if tresorerie < 0:
        alertes.append("Trésorerie nette négative.")

    return {
        "capitaux_propres": cp,
        "capital_social": capital,
        "resultat_exercice": resultat,
        "fonds_roulement": fonds_roulement,
        "tresorerie_nette": tresorerie,
        "seuil_signification": seuil,
        "alertes": alertes,
        "nb_alertes": len(alertes),
        "sources": list(dict.fromkeys(sources)),
    }


def get_diligence(code: str) -> dict | None:
    return DILIGENCES.get(code)


def liste_diligences() -> list[dict]:
    return sorted(DILIGENCES.values(), key=lambda d: d["ordre"])

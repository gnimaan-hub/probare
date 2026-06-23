"""Questionnaire de Contrôle Interne (QCI) par cycle — NEP 315."""
from __future__ import annotations

QCI_PAR_CYCLE: dict[str, list[dict]] = {
    "tresorerie": [
        {
            "id": "TR-CI-01",
            "question": "Les accès aux comptes bancaires et aux signatures sont-ils strictement limités aux personnes autorisées ?",
            "assertion": "Existence / Séparation des tâches",
            "risque_si_non": "Risque de détournement de fonds non détecté",
        },
        {
            "id": "TR-CI-02",
            "question": "Les chèques et virements au-delà d'un seuil font-ils l'objet d'une double signature ou autorisation ?",
            "assertion": "Autorisation",
            "risque_si_non": "Paiements non autorisés possibles",
        },
        {
            "id": "TR-CI-03",
            "question": "Des rapprochements bancaires sont-ils effectués mensuellement par une personne indépendante des encaissements/décaissements ?",
            "assertion": "Exactitude / Séparation des tâches",
            "risque_si_non": "Anomalies en trésorerie non détectées",
        },
        {
            "id": "TR-CI-04",
            "question": "Les rapprochements bancaires sont-ils revus et approuvés par un responsable hiérarchique ?",
            "assertion": "Surveillance",
            "risque_si_non": "Rapprochements de complaisance non repérés",
        },
        {
            "id": "TR-CI-05",
            "question": "Les encaissements en espèces sont-ils versés intégralement et rapidement en banque (J+1 maximum) ?",
            "assertion": "Exhaustivité / Coupure",
            "risque_si_non": "Détournements d'encaissements possibles",
        },
        {
            "id": "TR-CI-06",
            "question": "La caisse fait-elle l'objet d'un inventaire physique surprise et inopinée à intervalles réguliers ?",
            "assertion": "Existence",
            "risque_si_non": "Solde de caisse non justifié",
        },
        {
            "id": "TR-CI-07",
            "question": "Les chèques annulés sont-ils conservés, mutilés et rendus inutilisables ?",
            "assertion": "Autorisation / Exhaustivité",
            "risque_si_non": "Réutilisation frauduleuse possible",
        },
        {
            "id": "TR-CI-08",
            "question": "Existe-t-il une procédure formalisée pour le traitement des rejets de paiement et des litiges bancaires ?",
            "assertion": "Exactitude",
            "risque_si_non": "Transactions non résolues omises",
        },
        {
            "id": "TR-CI-09",
            "question": "Les justificatifs de dépenses en espèces (petite caisse) sont-ils exigés systématiquement et archivés ?",
            "assertion": "Réalité / Autorisation",
            "risque_si_non": "Dépenses fictives ou non autorisées",
        },
        {
            "id": "TR-CI-10",
            "question": "Les coordonnées bancaires des bénéficiaires de virement sont-elles vérifiées avant tout premier paiement ?",
            "assertion": "Exactitude / Autorisation",
            "risque_si_non": "Fraude au virement (changement de RIB)",
        },
    ],
    "achats": [
        {
            "id": "AC-CI-01",
            "question": "Les commandes d'achat sont-elles formalisées, numérotées et approuvées par un responsable habilité ?",
            "assertion": "Autorisation",
            "risque_si_non": "Achats non autorisés ou fictifs",
        },
        {
            "id": "AC-CI-02",
            "question": "La réception des biens/services est-elle systématiquement validée par un bon de réception signé ?",
            "assertion": "Existence / Réalité",
            "risque_si_non": "Factures payées sans livraison effective",
        },
        {
            "id": "AC-CI-03",
            "question": "La saisie comptable des factures est-elle effectuée par une personne distincte de celle qui les reçoit et les approuve ?",
            "assertion": "Séparation des tâches",
            "risque_si_non": "Fraudes internes non détectées",
        },
        {
            "id": "AC-CI-04",
            "question": "Un rapprochement à 3 voies est-il effectué entre commande, bon de réception et facture avant paiement ?",
            "assertion": "Exactitude / Réalité",
            "risque_si_non": "Surpaiements ou paiements de factures non conformes",
        },
        {
            "id": "AC-CI-05",
            "question": "Les fournisseurs sont-ils référencés dans un fichier maître contrôlé et les modifications soumises à autorisation ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Fournisseurs fictifs ou coordonnées bancaires falsifiées",
        },
        {
            "id": "AC-CI-06",
            "question": "Les avoirs fournisseurs sont-ils suivis systématiquement et imputés sur les prochains paiements ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Avoirs non comptabilisés, surcharge de charges",
        },
        {
            "id": "AC-CI-07",
            "question": "Les soldes fournisseurs débiteurs font-ils l'objet d'une analyse régulière et de relances ?",
            "assertion": "Exhaustivité",
            "risque_si_non": "Avoirs ou paiements en double non réclamés",
        },
        {
            "id": "AC-CI-08",
            "question": "Les engagements hors bilan (contrats pluriannuels, locations) sont-ils recensés et approuvés par la direction ?",
            "assertion": "Présentation / Information à fournir",
            "risque_si_non": "Engagements non divulgués dans les états financiers",
        },
        {
            "id": "AC-CI-09",
            "question": "Une procédure de coupure des achats (cut-off) est-elle appliquée formellement en fin d'exercice ?",
            "assertion": "Coupure",
            "risque_si_non": "Charges comptabilisées dans le mauvais exercice",
        },
        {
            "id": "AC-CI-10",
            "question": "Les charges sont-elles soumises à budget et les dépassements font-ils l'objet d'une autorisation expresse ?",
            "assertion": "Autorisation / Surveillance",
            "risque_si_non": "Dépassements budgétaires non maîtrisés",
        },
    ],
    "ventes": [
        {
            "id": "VE-CI-01",
            "question": "Les conditions de vente (prix, remises, délais de paiement) sont-elles formalisées et les exceptions autorisées par un responsable ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Ventes à prix non conformes ou remises excessives",
        },
        {
            "id": "VE-CI-02",
            "question": "Les factures de vente sont-elles numérotées séquentiellement et toute rupture de séquence est-elle justifiée ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Ventes non facturées ou dissimulées",
        },
        {
            "id": "VE-CI-03",
            "question": "La solvabilité des clients est-elle évaluée avant accord de crédit et les limites de crédit respectées ?",
            "assertion": "Réalité / Évaluation",
            "risque_si_non": "Créances irrécouvrables non provisionnées",
        },
        {
            "id": "VE-CI-04",
            "question": "Un état de l'antériorité des créances est-il produit mensuellement et analysé par la direction ?",
            "assertion": "Évaluation / Surveillance",
            "risque_si_non": "Créances douteuses non identifiées et non provisionnées",
        },
        {
            "id": "VE-CI-05",
            "question": "Les provisions pour créances douteuses sont-elles constituées selon une méthode documentée et appliquée de manière cohérente ?",
            "assertion": "Évaluation",
            "risque_si_non": "Provisions insuffisantes ou incohérentes d'un exercice à l'autre",
        },
        {
            "id": "VE-CI-06",
            "question": "Les avoirs accordés aux clients sont-ils soumis à autorisation formelle d'un responsable distinct du commercial ?",
            "assertion": "Autorisation / Séparation des tâches",
            "risque_si_non": "Avoirs fictifs pour dissimuler des fraudes commerciales",
        },
        {
            "id": "VE-CI-07",
            "question": "Les encaissements clients sont-ils rapprochés avec les ventes facturées au moins mensuellement ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Encaissements détournés ou non comptabilisés",
        },
        {
            "id": "VE-CI-08",
            "question": "Une procédure de relance clients est-elle formalisée et appliquée dès le premier jour de retard ?",
            "assertion": "Évaluation / Surveillance",
            "risque_si_non": "Dégradation non maîtrisée du portefeuille clients",
        },
        {
            "id": "VE-CI-09",
            "question": "La coupure des ventes (cut-off) est-elle contrôlée formellement en fin d'exercice ?",
            "assertion": "Coupure",
            "risque_si_non": "Produits comptabilisés dans le mauvais exercice",
        },
        {
            "id": "VE-CI-10",
            "question": "Un rapprochement est-il effectué entre les quantités livrées (bons de livraison) et les quantités facturées ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Livraisons non facturées ou facturations sans livraison",
        },
    ],
}

NIVEAUX_RISQUE_CI = {
    "faible":  {"seuil_min": 0.70, "label": "Faible", "couleur": "emerald",
                "implication": "Vous pouvez vous appuyer sur le contrôle interne et réduire l'étendue des tests substantifs."},
    "moyen":   {"seuil_min": 0.40, "label": "Moyen", "couleur": "amber",
                "implication": "Appui partiel possible. Renforcez les tests analytiques sur les zones de faiblesse identifiées."},
    "eleve":   {"seuil_min": 0.00, "label": "Élevé", "couleur": "red",
                "implication": "Pas d'appui sur le contrôle interne. Étendez significativement les travaux substantifs."},
}


def calculer_niveau_risque(reponses: list[dict]) -> dict:
    """
    Calcule le niveau de risque CI à partir des réponses.
    reponses : [{question_id, reponse: 'oui'|'non'|'na', commentaire}]
    """
    total = len([r for r in reponses if r.get("reponse") in ("oui", "non")])
    if total == 0:
        return {"score": 0.0, "niveau": "eleve", "nb_oui": 0, "nb_non": 0, "nb_na": 0}

    nb_oui = sum(1 for r in reponses if r.get("reponse") == "oui")
    nb_non = sum(1 for r in reponses if r.get("reponse") == "non")
    nb_na  = sum(1 for r in reponses if r.get("reponse") == "na")
    score = nb_oui / total if total > 0 else 0.0

    niveau = "eleve"
    for key, cfg in NIVEAUX_RISQUE_CI.items():
        if score >= cfg["seuil_min"]:
            niveau = key
            break

    return {
        "score": round(score, 2),
        "niveau": niveau,
        "nb_oui": nb_oui,
        "nb_non": nb_non,
        "nb_na": nb_na,
        **NIVEAUX_RISQUE_CI[niveau],
    }

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
    "immobilisations": [
        {
            "id": "IM-CI-01",
            "question": "Un tableau des immobilisations (TVA) est-il tenu à jour et rapproché avec la comptabilité au moins une fois par an ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Immobilisations non comptabilisées ou sorties non enregistrées",
        },
        {
            "id": "IM-CI-02",
            "question": "Tout investissement excédant un seuil défini fait-il l'objet d'une approbation préalable par la direction ou un comité d'investissement ?",
            "assertion": "Autorisation",
            "risque_si_non": "Acquisitions non autorisées ou fictives",
        },
        {
            "id": "IM-CI-03",
            "question": "Les plans d'amortissement sont-ils établis conformément à la politique comptable et aux durées de vie économiques réelles ?",
            "assertion": "Évaluation",
            "risque_si_non": "Dotations inexactes, valeur nette comptable erronée",
        },
        {
            "id": "IM-CI-04",
            "question": "Les sorties d'immobilisations (cessions, mises au rebut) sont-elles systématiquement autorisées, documentées et comptabilisées ?",
            "assertion": "Exhaustivité / Autorisation",
            "risque_si_non": "Actifs sortis sans enregistrement comptable, gains/pertes omis",
        },
        {
            "id": "IM-CI-05",
            "question": "Un inventaire physique des immobilisations est-il réalisé au moins tous les trois ans et les écarts sont-ils comptabilisés ?",
            "assertion": "Existence",
            "risque_si_non": "Immobilisations fictives ou disparues non détectées",
        },
        {
            "id": "IM-CI-06",
            "question": "Les dépenses d'entretien et réparations sont-elles distinguées des dépenses d'investissement selon des critères documentés ?",
            "assertion": "Exactitude / Évaluation",
            "risque_si_non": "Charges passées en investissement ou investissements en charges",
        },
        {
            "id": "IM-CI-07",
            "question": "Les dotations aux amortissements sont-elles calculées par un système informatisé ou vérifiées par une personne indépendante ?",
            "assertion": "Exactitude / Surveillance",
            "risque_si_non": "Erreurs de calcul systématiques non détectées",
        },
        {
            "id": "IM-CI-08",
            "question": "Une procédure de coupure des acquisitions et mises en service est-elle appliquée formellement en fin d'exercice ?",
            "assertion": "Coupure",
            "risque_si_non": "Immobilisations ou amortissements comptabilisés dans le mauvais exercice",
        },
        {
            "id": "IM-CI-09",
            "question": "Les immobilisations appartenant à des tiers (contrats de location, biens mis à disposition) sont-elles identifiées et exclues du bilan ?",
            "assertion": "Droits et obligations",
            "risque_si_non": "Actifs hors bilan inclus par erreur",
        },
        {
            "id": "IM-CI-10",
            "question": "Les contrats d'assurance des immobilisations sont-ils revus annuellement pour s'assurer qu'ils reflètent la valeur de remplacement des biens ?",
            "assertion": "Évaluation",
            "risque_si_non": "Sous-assurance et risque de perte non compensée",
        },
    ],
    "stocks": [
        {
            "id": "ST-CI-01",
            "question": "Un inventaire physique exhaustif est-il réalisé au moins une fois par an et rapproché avec les enregistrements comptables ?",
            "assertion": "Existence",
            "risque_si_non": "Stocks fictifs ou disparitions non détectées",
        },
        {
            "id": "ST-CI-02",
            "question": "Les écarts d'inventaire sont-ils analysés, justifiés et approuvés par un responsable avant comptabilisation ?",
            "assertion": "Exactitude / Autorisation",
            "risque_si_non": "Ajustements de complaisance non contrôlés",
        },
        {
            "id": "ST-CI-03",
            "question": "La méthode de valorisation des stocks (FIFO, CMUP, etc.) est-elle documentée, appliquée de manière cohérente et approuvée par la direction ?",
            "assertion": "Évaluation",
            "risque_si_non": "Valorisation incohérente d'un exercice à l'autre",
        },
        {
            "id": "ST-CI-04",
            "question": "Les stocks obsolètes, à rotation lente ou endommagés font-ils l'objet d'une revue régulière et de dépréciations documentées ?",
            "assertion": "Évaluation",
            "risque_si_non": "Stocks surévalués, provisions insuffisantes",
        },
        {
            "id": "ST-CI-05",
            "question": "Les entrées et sorties de stocks sont-elles contrôlées par des documents formels (bons d'entrée, bons de sortie) avec autorisation ?",
            "assertion": "Exhaustivité / Autorisation",
            "risque_si_non": "Mouvements non enregistrés ou non autorisés",
        },
        {
            "id": "ST-CI-06",
            "question": "La coupure des mouvements de stocks est-elle contrôlée en fin d'exercice pour rattacher chaque mouvement au bon exercice ?",
            "assertion": "Coupure",
            "risque_si_non": "Stocks ou charges comptabilisés dans le mauvais exercice",
        },
        {
            "id": "ST-CI-07",
            "question": "Les stocks appartenant à des tiers (consignation, dépôt) sont-ils physiquement séparés et exclus de la valorisation du bilan ?",
            "assertion": "Droits et obligations",
            "risque_si_non": "Stocks de tiers inclus dans le bilan par erreur",
        },
        {
            "id": "ST-CI-08",
            "question": "L'accès aux zones de stockage est-il restreint aux personnes autorisées et contrôlé par un système formalisé ?",
            "assertion": "Existence / Séparation des tâches",
            "risque_si_non": "Vols ou manipulations physiques non détectés",
        },
        {
            "id": "ST-CI-09",
            "question": "Les stocks en transit ou chez des tiers font-ils l'objet d'un suivi documenté et d'une confirmation périodique ?",
            "assertion": "Exhaustivité",
            "risque_si_non": "Stocks hors site omis dans l'inventaire",
        },
        {
            "id": "ST-CI-10",
            "question": "Le coût de revient des stocks est-il suivi pour détecter les articles valorisés au-dessus de leur valeur nette de réalisation ?",
            "assertion": "Évaluation",
            "risque_si_non": "Stocks surévalués non dépréciés",
        },
    ],
    "paie": [
        {
            "id": "PA-CI-01",
            "question": "Le fichier du personnel est-il tenu à jour et les entrées/sorties de salariés formellement autorisées par les RH et la direction ?",
            "assertion": "Existence / Autorisation",
            "risque_si_non": "Salariés fantômes ou départs non enregistrés",
        },
        {
            "id": "PA-CI-02",
            "question": "La paie est-elle établie par une personne distincte de celle qui autorise les embauches et les modifications de salaires ?",
            "assertion": "Séparation des tâches",
            "risque_si_non": "Fraudes à la paie non détectées",
        },
        {
            "id": "PA-CI-03",
            "question": "Les bulletins de paie sont-ils revus et approuvés par un responsable avant tout virement de salaires ?",
            "assertion": "Surveillance / Autorisation",
            "risque_si_non": "Paiements non autorisés ou erronés",
        },
        {
            "id": "PA-CI-04",
            "question": "Les heures supplémentaires, primes et avantages en nature sont-ils approuvés formellement avant d'être intégrés dans la paie ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Éléments variables non justifiés, charges gonflées",
        },
        {
            "id": "PA-CI-05",
            "question": "Les déclarations sociales (CNSS, organismes sociaux) sont-elles réconciliées avec la comptabilité et déposées dans les délais légaux ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Pénalités pour retard, charges sociales sous-déclarées",
        },
        {
            "id": "PA-CI-06",
            "question": "Des contrôles sont-ils effectués pour détecter les salariés fictifs (vérification des RIB, des numéros de sécurité sociale) ?",
            "assertion": "Existence",
            "risque_si_non": "Détournements via des salariés fantômes",
        },
        {
            "id": "PA-CI-07",
            "question": "Les modifications du fichier du personnel (salaires, coordonnées bancaires) sont-elles soumises à autorisation hiérarchique et traçables informatiquement ?",
            "assertion": "Autorisation",
            "risque_si_non": "Modifications frauduleuses de salaires ou de RIB",
        },
        {
            "id": "PA-CI-08",
            "question": "Un rapprochement est-il effectué entre la masse salariale comptabilisée et les déclarations sociales au moins trimestriellement ?",
            "assertion": "Exactitude / Exhaustivité",
            "risque_si_non": "Écarts entre paie et déclarations non détectés",
        },
        {
            "id": "PA-CI-09",
            "question": "Les soldes de tout compte et indemnités de départ sont-ils calculés, vérifiés et approuvés par la direction avant paiement ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Indemnités sur- ou sous-évaluées, litiges prud'homaux",
        },
        {
            "id": "PA-CI-10",
            "question": "Les accès au logiciel de paie sont-ils strictement limités et les modifications de paramètres (taux, barèmes) soumises à autorisation ?",
            "assertion": "Séparation des tâches / Autorisation",
            "risque_si_non": "Manipulations des paramètres de calcul de la paie",
        },
    ],
    "impots": [
        {
            "id": "TX-CI-01",
            "question": "Les déclarations fiscales (TVA, IS, IRPP, etc.) sont-elles établies par une personne compétente, revues et déposées dans les délais légaux ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Pénalités pour retard, redressements fiscaux",
        },
        {
            "id": "TX-CI-02",
            "question": "Un calendrier fiscal est-il tenu à jour avec toutes les échéances et une personne désignée en est-elle responsable ?",
            "assertion": "Surveillance",
            "risque_si_non": "Obligations fiscales oubliées, pénalités",
        },
        {
            "id": "TX-CI-03",
            "question": "Les crédits de TVA sont-ils analysés régulièrement et les demandes de remboursement engagées dans les délais réglementaires ?",
            "assertion": "Évaluation / Surveillance",
            "risque_si_non": "Crédits de TVA non récupérés, trésorerie obérée",
        },
        {
            "id": "TX-CI-04",
            "question": "Les changements de réglementation fiscale font-ils l'objet d'une veille formalisée et leur impact sur la comptabilité est-il analysé ?",
            "assertion": "Exactitude",
            "risque_si_non": "Application de règles fiscales obsolètes, risque de redressement",
        },
        {
            "id": "TX-CI-05",
            "question": "Les charges fiscales comptabilisées sont-elles réconciliées avec les déclarations fiscales au moins annuellement ?",
            "assertion": "Exactitude",
            "risque_si_non": "Écarts non détectés entre comptabilité et déclarations",
        },
        {
            "id": "TX-CI-06",
            "question": "Les litiges fiscaux en cours sont-ils documentés et les risques provisionnés selon une évaluation prudente et revue par un juriste ou un expert ?",
            "assertion": "Évaluation / Présentation",
            "risque_si_non": "Passifs éventuels non provisionnés, sous-évaluation du risque",
        },
        {
            "id": "TX-CI-07",
            "question": "La TVA déductible est-elle vérifiée facture par facture pour s'assurer de l'éligibilité à la déduction (nature, activité taxable) ?",
            "assertion": "Exactitude / Exhaustivité",
            "risque_si_non": "TVA déduite à tort, risque de redressement",
        },
        {
            "id": "TX-CI-08",
            "question": "Les taxes locales et parafiscales (taxe foncière, taxe professionnelle, etc.) sont-elles inventoriées et comptabilisées exhaustivement ?",
            "assertion": "Exhaustivité",
            "risque_si_non": "Charges fiscales omises, passifs non comptabilisés",
        },
        {
            "id": "TX-CI-09",
            "question": "Une procédure de cut-off fiscal est-elle appliquée pour rattacher les charges fiscales au bon exercice ?",
            "assertion": "Coupure",
            "risque_si_non": "Charges fiscales imputées dans le mauvais exercice",
        },
        {
            "id": "TX-CI-10",
            "question": "Les acomptes d'impôt sur les bénéfices sont-ils calculés selon les règles en vigueur et payés avant les échéances légales ?",
            "assertion": "Exactitude / Surveillance",
            "risque_si_non": "Intérêts de retard, majoration des acomptes",
        },
    ],
    "capitaux_propres": [
        {
            "id": "CP-CI-01",
            "question": "Toute modification du capital social (augmentation, réduction) est-elle appuyée par des décisions d'assemblée générale formelles et inscrite au registre du commerce ?",
            "assertion": "Autorisation / Réalité",
            "risque_si_non": "Modifications de capital irrégulières, risque juridique",
        },
        {
            "id": "CP-CI-02",
            "question": "Les distributions de dividendes sont-elles décidées en assemblée générale et leur comptabilisation et paiement sont-ils contrôlés ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Distributions non autorisées, atteinte au capital légal minimum",
        },
        {
            "id": "CP-CI-03",
            "question": "Les provisions pour risques et charges font-elles l'objet d'une revue annuelle par la direction avec documentation des hypothèses retenues ?",
            "assertion": "Évaluation / Surveillance",
            "risque_si_non": "Provisions insuffisantes ou excessives, lissage du résultat",
        },
        {
            "id": "CP-CI-04",
            "question": "Les provisions sont-elles constituées sur la base de critères objectifs (obligation probable, montant estimable) et non à des fins de lissage du résultat ?",
            "assertion": "Évaluation",
            "risque_si_non": "Provisions fictives ou injustifiées, résultat manipulé",
        },
        {
            "id": "CP-CI-05",
            "question": "L'affectation du résultat de l'exercice précédent est-elle conforme aux décisions de l'assemblée générale et correctement comptabilisée ?",
            "assertion": "Autorisation / Exactitude",
            "risque_si_non": "Résultat non affecté ou mal imputé (121 vs 120/129)",
        },
        {
            "id": "CP-CI-06",
            "question": "La dotation à la réserve légale est-elle calculée conformément aux obligations légales (5 % du bénéfice net jusqu'à 10 % du capital) ?",
            "assertion": "Exhaustivité / Exactitude",
            "risque_si_non": "Obligation légale non respectée, sanction possible",
        },
        {
            "id": "CP-CI-07",
            "question": "Les engagements hors bilan (cautions, garanties, hypothèques, avals) sont-ils recensés et mentionnés dans l'annexe aux comptes ?",
            "assertion": "Présentation / Exhaustivité",
            "risque_si_non": "Passifs éventuels non divulgués aux actionnaires et aux tiers",
        },
        {
            "id": "CP-CI-08",
            "question": "Les subventions d'investissement reçues sont-elles comptabilisées correctement et les quotes-parts virées au résultat calculées selon le plan d'amortissement lié ?",
            "assertion": "Évaluation / Exactitude",
            "risque_si_non": "Produits de subvention mal étalés, résultat distordu",
        },
        {
            "id": "CP-CI-09",
            "question": "Les opérations entre la société et ses actionnaires ou dirigeants (comptes courants, avances, conventions réglementées) sont-elles identifiées, autorisées et correctement présentées ?",
            "assertion": "Autorisation / Présentation",
            "risque_si_non": "Conventions réglementées non déclarées, risque de conflits d'intérêts",
        },
        {
            "id": "CP-CI-10",
            "question": "Le résultat comptable est-il réconcilié avec le résultat fiscal pour documenter les différences temporaires et permanentes ?",
            "assertion": "Exactitude / Présentation",
            "risque_si_non": "Impôts différés mal calculés, distorsion de l'image fidèle",
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
    # Barème prudent : le questionnaire est déclaratif (aucun test d'efficacité).
    # « Faible » exige en outre ZÉRO réponse « non » (voir calculer_niveau_risque).
    "faible":  {"seuil_min": 0.85, "label": "Faible", "couleur": "emerald",
                "implication": "Environnement de contrôle favorable. L'étendue des travaux substantifs "
                               "n'est pas réduite pour autant sans test d'efficacité du contrôle interne."},
    "moyen":   {"seuil_min": 0.50, "label": "Moyen", "couleur": "amber",
                "implication": "Faiblesses identifiées. Renforcez les tests sur les zones concernées."},
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

    # Chaque « non » est une faiblesse avouée : un risque CI « faible »
    # exige un score élevé ET aucune faiblesse déclarée.
    niveau = "eleve"
    for key, cfg in NIVEAUX_RISQUE_CI.items():
        if score >= cfg["seuil_min"]:
            niveau = key
            break
    if niveau == "faible" and nb_non > 0:
        niveau = "moyen"

    return {
        "score": round(score, 2),
        "niveau": niveau,
        "nb_oui": nb_oui,
        "nb_non": nb_non,
        "nb_na": nb_na,
        **NIVEAUX_RISQUE_CI[niveau],
    }

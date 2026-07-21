"""Registre des contrôles déterministes — normes en données, pas en dur.

Les définitions ci-dessous sont écrites avec le préfixe historique « NEP » ;
`enregistrer()` les normalise au chargement dans le référentiel actif du
cabinet (ISA par défaut, NEP en option — voir probare_engine.normes).
La numérotation étant identique entre NEP et ISA, seule la présentation change.

M4 (ISA 315 révisée) : chaque contrôle déclare les ASSERTIONS qu'il couvre.
C'est ce qui permet de démontrer, risque par risque, que chaque assertion à
risque est couverte par au moins une procédure (matrice de couverture).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from ..normes import reformater_refs


# Vocabulaire canonique des assertions d'audit — le même que celui utilisé par
# la cartographie des risques (table `risque.assertions`) et par l'IA.
ASSERTIONS: dict[str, str] = {
    "existence":    "Existence / Réalité",
    "exhaustivite": "Exhaustivité",
    "evaluation":   "Évaluation / Exactitude",
    "cut_off":      "Séparation des exercices (cut-off)",
    "droits":       "Droits et obligations",
    "presentation": "Présentation / Classement",
}


@dataclass
class ControleDefinition:
    ref: str
    libelle: str
    nep_ref: str  # référence de norme, rendue dans le référentiel actif
    cycle: str
    description: str
    severite_defaut: str = "significative"
    # Assertions couvertes par le contrôle (codes du vocabulaire ASSERTIONS)
    assertions: list[str] = field(default_factory=list)


REGISTRE: dict[str, ControleDefinition] = {}


def enregistrer(defn: ControleDefinition) -> ControleDefinition:
    inconnues = [a for a in defn.assertions if a not in ASSERTIONS]
    if inconnues:
        raise ValueError(f"Contrôle {defn.ref} : assertions inconnues {inconnues}. "
                         f"Vocabulaire : {sorted(ASSERTIONS)}")
    defn.nep_ref = reformater_refs(defn.nep_ref)
    defn.description = reformater_refs(defn.description)
    REGISTRE[defn.ref] = defn
    return defn


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE TRÉSORERIE (comptes 5xx) — 8 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="TRESOR-BAL-EQUIL",
    assertions=["evaluation"],
    libelle="Équilibre de la balance",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="Vérifie que la somme des débits égale la somme des crédits dans la balance.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="La somme des mouvements du grand livre par compte (5xx) doit égaler le solde de la balance.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-SEQ-PIECES",
    assertions=["exhaustivite"],
    libelle="Continuité des séquences de pièces",
    nep_ref="NEP 330",
    cycle="tresorerie",
    description="Détecte les trous et doublons dans la numérotation des pièces comptables.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="TRESOR-VARIATION",
    assertions=["evaluation"],
    libelle="Variations N/N-1 trésorerie",
    nep_ref="NEP 520",
    cycle="tresorerie",
    description="Identifie les variations de solde des comptes de trésorerie dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="TRESOR-RAPPROCH",
    assertions=["existence", "evaluation"],
    libelle="Rapprochement bancaire",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="Rapprochement entre solde comptable et solde relevé bancaire.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-SOLDE-ANORMAL",
    assertions=["evaluation", "presentation"],
    libelle="Soldes créditeurs anormaux — Trésorerie",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description=(
        "Détecte les comptes de trésorerie (5xx) présentant un solde créditeur anormal. "
        "Un compte de trésorerie ne devrait pas avoir de solde net créditeur hors découvert autorisé."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="TRESOR-ROUND",
    assertions=["existence"],
    libelle="Concentration de montants ronds — Trésorerie",
    nep_ref="NEP 520",
    cycle="tresorerie",
    description=(
        "Détecte une proportion anormalement élevée de montants ronds (multiples de 100) "
        "dans les mouvements de trésorerie. Un ratio > 40 % est suspect (montants fictifs potentiels)."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="TRESOR-CUT-OFF",
    assertions=["cut_off"],
    libelle="Concentration d'écritures en fin d'exercice — Trésorerie",
    nep_ref="NEP 330",
    cycle="tresorerie",
    description=(
        "Détecte une concentration anormale d'écritures de trésorerie dans les 15 derniers jours "
        "de l'exercice. Un ratio > 30 % signale un risque de cut-off ou de manipulation."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE ACHATS-FOURNISSEURS (comptes 40x + 60x-62x) — 9 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="ACHAT-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Achats",
    nep_ref="NEP 500",
    cycle="achats",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes fournisseurs (40x) "
        "et charges (60x-62x) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="ACHAT-SEQ-FACTURES",
    assertions=["exhaustivite"],
    libelle="Continuité des séquences de factures — Achats",
    nep_ref="NEP 330",
    cycle="achats",
    description="Détecte les trous et doublons dans les numéros de factures fournisseurs.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="ACHAT-VARIATION",
    assertions=["evaluation"],
    libelle="Variations N/N-1 — Achats",
    nep_ref="NEP 520",
    cycle="achats",
    description="Variations des charges d'achats dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="ACHAT-SOLDE-DEBITEUR",
    assertions=["evaluation", "presentation"],
    libelle="Soldes débiteurs anormaux — Fournisseurs",
    nep_ref="NEP 500",
    cycle="achats",
    description=(
        "Détecte les comptes fournisseurs (40x) présentant un solde débiteur net. "
        "Un fournisseur a normalement un solde créditeur (somme due). Un solde débiteur "
        "signale un trop-versé, un avoir non apuré ou une erreur comptable."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="ACHAT-DOUBLON",
    assertions=["existence"],
    libelle="Doublons de factures fournisseurs",
    nep_ref="NEP 330",
    cycle="achats",
    description=(
        "Détecte les factures fournisseurs potentiellement en doublon : même montant, "
        "même compte fournisseur et même numéro de pièce (ou dates très proches). "
        "Risque de double paiement."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="ACHAT-CONCENTRATION",
    assertions=["existence"],
    libelle="Concentration des achats sur un fournisseur",
    nep_ref="NEP 520",
    cycle="achats",
    description=(
        "Détecte qu'un fournisseur représente plus de 30 % du total des achats. "
        "Risque de dépendance, de complaisance ou de fraude aux fournisseurs."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="ACHAT-AVOIR",
    assertions=["evaluation"],
    libelle="Ratio avoirs / achats anormal",
    nep_ref="NEP 520",
    cycle="achats",
    description=(
        "Détecte un ratio avoirs fournisseurs / total achats supérieur à 5 %. "
        "Un ratio élevé signale des contestations récurrentes, des retours marchandises "
        "ou des pratiques de régularisation suspectes."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="ACHAT-ROUND",
    assertions=["existence"],
    libelle="Concentration de montants ronds — Achats",
    nep_ref="NEP 520",
    cycle="achats",
    description=(
        "Détecte une proportion anormalement élevée de factures fournisseurs à montants ronds. "
        "Un ratio > 40 % peut indiquer des factures fictives ou de complaisance."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="ACHAT-CUT-OFF",
    assertions=["cut_off"],
    libelle="Achats concentrés en fin d'exercice",
    nep_ref="NEP 330",
    cycle="achats",
    description=(
        "Détecte une concentration anormale de factures d'achats dans les 15 derniers jours "
        "de l'exercice. Risque de rattachement à la mauvaise période (cut-off)."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE VENTES-CLIENTS (comptes 41x + 70x-72x) — 10 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="VENTE-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Ventes",
    nep_ref="NEP 500",
    cycle="ventes",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes clients (41x) "
        "et produits (70x-72x) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="VENTE-SEQ-FACTURES",
    assertions=["exhaustivite"],
    libelle="Continuité des séquences de factures — Ventes",
    nep_ref="NEP 330",
    cycle="ventes",
    description="Détecte les trous et doublons dans les numéros de factures clients.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="VENTE-VARIATION",
    assertions=["evaluation"],
    libelle="Variations N/N-1 — Ventes",
    nep_ref="NEP 520",
    cycle="ventes",
    description="Variations des produits de vente dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="VENTE-SOLDE-CREDITEUR",
    assertions=["evaluation", "presentation"],
    libelle="Soldes créditeurs anormaux — Clients",
    nep_ref="NEP 500",
    cycle="ventes",
    description=(
        "Détecte les comptes clients (41x) présentant un solde créditeur net. "
        "Un client a normalement un solde débiteur (il nous doit). Un solde créditeur "
        "signale un trop-perçu, un avoir non apuré ou une erreur comptable."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="VENTE-DOUBLON",
    assertions=["existence"],
    libelle="Doublons de factures clients",
    nep_ref="NEP 330",
    cycle="ventes",
    description=(
        "Détecte les factures clients potentiellement en doublon : même montant, "
        "même compte client et même numéro de pièce. Risque de double comptabilisation."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="VENTE-CONCENTRATION",
    assertions=["evaluation"],
    libelle="Concentration des ventes sur un client",
    nep_ref="NEP 520",
    cycle="ventes",
    description=(
        "Détecte qu'un client représente plus de 30 % du total des ventes. "
        "Risque de dépendance commerciale et d'impact en cas de défaillance."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="VENTE-AVOIR",
    assertions=["existence"],
    libelle="Ratio avoirs / ventes anormal",
    nep_ref="NEP 520",
    cycle="ventes",
    description=(
        "Détecte un ratio avoirs clients / total ventes supérieur à 5 %. "
        "Peut indiquer des retours anormaux, des litiges récurrents ou des revenus surévalués."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="VENTE-ROUND",
    assertions=["existence"],
    libelle="Concentration de montants ronds — Ventes",
    nep_ref="NEP 520",
    cycle="ventes",
    description="Proportion anormalement élevée de factures clients à montants ronds (> 40 %).",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="VENTE-CUT-OFF",
    assertions=["cut_off"],
    libelle="Ventes concentrées en fin d'exercice",
    nep_ref="NEP 330",
    cycle="ventes",
    description=(
        "Détecte une concentration anormale de factures de vente dans les 15 derniers jours "
        "de l'exercice. Risque de reconnaissance anticipée des produits (revenue recognition)."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="VENTE-CREANCES-ECHUES",
    assertions=["evaluation"],
    libelle="Créances clients anciennes (> 90 jours)",
    nep_ref="NEP 500",
    cycle="ventes",
    description=(
        "Détecte les créances clients dont la date d'émission dépasse 90 jours avant la clôture. "
        "Risque d'irrécouvrabilité non provisionné. NEP 500 : caractère recouvrable des créances."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE IMMOBILISATIONS (comptes 2xx) — 5 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="IMO-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Immobilisations",
    nep_ref="NEP 500",
    cycle="immobilisations",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes d'immobilisations (2xx) "
        "et d'amortissements (28xx) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="IMO-AMORTISSEMENT",
    assertions=["evaluation"],
    libelle="Sous-amortissement — Immobilisations sans amortissements cumulés",
    nep_ref="NEP 500",
    cycle="immobilisations",
    description=(
        "Détecte des immobilisations amortissables (21x-25x) présentant une valeur nette "
        "positive sans aucun amortissement cumulé correspondant (28xx). "
        "Risque de non-respect du plan d'amortissement."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="IMO-AMORT-EXCEDENT",
    assertions=["evaluation"],
    libelle="Amortissements cumulés supérieurs à la valeur brute",
    nep_ref="NEP 500",
    cycle="immobilisations",
    description=(
        "Détecte un total d'amortissements cumulés (28xx) supérieur à la valeur brute "
        "des immobilisations (2xx hors 28xx). "
        "Une immobilisation ne peut être amortie au-delà de sa valeur d'acquisition."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="IMO-VARIATION",
    assertions=["existence", "evaluation"],
    libelle="Variations N/N-1 — Immobilisations",
    nep_ref="NEP 520",
    cycle="immobilisations",
    description=(
        "Identifie les variations de solde des comptes d'immobilisations (2xx) "
        "dépassant le seuil de signification. Une variation importante signale "
        "des acquisitions, cessions ou réévaluations à documenter."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="IMO-SOLDE-ANORMAL",
    assertions=["evaluation", "presentation"],
    libelle="Soldes créditeurs anormaux — Immobilisations brutes",
    nep_ref="NEP 500",
    cycle="immobilisations",
    description=(
        "Détecte les comptes d'immobilisations brutes (20x-27x hors 28x) "
        "présentant un solde créditeur net. "
        "La valeur brute d'une immobilisation doit être débitrice."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE STOCKS (comptes 3xx) — 5 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="STOCK-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Stocks",
    nep_ref="NEP 500",
    cycle="stocks",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes de stocks (3xx) "
        "correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="STOCK-SOLDE-ANORMAL",
    assertions=["evaluation"],
    libelle="Soldes créditeurs anormaux — Stocks",
    nep_ref="NEP 500",
    cycle="stocks",
    description=(
        "Détecte les comptes de stocks (3xx) présentant un solde créditeur net. "
        "Un stock ne peut pas avoir de valeur négative — signale une erreur comptable "
        "ou une valorisation incorrecte."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="STOCK-VARIATION",
    assertions=["evaluation"],
    libelle="Variations N/N-1 — Stocks",
    nep_ref="NEP 520",
    cycle="stocks",
    description=(
        "Identifie les variations de solde des comptes de stocks (3xx) "
        "dépassant le seuil de signification. "
        "Peut signaler un changement de méthode de valorisation ou une anomalie."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="STOCK-ROUND",
    assertions=["existence", "evaluation"],
    libelle="Concentration de montants ronds — Stocks",
    nep_ref="NEP 520",
    cycle="stocks",
    description=(
        "Détecte une proportion anormalement élevée de valorisations rondes dans les "
        "mouvements de stocks. Un ratio > 40 % signale une valorisation estimée ou fictive."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="STOCK-CUT-OFF",
    assertions=["cut_off"],
    libelle="Mouvements de stocks concentrés en fin d'exercice",
    nep_ref="NEP 330",
    cycle="stocks",
    description=(
        "Détecte une concentration anormale de mouvements de stocks dans les 15 derniers jours "
        "de l'exercice. Risque de cut-off (rattachement à la mauvaise période) "
        "ou de manipulation des inventaires de clôture."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE PAIE / PERSONNEL (comptes 64x + 42x) — 5 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="PAIE-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Paie",
    nep_ref="NEP 500",
    cycle="paie",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes de charges de personnel "
        "(64x) et de dettes sociales (42x) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="PAIE-VARIATION",
    assertions=["existence", "evaluation"],
    libelle="Variations N/N-1 — Charges de personnel",
    nep_ref="NEP 520",
    cycle="paie",
    description=(
        "Identifie les variations des charges de personnel (64x) dépassant le seuil "
        "de signification. Une variation importante peut signaler des embauches ou départs "
        "non documentés, des augmentations anormales ou des charges fictives."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="PAIE-RATIO-SOCIAL",
    assertions=["exhaustivite", "evaluation"],
    libelle="Ratio charges sociales / salaires bruts hors norme",
    nep_ref="NEP 520",
    cycle="paie",
    description=(
        "Vérifie que le ratio cotisations patronales (645x) / salaires bruts (641x) "
        "se situe dans la fourchette attendue (20 %–60 %). "
        "Un ratio hors norme signale une sous-déclaration ou une anomalie structurelle."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="PAIE-MENSUALITE",
    assertions=["exhaustivite"],
    libelle="Régularité mensuelle des salaires",
    nep_ref="NEP 330",
    cycle="paie",
    description=(
        "Vérifie que des écritures de paie (641x) sont présentes dans au moins 10 mois "
        "de l'exercice. Des mois sans salaires signalent un risque d'omission "
        "ou de non-déclaration sur certaines périodes."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="PAIE-SOLDE-ANORMAL",
    assertions=["evaluation", "presentation"],
    libelle="Soldes débiteurs anormaux — Dettes sociales",
    nep_ref="NEP 500",
    cycle="paie",
    description=(
        "Détecte les comptes de dettes sociales (42x) présentant un solde débiteur net. "
        "Ces comptes doivent normalement être créditeurs (somme due aux organismes sociaux). "
        "Un solde débiteur signale un trop-versé ou une erreur comptable."
    ),
    severite_defaut="significative",
))


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE IMPÔTS / TAXES (comptes 44x + 63x) — 5 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="TAXE-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Impôts et taxes",
    nep_ref="NEP 500",
    cycle="impots",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes de TVA/impôts (44x) "
        "et charges fiscales (63x) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TAXE-VARIATION",
    assertions=["evaluation"],
    libelle="Variations N/N-1 — Impôts et taxes",
    nep_ref="NEP 520",
    cycle="impots",
    description=(
        "Identifie les variations des charges fiscales (63x) et comptes de TVA (44x) "
        "dépassant le seuil de signification. "
        "Peut signaler un changement de régime fiscal ou une anomalie déclarative."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="TAXE-TVA-COHERENCE",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence TVA déductible / TVA collectée",
    nep_ref="NEP 520",
    cycle="impots",
    description=(
        "Vérifie que la TVA déductible (4456x) ne dépasse pas anormalement la TVA collectée "
        "(4457x). Un ratio TVA déductible / collectée > 110 % est suspect sauf justification "
        "(exportateur, investissements exceptionnels)."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="TAXE-SOLDE-ANORMAL",
    assertions=["evaluation", "presentation"],
    libelle="Soldes anormaux — Comptes de TVA et impôts",
    nep_ref="NEP 500",
    cycle="impots",
    description=(
        "Détecte les comptes de TVA collectée (4457x) présentant un solde débiteur "
        "et les comptes de TVA déductible (4456x) présentant un solde créditeur. "
        "Ces situations sont anormales et signalent une erreur ou manipulation."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="TAXE-CUT-OFF",
    assertions=["cut_off"],
    libelle="Charges fiscales concentrées en fin d'exercice",
    nep_ref="NEP 330",
    cycle="impots",
    description=(
        "Détecte une concentration anormale d'écritures fiscales (63x) dans les 15 derniers "
        "jours de l'exercice. Risque de rattachement à la mauvaise période (cut-off) "
        "ou de régularisation fiscale de fin d'année suspecte."
    ),
    severite_defaut="significative",
))



# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE CAPITAUX PROPRES ET PROVISIONS (comptes 10x-15x) — 5 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="CP-GL-COHER",
    assertions=["exhaustivite", "evaluation"],
    libelle="Cohérence grand livre / balance — Capitaux propres",
    nep_ref="NEP 500",
    cycle="capitaux_propres",
    description=(
        "Vérifie que les mouvements du grand livre pour les comptes de capitaux propres "
        "(10x-15x) correspondent aux soldes de la balance."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="CP-VARIATION",
    assertions=["droits", "evaluation"],
    libelle="Variations N/N-1 — Capitaux propres",
    nep_ref="NEP 520",
    cycle="capitaux_propres",
    description=(
        "Identifie les variations des capitaux propres (10x-13x) dépassant le seuil de "
        "signification. Une variation importante signale des distributions, augmentations "
        "de capital ou affectations de résultat à documenter."
    ),
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="CP-PROVISION-MOUVEMENT",
    assertions=["existence", "evaluation"],
    libelle="Mouvements de provisions pour risques sans charge (15x / 68x)",
    nep_ref="NEP 500",
    cycle="capitaux_propres",
    description=(
        "Détecte des dotations aux provisions pour risques et charges (crédit 15x) sans "
        "charge de dotation correspondante en 68x. "
        "Risque de provision sans justification comptable ou de provision fictive."
    ),
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="CP-RESULTAT-COHERENCE",
    assertions=["evaluation", "presentation"],
    libelle="Cohérence des comptes de résultat (120 / 129)",
    nep_ref="NEP 500",
    cycle="capitaux_propres",
    description=(
        "Vérifie que les comptes 120 (résultat bénéficiaire) et 129 (résultat déficitaire) "
        "ne sont pas tous deux non nuls simultanément. "
        "Une entité ne peut avoir à la fois un résultat bénéficiaire et déficitaire."
    ),
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="CP-SOLDE-ANORMAL",
    assertions=["evaluation", "presentation"],
    libelle="Capitaux propres négatifs — Soldes débiteurs anormaux",
    nep_ref="NEP 500",
    cycle="capitaux_propres",
    description=(
        "Détecte les comptes de capitaux propres (10x-13x) présentant un solde débiteur net. "
        "Des capitaux propres négatifs ou un capital débiteur signalent un risque important "
        "pour la continuité d'exploitation."
    ),
    severite_defaut="critique",
))


def get_controles_par_cycle(cycle: str) -> list[ControleDefinition]:
    return [c for c in REGISTRE.values() if c.cycle == cycle]


def controles_couvrant(cycle: str, assertion: str) -> list[ControleDefinition]:
    """Contrôles du cycle donné qui couvrent l'assertion donnée (M4)."""
    return [c for c in REGISTRE.values()
            if c.cycle == cycle and assertion in c.assertions]

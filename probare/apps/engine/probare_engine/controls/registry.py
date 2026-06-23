"""Registre des contrôles déterministes — NEP en données, pas en dur."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ControleDefinition:
    ref: str
    libelle: str
    nep_ref: str
    cycle: str
    description: str
    severite_defaut: str = "significative"


REGISTRE: dict[str, ControleDefinition] = {}


def enregistrer(defn: ControleDefinition) -> ControleDefinition:
    REGISTRE[defn.ref] = defn
    return defn


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE TRÉSORERIE (comptes 5xx) — 8 contrôles
# ═══════════════════════════════════════════════════════════════════════════════

enregistrer(ControleDefinition(
    ref="TRESOR-BAL-EQUIL",
    libelle="Équilibre de la balance",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="Vérifie que la somme des débits égale la somme des crédits dans la balance.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-GL-COHER",
    libelle="Cohérence grand livre / balance",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="La somme des mouvements du grand livre par compte (5xx) doit égaler le solde de la balance.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-SEQ-PIECES",
    libelle="Continuité des séquences de pièces",
    nep_ref="NEP 330",
    cycle="tresorerie",
    description="Détecte les trous et doublons dans la numérotation des pièces comptables.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="TRESOR-VARIATION",
    libelle="Variations N/N-1 trésorerie",
    nep_ref="NEP 520",
    cycle="tresorerie",
    description="Identifie les variations de solde des comptes de trésorerie dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="TRESOR-RAPPROCH",
    libelle="Rapprochement bancaire",
    nep_ref="NEP 500",
    cycle="tresorerie",
    description="Rapprochement entre solde comptable et solde relevé bancaire.",
    severite_defaut="critique",
))

enregistrer(ControleDefinition(
    ref="TRESOR-SOLDE-ANORMAL",
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
    libelle="Continuité des séquences de factures — Achats",
    nep_ref="NEP 330",
    cycle="achats",
    description="Détecte les trous et doublons dans les numéros de factures fournisseurs.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="ACHAT-VARIATION",
    libelle="Variations N/N-1 — Achats",
    nep_ref="NEP 520",
    cycle="achats",
    description="Variations des charges d'achats dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="ACHAT-SOLDE-DEBITEUR",
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
    libelle="Continuité des séquences de factures — Ventes",
    nep_ref="NEP 330",
    cycle="ventes",
    description="Détecte les trous et doublons dans les numéros de factures clients.",
    severite_defaut="significative",
))

enregistrer(ControleDefinition(
    ref="VENTE-VARIATION",
    libelle="Variations N/N-1 — Ventes",
    nep_ref="NEP 520",
    cycle="ventes",
    description="Variations des produits de vente dépassant le seuil de signification.",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="VENTE-SOLDE-CREDITEUR",
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
    libelle="Concentration de montants ronds — Ventes",
    nep_ref="NEP 520",
    cycle="ventes",
    description="Proportion anormalement élevée de factures clients à montants ronds (> 40 %).",
    severite_defaut="mineure",
))

enregistrer(ControleDefinition(
    ref="VENTE-CUT-OFF",
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
    libelle="Créances clients anciennes (> 90 jours)",
    nep_ref="NEP 500",
    cycle="ventes",
    description=(
        "Détecte les créances clients dont la date d'émission dépasse 90 jours avant la clôture. "
        "Risque d'irrécouvrabilité non provisionné. NEP 500 : caractère recouvrable des créances."
    ),
    severite_defaut="significative",
))


def get_controles_par_cycle(cycle: str) -> list[ControleDefinition]:
    return [c for c in REGISTRE.values() if c.cycle == cycle]

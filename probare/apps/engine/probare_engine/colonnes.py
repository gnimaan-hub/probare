"""Classification des colonnes de montant d'un fichier comptable.

Module neutre partagé par l'ingestion (`ingestion/excel_csv.py`) et le moteur
de contrôles (`controls/engine.py`) : les deux doivent classer un nom de
colonne exactement de la même façon, sinon une colonne ingérée sous un champ
est relue sous un autre.

Point clé : une balance porte souvent QUATRE colonnes de montant — « mvt
débit », « mvt crédit », « solde débit », « solde crédit ». Les colonnes de
SOLDE et les colonnes de MOUVEMENT sont des grandeurs différentes et ne
doivent jamais être confondues : le solde net d'un compte est
`solde débit − solde crédit`, jamais un solde diminué d'un mouvement.
"""
from __future__ import annotations

# Marqueurs recherchés dans un nom de colonne normalisé (minuscules, sans
# espaces superflus). Les variantes accentuées et non accentuées coexistent
# car les exports comptables ne sont pas homogènes.
MOTS_SOLDE = ("solde", "balance", "sold")
MOTS_DEBIT = ("debit", "débit", " db", ":db", "db:")
MOTS_CREDIT = ("credit", "crédit", " cr", ":cr", "cr:")

# Champs montants canoniques produits par la classification.
CHAMPS_MONTANT = ("solde_debit", "solde_credit", "solde", "debit", "credit")


def classer_colonne_montant(nom: str) -> str | None:
    """Classe un nom de colonne en champ montant canonique, ou None.

    Le test « solde » passe AVANT « débit »/« crédit » : « solde débit »
    contient les deux marqueurs et doit être classé en solde, pas en mouvement.

    - « solde débit » / « solde débiteur »  → ``solde_debit``
    - « solde crédit » / « solde créditeur »→ ``solde_credit``
    - « solde » / « balance » (signé)       → ``solde``
    - « débit » / « mvt débit »             → ``debit``   (mouvement)
    - « crédit » / « mvt crédit »           → ``credit``  (mouvement)
    """
    nom = (nom or "").lower().strip()
    est_solde = any(m in nom for m in MOTS_SOLDE)
    est_debit = any(m in nom for m in MOTS_DEBIT)
    est_credit = any(m in nom for m in MOTS_CREDIT)

    if est_solde and est_debit:
        return "solde_debit"
    if est_solde and est_credit:
        return "solde_credit"
    if est_solde:
        return "solde"
    if est_debit:
        return "debit"
    if est_credit:
        return "credit"
    return None

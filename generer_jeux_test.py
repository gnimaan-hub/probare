"""Génère 3 couples balance/grand livre pour tester les contrôles Probare."""
import csv
import os

OUT = r"D:\projet\Audit_Comptable\probare\test_data"
os.makedirs(OUT, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=",")
        w.writerow(headers)
        w.writerows(rows)
    print(f"  Créé : {path}")


# ──────────────────────────────────────────────────────────────────────────────
# EXERCICE 2024 — CORRECT
# Σ débit = 74 500 000  /  Σ crédit = 74 500 000  /  Pièces 1001→1020 sans trou
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== Exercice 2024 (CORRECT) ===")

balance_2024 = [
    # compte, libelle,                    debit,      credit,    exercice
    ["101",  "Capital social",             0,          30000000,  2024],
    ["106",  "Réserves légales",           0,           5000000,  2024],
    ["161",  "Emprunts BCI long terme",    0,          18000000,  2024],
    ["401",  "Fournisseurs divers",        0,          12500000,  2024],
    ["404",  "Fournisseurs d'immo",        0,           3000000,  2024],
    ["411",  "Clients Djibouti",       22000000,           0,     2024],
    ["416",  "Clients douteux",         3500000,            0,    2024],
    ["512",  "Banque BCI — CC n°4521",  31500000,           0,    2024],
    ["514",  "Banque CFE — CC n°8830",   8000000,           0,    2024],
    ["531",  "Caisse principale",         7000000,           0,    2024],
    ["601",  "Achats matières premières", 14000000,          0,    2024],
    ["624",  "Transports sur achats",      2500000,          0,    2024],
    ["641",  "Rémunérations du personnel", 15000000,         0,    2024],
    ["706",  "Prestations de services",    0,         35000000,    2024],
]
# Vérification : Σ débit = Σ crédit
sd = sum(r[2] for r in balance_2024)
sc = sum(r[3] for r in balance_2024)
assert sd == sc == 103500000, f"Balance 2024 déséquilibrée : {sd} vs {sc}"

write_csv(
    os.path.join(OUT, "balance_2024.csv"),
    ["compte", "libelle", "debit", "credit", "exercice"],
    balance_2024,
)

# Grand livre 2024 : 20 écritures, pièces 1001 à 1020 — séquence parfaite
grand_livre_2024 = [
    # compte, libelle,                          date,         numero_piece, debit,     credit
    ["512", "Virement reçu client Al-Baraka",  "2024-01-08",  1001,      8500000,       0],
    ["512", "Paiement fournisseur Ali Trading", "2024-01-15", 1002,           0,  3200000],
    ["512", "Encaissement facture F-2401",      "2024-01-22",  1003,     6200000,       0],
    ["512", "Virement loyer local commercial",  "2024-01-31",  1004,          0,  1800000],
    ["531", "Versement espèces caisse",         "2024-02-05",  1005,     2000000,       0],
    ["512", "Encaissement client Ibrahim & Co", "2024-02-12",  1006,     5800000,       0],
    ["512", "Règlement fournisseur Petrom",     "2024-02-20",  1007,           0,  2750000],
    ["531", "Paiement petites dépenses",        "2024-02-25",  1008,           0,   185000],
    ["512", "Virement reçu client Osman",       "2024-03-04",  1009,     4200000,       0],
    ["514", "Virement inter-comptes",           "2024-03-10",  1010,     8000000,       0],
    ["512", "Encaissement facture F-2406",      "2024-03-18",  1011,     3100000,       0],
    ["512", "Paiement salaires mars",           "2024-03-28",  1012,           0,  5000000],
    ["531", "Versement espèces caisse",         "2024-04-02",  1013,     1500000,       0],
    ["512", "Encaissement client Aden Port",    "2024-04-15",  1014,     7200000,       0],
    ["512", "Règlement fournisseur Somali Oil",  "2024-04-22", 1015,           0,  2100000],
    ["531", "Paiement petites dépenses",        "2024-04-30",  1016,           0,   315000],
    ["512", "Encaissement facture F-2410",      "2024-05-08",  1017,     4800000,       0],
    ["512", "Virement reçu client PAID",        "2024-05-20",  1018,     5200000,       0],
    ["512", "Paiement fournisseur Djibouti Gas","2024-05-28",  1019,           0,  1950000],
    ["531", "Versement espèces caisse",         "2024-06-01",  1020,     2000000,       0],
]

write_csv(
    os.path.join(OUT, "grand_livre_2024.csv"),
    ["compte", "libelle", "date", "numero_piece", "debit", "credit"],
    grand_livre_2024,
)


# ──────────────────────────────────────────────────────────────────────────────
# EXERCICE 2023 — ERREUR 1 : Déséquilibre balance + ERREUR 2 : Trous séquence
#
# ERREUR 1 — TRESOR-BAL-EQUIL :
#   Compte 512 affiché à 35 000 000 XDJ au débit
#   alors que le total correct serait 28 500 000 XDJ.
#   → Écart = 6 500 000 XDJ  (Σ débit > Σ crédit)
#
# ERREUR 2 — TRESOR-SEQ-PIECES :
#   Pièces attendues 1001→1018 (18 pièces)
#   Pièces manquantes : 1004, 1007, 1011  → 3 trous
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== Exercice 2023 (ERREURS : déséquilibre + trous de pièces) ===")

balance_2023 = [
    # compte, libelle,                        debit,       credit,   exercice
    ["101",  "Capital social",                 0,          25000000,  2023],
    ["106",  "Réserves légales",               0,           3500000,  2023],
    ["161",  "Emprunts BCI long terme",        0,          21000000,  2023],
    ["401",  "Fournisseurs divers",            0,           9500000,  2023],
    ["411",  "Clients Djibouti",           18500000,            0,    2023],
    ["416",  "Clients douteux",             2000000,            0,    2023],
    # ↓ ERREUR : valeur saisie 35 000 000 — valeur correcte = 28 500 000
    # → Écart intentionnel de 6 500 000 XDJ sur ce compte
    ["512",  "Banque BCI — CC n°4521 [ERREUR: 6 500 000 en trop]",
                                           35000000,            0,    2023],
    ["514",  "Banque CFE — CC n°8830",      6500000,            0,    2023],
    ["531",  "Caisse principale",           5500000,            0,    2023],
    ["601",  "Achats matières premières",  11000000,            0,    2023],
    ["624",  "Transports sur achats",       2000000,            0,    2023],
    ["641",  "Rémunérations du personnel",  13000000,           0,    2023],
    ["706",  "Prestations de services",         0,          30000000,  2023],
]
sd = sum(r[2] for r in balance_2023)
sc = sum(r[3] for r in balance_2023)
assert sd != sc, "La balance 2023 devrait être déséquilibrée"
print(f"  [OK] Balance 2023 desEquilibree : Total debit={sd:,} / Total credit={sc:,} / Ecart={sd-sc:,} XDJ")

write_csv(
    os.path.join(OUT, "balance_2023.csv"),
    ["compte", "libelle", "debit", "credit", "exercice"],
    balance_2023,
)

# Grand livre 2023 : pièces 1001→1018 avec trous sur 1004, 1007, 1011
pieces_2023 = [p for p in range(1001, 1019) if p not in (1004, 1007, 1011)]
print(f"  [OK] Pièces présentes : {pieces_2023}")
print(f"  [OK] Trous attendus   : [1004, 1007, 1011]")

libelles_2023 = [
    ("512", "Encaissement client Abdourahman",  "2023-01-10",  6200000,       0),
    ("512", "Paiement fournisseur Gulf Trade",   "2023-01-18",       0, 2800000),
    ("531", "Versement espèces caisse",          "2023-01-25",  1800000,       0),
    # pièce 1004 manquante (saut intentionnel)
    ("512", "Encaissement facture F-2302",       "2023-02-08",  4500000,       0),
    ("512", "Règlement loyer bureau",            "2023-02-15",       0, 1600000),
    # pièce 1007 manquante (saut intentionnel)
    ("512", "Virement reçu client Port PAID",    "2023-02-28",  3800000,       0),
    ("531", "Paiement petites dépenses",         "2023-03-05",       0,  145000),
    ("512", "Encaissement client Haile Corp",    "2023-03-12",  5100000,       0),
    ("512", "Paiement salaires février",         "2023-03-20",       0, 4200000),
    # pièce 1011 manquante (saut intentionnel)
    ("514", "Virement inter-comptes",            "2023-04-02",  6500000,       0),
    ("512", "Encaissement facture F-2308",       "2023-04-10",  3200000,       0),
    ("512", "Règlement fournisseur Arta Oil",    "2023-04-18",       0, 1950000),
    ("531", "Versement espèces caisse",          "2023-04-25",  2000000,       0),
    ("512", "Encaissement client Youssouf SA",   "2023-05-03",  4800000,       0),
    ("512", "Paiement fournisseur Berbera Int.", "2023-05-15",       0, 2200000),
]

grand_livre_2023 = []
for i, (piece, row) in enumerate(zip(pieces_2023, libelles_2023)):
    compte, libelle, date, debit, credit = row
    grand_livre_2023.append([compte, libelle, date, piece, debit, credit])

write_csv(
    os.path.join(OUT, "grand_livre_2023.csv"),
    ["compte", "libelle", "date", "numero_piece", "debit", "credit"],
    grand_livre_2023,
)


# ──────────────────────────────────────────────────────────────────────────────
# EXERCICE 2022 — ERREUR : Balance équilibrée + Doublons de pièces
#
# ERREUR — TRESOR-SEQ-PIECES :
#   La pièce 1003 a été enregistrée deux fois (saisie en double)
#   La pièce 1007 a également un doublon (même numéro pour deux écritures différentes)
#   → 2 numéros en doublon détectés
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== Exercice 2022 (ERREUR : doublons de pièces — balance correcte) ===")

balance_2022 = [
    # compte, libelle,                       debit,       credit,   exercice
    ["101",  "Capital social",                 0,          20000000,  2022],
    ["106",  "Réserves légales",               0,           2000000,  2022],
    ["161",  "Emprunts BCI long terme",        0,          24000000,  2022],
    ["401",  "Fournisseurs divers",            0,           7000000,  2022],
    ["411",  "Clients Djibouti",           15000000,            0,    2022],
    ["416",  "Clients douteux",             1500000,            0,    2022],
    ["512",  "Banque BCI — CC n°4521",     24000000,            0,    2022],
    ["514",  "Banque CFE — CC n°8830",      5000000,            0,    2022],
    ["531",  "Caisse principale",            4500000,            0,    2022],
    ["601",  "Achats matières premières",   9000000,             0,    2022],
    ["624",  "Transports sur achats",        1500000,            0,    2022],
    ["641",  "Rémunérations du personnel",  12000000,            0,    2022],
    ["706",  "Prestations de services",         0,          19500000,  2022],
]
sd = sum(r[2] for r in balance_2022)
sc = sum(r[3] for r in balance_2022)
assert sd == sc == 72500000, f"Balance 2022 déséquilibrée : {sd} vs {sc}"
print(f"  [OK] Balance 2022 equilibree : Total debit = Total credit = {sd:,} XDJ")

write_csv(
    os.path.join(OUT, "balance_2022.csv"),
    ["compte", "libelle", "debit", "credit", "exercice"],
    balance_2022,
)

# Grand livre 2022 : pièces avec doublons sur 1003 et 1007
grand_livre_2022 = [
    # compte, libelle,                           date,         numero_piece, debit,    credit
    ["512", "Encaissement client Mahamoud",      "2022-01-12",  1001,      5800000,       0],
    ["512", "Paiement fournisseur Orient Trade", "2022-01-20",  1002,           0, 2300000],
    # ↓ ERREUR : pièce 1003 saisie une première fois
    ["512", "Encaissement facture F-2201",       "2022-01-28",  1003,      3500000,       0],
    # ↓ ERREUR : pièce 1003 saisie une deuxième fois (doublon — même numéro, écriture différente)
    ["531", "Versement caisse [DOUBLON pièce 1003]", "2022-02-01", 1003,  1200000,       0],
    ["512", "Règlement loyer janvier",           "2022-02-05",  1004,           0, 1500000],
    ["512", "Encaissement client Ibrahim",       "2022-02-14",  1005,      4200000,       0],
    ["512", "Paiement fournisseur Tadjourah",    "2022-02-22",  1006,           0, 1800000],
    # ↓ ERREUR : pièce 1007 saisie une première fois
    ["512", "Virement reçu client Djib Port",    "2022-03-01",  1007,      6000000,       0],
    # ↓ ERREUR : pièce 1007 saisie une deuxième fois (doublon)
    ["514", "Virement inter-comptes [DOUBLON pièce 1007]", "2022-03-05", 1007, 5000000, 0],
    ["512", "Encaissement facture F-2206",       "2022-03-12",  1008,      3800000,       0],
    ["531", "Paiement petites dépenses",         "2022-03-18",  1009,           0,  165000],
    ["512", "Encaissement client Awash SA",      "2022-04-02",  1010,      4500000,       0],
    ["512", "Paiement salaires mars",            "2022-04-08",  1011,           0, 3800000],
    ["531", "Versement espèces caisse",          "2022-04-15",  1012,      1200000,       0],
    ["512", "Encaissement client Port Obock",    "2022-04-22",  1013,      3200000,       0],
]
print(f"  [OK] Doublons attendus sur les pièces : [1003, 1007]")

write_csv(
    os.path.join(OUT, "grand_livre_2022.csv"),
    ["compte", "libelle", "date", "numero_piece", "debit", "credit"],
    grand_livre_2022,
)

print(f"\n=== 6 fichiers générés dans {OUT} ===\n")

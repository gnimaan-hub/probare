# -*- coding: utf-8 -*-
"""Générateur du jeu de test « HARBI MATÉRIAUX SARL » (société fictive, Djibouti).

Produit un dossier comptable complet et cohérent en partie double pour
l'exercice 2025 (comparatif 2024) :
  - grand_livre_2025.csv   : écritures de l'exercice, à-nouveaux inclus
  - balance_2025.csv       : soldes nets dérivés du grand livre (cohérence garantie)
  - balance_2024.csv       : balance N-1 équilibrée (bilan + comptes de gestion)
  - releve_bancaire_2025.csv : relevé BCIMR avec écart de rapprochement volontaire

Anomalies plantées (oracle du test de bout en bout) :
  A1  Rapprochement bancaire : chèque de 850 000 FDJ émis le 30/12 non
      débité au relevé + frais bancaires 12 500 FDJ non comptabilisés
      → écart net attendu : 837 500 FDJ (TRESOR-RAPPROCH)
  A2  Facture fournisseur saisie deux fois : même pièce, compte 601,
      2 340 000 FDJ (ACHAT-DOUBLON + doublon de séquence)
  A3  Trou de séquence : pièce 5087 jamais utilisée (SEQ-PIECES/FACTURES)
  A4  Concentration de ventes sur les 15 derniers jours de décembre
      (VENTE-CUT-OFF, > 30 % des lignes 70x)
  A5  Immobilisations 218 (6 400 000 + 3 500 000) sans amortissement cumulé
      2818 (IMO-AMORTISSEMENT)
  A6  Créance client de 2 447 350 FDJ facturée le 12/02/2025, toujours
      impayée au 31/12 (VENTE-CREANCES-ECHUES) + clients douteux 416 sans
      dépréciation
  A7  Variations N/N-1 marquées : CA +33 %, créances clients +47 %,
      stocks +38 % (contrôles VARIATION + procédures analytiques)
"""
from __future__ import annotations
import csv
from pathlib import Path

OUT = Path(__file__).parent

# ─── Séquence unique de pièces (numérique, comme un journal réel) ───────────
_PIECE = 5000
_TROU = 5087  # A3 : numéro sauté volontairement


def piece() -> str:
    global _PIECE
    _PIECE += 1
    if _PIECE == _TROU:
        _PIECE += 1
    return str(_PIECE)


# ─── Grand livre 2025 ────────────────────────────────────────────────────────
GL: list[dict] = []


def ecrire(date: str, num: str, lignes: list[tuple[str, str, int, int]]) -> None:
    """Ajoute une écriture équilibrée au grand livre."""
    total_d = sum(l[2] for l in lignes)
    total_c = sum(l[3] for l in lignes)
    assert total_d == total_c, f"Écriture déséquilibrée {num} du {date} : D={total_d} C={total_c}"
    for compte, libelle, debit, credit in lignes:
        GL.append({"compte": compte, "libelle": libelle, "date": date,
                   "numero_piece": num, "debit": debit, "credit": credit})


# ─── Bilan de clôture 2024 (= à-nouveaux 2025 après affectation du résultat) ─
BILAN_2024 = {
    # compte: (libellé, solde net ; positif = débiteur)
    "101":  ("Capital social",                     -40_000_000),
    "106":  ("Réserves légales",                    -6_500_000),
    "110":  ("Report à nouveau",                     None),  # calculé (équilibre)
    "164":  ("Emprunt BCIMR moyen terme",          -18_000_000),
    "215":  ("Matériel de transport",               28_000_000),
    "2815": ("Amort. matériel de transport",        -9_800_000),
    "218":  ("Matériel et mobilier de bureau",       6_400_000),
    "310":  ("Stocks de marchandises",              25_000_000),
    "401":  ("Fournisseurs",                       -14_300_000),
    "411":  ("Clients",                             22_000_000),
    "416":  ("Clients douteux",                      1_200_000),
    "421":  ("Personnel - rémunérations dues",      -1_900_000),
    "431":  ("CNSS - cotisations dues",               -950_000),
    "444":  ("État - impôt sur les bénéfices",      -1_900_000),
    "512":  ("Banque BCIMR",                        20_000_000),
    "531":  ("Caisse",                               1_100_000),
}

# Comptes de gestion 2024 (balance N-1 avant affectation)
GESTION_2024 = {
    "601":  ("Achats de marchandises",             104_000_000),
    "6031": ("Variation des stocks de march.",       2_500_000),
    "606":  ("Eau, électricité, fournitures",        1_847_350),
    "613":  ("Locations",                            5_400_000),
    "622":  ("Honoraires et intermédiaires",           948_275),
    "624":  ("Transports de biens",                  3_214_680),
    "641":  ("Rémunérations du personnel",          22_800_000),
    "645":  ("Charges de sécurité sociale",          4_560_000),
    "661":  ("Charges d'intérêts",                   1_430_500),
    "681":  ("Dotations aux amortissements",         2_600_000),
    "695":  ("Impôt sur les bénéfices",              1_900_000),
    "701":  ("Ventes de marchandises",            -152_000_000),
    "706":  ("Prestations de services (livraison)",  -6_500_000),
}

RESULTAT_2024 = -sum(v for _, v in GESTION_2024.values())  # bénéfice si positif
assert RESULTAT_2024 > 0, "Le résultat 2024 doit être bénéficiaire pour ce scénario."

# Report à nouveau 2024 (avant affectation) : force l'équilibre global de la balance N-1
_som_bilan_sans_110 = sum(v for _, v in BILAN_2024.values() if v is not None)
REPORT_2024 = -(_som_bilan_sans_110 + sum(v for _, v in GESTION_2024.values()))
BILAN_2024["110"] = ("Report à nouveau", REPORT_2024)

# À-nouveaux 2025 : bilan 2024 avec le résultat 2024 affecté au report à nouveau
AN_2025 = {k: (lib, v) for k, (lib, v) in BILAN_2024.items()}
AN_2025["110"] = ("Report à nouveau", REPORT_2024 - RESULTAT_2024)

_an_lignes = []
for compte, (lib, solde) in sorted(AN_2025.items()):
    if solde >= 0:
        _an_lignes.append((compte, f"À nouveau — {lib}", solde, 0))
    else:
        _an_lignes.append((compte, f"À nouveau — {lib}", 0, -solde))
ecrire("2025-01-01", piece(), _an_lignes)

# ─── Activité 2025 ───────────────────────────────────────────────────────────
# Ventes à crédit (factures) : (date, montant). Peu de lignes jan→nov,
# concentration volontaire sur les 15 derniers jours de décembre (A4).
VENTES_CREDIT = [
    ("2025-01-16", 6_845_250), ("2025-01-28", 5_230_480),
    ("2025-02-12", 2_447_350),   # A6 : restera impayée au 31/12
    ("2025-02-20", 7_118_320),
    ("2025-03-11", 6_530_240), ("2025-03-27", 7_842_615),
    ("2025-04-15", 6_920_430), ("2025-04-29", 7_455_280),
    ("2025-05-14", 7_236_140), ("2025-05-28", 8_012_375),
    ("2025-06-10", 7_648_220), ("2025-06-25", 8_237_490),
    ("2025-07-15", 7_925_360), ("2025-07-30", 8_418_245),
    ("2025-08-13", 8_146_530), ("2025-08-27", 8_659_410),
    ("2025-09-10", 8_324_275), ("2025-09-24", 8_871_620),
    ("2025-10-15", 8_562_340), ("2025-10-29", 9_148_255),
    ("2025-11-12", 8_795_430), ("2025-11-26", 9_386_215),
    ("2025-12-05", 6_218_340), ("2025-12-10", 5_442_180),
    # Fenêtre cut-off (17-31/12) : 12 factures sur 36 lignes 70x
    ("2025-12-18", 1_284_150), ("2025-12-19", 1_147_325),
    ("2025-12-22", 1_318_240), ("2025-12-23", 1_164_380),
    ("2025-12-26", 1_292_465), ("2025-12-27", 1_171_240),
    ("2025-12-29", 1_346_180), ("2025-12-29", 1_158_430),
    ("2025-12-30", 1_314_260), ("2025-12-30", 1_189_375),
    ("2025-12-31", 1_357_120), ("2025-12-31", 1_212_385),
]
for date, montant in VENTES_CREDIT:
    ecrire(date, piece(), [
        ("411", "Facture client négoce matériaux", montant, 0),
        ("701", "Vente de marchandises", 0, montant),
    ])

# Prestations de livraison facturées (706), une par trimestre
for date, montant in [("2025-03-31", 1_684_250), ("2025-06-30", 1_792_430),
                      ("2025-09-30", 1_845_270), ("2025-12-15", 1_923_450)]:
    ecrire(date, piece(), [
        ("411", "Facture prestation livraison chantier", montant, 0),
        ("706", "Prestation de livraison", 0, montant),
    ])

# Ventes comptant en caisse (mensuelles) puis remises en banque
CAISSE_VENTES = [
    ("2025-01-31", 412_350), ("2025-02-28", 386_240), ("2025-03-31", 428_615),
    ("2025-04-30", 395_480), ("2025-05-30", 441_270), ("2025-06-30", 407_935),
    ("2025-07-31", 452_340), ("2025-08-29", 418_265), ("2025-09-30", 463_180),
    ("2025-10-31", 429_450), ("2025-11-28", 474_325), ("2025-12-31", 512_240),
]
for date, montant in CAISSE_VENTES:
    ecrire(date, piece(), [
        ("531", "Ventes comptant du mois", montant, 0),
        ("701", "Ventes de marchandises au comptant", 0, montant),
    ])

REMISES = [
    ("2025-02-03", 400_000), ("2025-03-03", 380_000), ("2025-04-02", 420_000),
    ("2025-05-05", 390_000), ("2025-06-03", 430_000), ("2025-07-02", 400_000),
    ("2025-08-04", 450_000), ("2025-09-02", 410_000), ("2025-10-02", 460_000),
    ("2025-11-03", 420_000), ("2025-12-02", 470_000),
]
for date, montant in REMISES:
    ecrire(date, piece(), [
        ("512", "Remise en banque espèces", montant, 0),
        ("531", "Remise en banque espèces", 0, montant),
    ])

# Encaissements clients par virement : soldent les à-nouveaux puis les factures,
# SAUF la facture A6 du 12/02 et les factures de la fenêtre de cut-off.
ENCAISSEMENTS = [
    ("2025-01-20", 11_500_000, "Virements clients — solde exercice 2024"),
    ("2025-02-17", 10_500_000, "Virements clients — solde exercice 2024"),
    ("2025-02-25",  6_845_250, "Règlement facture janvier"),
    ("2025-03-18",  5_230_480, "Règlement facture janvier"),
    ("2025-03-28",  7_118_320, "Règlement facture février"),
    ("2025-04-22",  6_530_240, "Règlement facture mars"),
    ("2025-05-06",  7_842_615, "Règlement facture mars"),
    ("2025-05-26",  6_920_430, "Règlement facture avril"),
    ("2025-06-09",  7_455_280, "Règlement facture avril"),
    ("2025-06-24",  7_236_140, "Règlement facture mai"),
    ("2025-07-08",  8_012_375, "Règlement facture mai"),
    ("2025-07-22",  7_648_220, "Règlement facture juin"),
    ("2025-08-05",  8_237_490, "Règlement facture juin"),
    ("2025-08-19",  7_925_360, "Règlement facture juillet"),
    ("2025-09-04",  8_418_245, "Règlement facture juillet"),
    ("2025-09-18",  8_146_530, "Règlement facture août"),
    ("2025-10-06",  8_659_410, "Règlement facture août"),
    ("2025-10-20",  8_324_275, "Règlement facture septembre"),
    ("2025-11-05",  8_871_620, "Règlement facture septembre"),
    ("2025-11-19",  8_562_340, "Règlement facture octobre"),
    ("2025-12-04",  9_148_255, "Règlement facture octobre"),
    ("2025-12-16",  8_795_430, "Règlement facture novembre"),
    ("2025-12-23",  9_386_215, "Règlement facture novembre"),
    ("2025-12-29",  1_684_250, "Règlement prestation T1"),
    ("2025-12-30",  1_792_430, "Règlement prestation T2"),
]
for date, montant, lib in ENCAISSEMENTS:
    ecrire(date, piece(), [
        ("512", lib, montant, 0),
        ("411", lib, 0, montant),
    ])

# Achats de marchandises à crédit (fournisseurs locaux et import)
ACHATS = [
    ("2025-01-09", 4_618_340), ("2025-01-23", 4_927_255),
    ("2025-02-06", 4_753_180), ("2025-02-19", 5_112_430),
    ("2025-03-06", 4_986_215), ("2025-03-20", 5_248_370),
    ("2025-04-09", 5_134_260), ("2025-04-24", 5_396_480),
    ("2025-05-08", 5_287_325), ("2025-05-22", 5_524_190),
    ("2025-06-05", 5_412_275), ("2025-06-19", 5_683_420),
    ("2025-07-10", 5_578_310), ("2025-07-24", 5_812_245),
    ("2025-08-07", 5_694_380), ("2025-08-21", 5_927_150),
    ("2025-09-04", 5_836_425), ("2025-09-18", 6_048_310),
    ("2025-10-09", 5_952_270), ("2025-10-23", 6_187_435),
    ("2025-11-06", 6_074_320), ("2025-11-20", 6_298_255),
    ("2025-12-04", 6_183_470), ("2025-12-18", 6_412_385),
]
for date, montant in ACHATS:
    ecrire(date, piece(), [
        ("601", "Facture fournisseur marchandises", montant, 0),
        ("401", "Facture fournisseur marchandises", 0, montant),
    ])

# A2 : facture fournisseur ETS OMAR & FRÈRES saisie DEUX FOIS avec la même pièce
_p_doublon = piece()
for date in ("2025-08-14", "2025-09-11"):
    ecrire(date, _p_doublon, [
        ("601", "Facture ETS OMAR & FRÈRES n°OF-2025-118", 2_340_000, 0),
        ("401", "Facture ETS OMAR & FRÈRES n°OF-2025-118", 0, 2_340_000),
    ])

# Règlements fournisseurs par virement/chèque
PAIEMENTS_FOURN = [
    ("2025-01-27", 9_300_000, "Virement fournisseurs — solde 2024"),
    ("2025-02-24", 5_000_000, "Virement fournisseurs — solde 2024"),
    ("2025-03-13", 4_618_340, "Règlement facture janvier"),
    ("2025-03-27", 4_927_255, "Règlement facture janvier"),
    ("2025-04-14", 4_753_180, "Règlement facture février"),
    ("2025-04-28", 5_112_430, "Règlement facture février"),
    ("2025-05-13", 4_986_215, "Règlement facture mars"),
    ("2025-05-27", 5_248_370, "Règlement facture mars"),
    ("2025-06-12", 5_134_260, "Règlement facture avril"),
    ("2025-06-26", 5_396_480, "Règlement facture avril"),
    ("2025-07-14", 5_287_325, "Règlement facture mai"),
    ("2025-07-28", 5_524_190, "Règlement facture mai"),
    ("2025-08-12", 5_412_275, "Règlement facture juin"),
    ("2025-08-26", 5_683_420, "Règlement facture juin"),
    ("2025-09-11", 5_578_310, "Règlement facture juillet"),
    ("2025-09-25", 5_812_245, "Règlement facture juillet"),
    ("2025-10-13", 5_694_380, "Règlement facture août"),
    ("2025-10-27", 5_927_150, "Règlement facture août"),
    ("2025-11-12", 5_836_425, "Règlement facture septembre"),
    ("2025-11-26", 6_048_310, "Règlement facture septembre"),
    ("2025-12-11", 5_952_270, "Règlement facture octobre"),
    ("2025-12-22", 6_187_435, "Règlement facture octobre"),
]
for date, montant, lib in PAIEMENTS_FOURN:
    ecrire(date, piece(), [
        ("401", lib, montant, 0),
        ("512", lib, 0, montant),
    ])

# A1 : chèque émis le 30/12 (fournisseur), NON débité au relevé bancaire
PIECE_CHEQUE_A1 = piece()
ecrire("2025-12-30", PIECE_CHEQUE_A1, [
    ("401", f"Chèque n°{PIECE_CHEQUE_A1} — ETS DARYEEL BTP", 850_000, 0),
    ("512", f"Chèque n°{PIECE_CHEQUE_A1} — ETS DARYEEL BTP", 0, 850_000),
])

# Paie mensuelle : salaires constants, cotisations CNSS 20 % (ratio normal)
MOIS_FIN = ["2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30", "2025-05-30",
            "2025-06-30", "2025-07-31", "2025-08-29", "2025-09-30", "2025-10-31",
            "2025-11-28", "2025-12-31"]
SALAIRE_MENSUEL, CNSS_MENSUEL = 2_050_000, 410_000
for fin in MOIS_FIN:
    ecrire(fin, piece(), [
        ("641", "Salaires du mois", SALAIRE_MENSUEL, 0),
        ("421", "Salaires du mois", 0, SALAIRE_MENSUEL),
    ])
    ecrire(fin, piece(), [
        ("645", "Cotisations CNSS du mois", CNSS_MENSUEL, 0),
        ("431", "Cotisations CNSS du mois", 0, CNSS_MENSUEL),
    ])
# Paiement le 5 du mois suivant (déc. 2024 payé en janv. 2025 ; déc. 2025 reste dû)
PAIE_DATES = ["2025-01-06", "2025-02-05", "2025-03-05", "2025-04-07", "2025-05-05",
              "2025-06-05", "2025-07-07", "2025-08-05", "2025-09-05", "2025-10-06",
              "2025-11-05", "2025-12-05"]
for i, d in enumerate(PAIE_DATES):
    sal = 1_900_000 if i == 0 else SALAIRE_MENSUEL   # janvier : solde 421 de 2024
    cns = 950_000 if i == 0 else CNSS_MENSUEL        # janvier : solde 431 de 2024
    ecrire(d, piece(), [
        ("421", "Virement salaires", sal, 0),
        ("512", "Virement salaires", 0, sal),
    ])
    ecrire(d, piece(), [
        ("431", "Paiement cotisations CNSS", cns, 0),
        ("512", "Paiement cotisations CNSS", 0, cns),
    ])

# Loyer de l'entrepôt (rond — réaliste) et charges externes variées
for i, fin in enumerate(MOIS_FIN):
    d = fin[:8] + "05"
    ecrire(d, piece(), [
        ("613", "Loyer entrepôt Boulaos", 500_000, 0),
        ("512", "Loyer entrepôt Boulaos", 0, 500_000),
    ])
ELEC = [318_425, 294_310, 331_240, 305_185, 342_370, 328_415,
        356_240, 349_180, 337_425, 322_310, 314_270, 361_435]
for fin, m in zip(MOIS_FIN, ELEC):
    ecrire(fin, piece(), [
        ("606", "Facture EDD électricité", m, 0),
        ("512", "Facture EDD électricité", 0, m),
    ])
TRANSPORT = [512_340, 498_215, 534_180, 521_425, 547_310, 539_240,
             561_385, 553_270, 544_425, 568_310, 572_245, 589_430]
for fin, m in zip(MOIS_FIN, TRANSPORT):
    ecrire(fin, piece(), [
        ("624", "Transport et manutention port", m, 0),
        ("512", "Transport et manutention port", 0, m),
    ])
# Honoraires expert-comptable (novembre)
ecrire("2025-11-17", piece(), [
    ("622", "Honoraires cabinet comptable", 975_340, 0),
    ("512", "Honoraires cabinet comptable", 0, 975_340),
])

# Emprunt BCIMR : échéances trimestrielles (capital 1 500 000 + intérêts dégressifs)
for d, interet in [("2025-03-31", 427_500), ("2025-06-30", 391_250),
                   ("2025-09-30", 355_425), ("2025-12-19", 319_180)]:
    ecrire(d, piece(), [
        ("164", "Échéance emprunt BCIMR — capital", 1_500_000, 0),
        ("661", "Échéance emprunt BCIMR — intérêts", interet, 0),
        ("512", "Échéance emprunt BCIMR", 0, 1_819_180 if d == "2025-12-19" else 1_500_000 + interet),
    ])

# Acquisition mobilier/rayonnages (juin) — reste sans amortissement (A5)
ecrire("2025-06-16", piece(), [
    ("218", "Rayonnages entrepôt + mobilier bureau", 3_500_000, 0),
    ("512", "Rayonnages entrepôt + mobilier bureau", 0, 3_500_000),
])

# Règlement IS 2024 (avril)
ecrire("2025-04-15", piece(), [
    ("444", "Règlement IS exercice 2024", 1_900_000, 0),
    ("512", "Règlement IS exercice 2024", 0, 1_900_000),
])

# Menues dépenses de caisse (fournitures)
for d, m in [("2025-03-14", 87_425), ("2025-06-12", 92_310),
             ("2025-09-15", 78_240), ("2025-12-12", 96_415)]:
    ecrire(d, piece(), [
        ("606", "Petites fournitures payées en espèces", m, 0),
        ("531", "Petites fournitures payées en espèces", 0, m),
    ])

# ─── Écritures d'inventaire du 31/12/2025 ────────────────────────────────────
# Stock final 34 450 000 (ouverture 25 000 000) → variation créditrice 9 450 000
ecrire("2025-12-31", piece(), [
    ("310", "Variation de stock — inventaire au 31/12", 9_450_000, 0),
    ("6031", "Variation de stock — inventaire au 31/12", 0, 9_450_000),
])
# Dotation amortissement matériel de transport (rien sur 218 → A5)
ecrire("2025-12-31", piece(), [
    ("681", "Dotation amortissement matériel transport", 2_912_425, 0),
    ("2815", "Dotation amortissement matériel transport", 0, 2_912_425),
])
# IS estimé 2025 (payable 2026)
ecrire("2025-12-31", piece(), [
    ("695", "Impôt sur les bénéfices — exercice 2025", 2_384_150, 0),
    ("444", "Impôt sur les bénéfices — exercice 2025", 0, 2_384_150),
])
# Dernier mouvement bancaire de l'exercice : encaissement de la prestation T3
ecrire("2025-12-31", piece(), [
    ("512", "Règlement prestation T3", 1_845_270, 0),
    ("411", "Règlement prestation T3", 0, 1_845_270),
])

# ─── Sorties fichiers ────────────────────────────────────────────────────────
LIBELLES_COMPTES = {**{k: lib for k, (lib, _) in BILAN_2024.items()},
                    **{k: lib for k, (lib, _) in GESTION_2024.items()}}

# Grand livre trié par date puis pièce
GL.sort(key=lambda r: (r["date"], int(r["numero_piece"])))
with open(OUT / "grand_livre_2025.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["compte", "libelle", "date", "numero_piece", "debit", "credit"])
    w.writeheader()
    w.writerows(GL)

# Balance 2025 dérivée du grand livre (cohérence GL/balance garantie)
soldes: dict[str, int] = {}
for r in GL:
    soldes[r["compte"]] = soldes.get(r["compte"], 0) + r["debit"] - r["credit"]
assert sum(soldes.values()) == 0, "La balance 2025 doit être équilibrée."
with open(OUT / "balance_2025.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["compte", "libelle", "debit", "credit", "exercice"])
    for compte in sorted(soldes):
        s = soldes[compte]
        lib = LIBELLES_COMPTES.get(compte, compte)
        w.writerow([compte, lib, s if s > 0 else 0, -s if s < 0 else 0, 2025])

# Balance 2024 (bilan avant affectation + comptes de gestion)
b24 = {**{k: v for k, (_, v) in BILAN_2024.items()},
       **{k: v for k, (_, v) in GESTION_2024.items()}}
assert sum(b24.values()) == 0, "La balance 2024 doit être équilibrée."
with open(OUT / "balance_2024.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["compte", "libelle", "debit", "credit", "exercice"])
    for compte in sorted(b24):
        s = b24[compte]
        w.writerow([compte, LIBELLES_COMPTES[compte], s if s > 0 else 0, -s if s < 0 else 0, 2024])

# Relevé bancaire BCIMR 2025 : miroir des mouvements 512 SAUF le chèque A1,
# PLUS frais de tenue de compte du 31/12 non comptabilisés (A1).
mvts_512 = [r for r in GL if r["compte"] == "512" and r["date"] != "2025-01-01"]
solde = AN_2025["512"][1]
releve = [{"date": "2025-01-01", "libelle": "Solde d'ouverture",
           "debit": 0, "credit": 0, "solde": solde}]
for r in mvts_512:
    if r["numero_piece"] == PIECE_CHEQUE_A1:
        continue  # A1 : chèque en circulation, non débité par la banque
    # Convention relevé côté banque tenue en perspective entreprise :
    # crédit du relevé = entrée de fonds (débit 512 au GL)
    solde += r["debit"] - r["credit"]
    releve.append({"date": r["date"], "libelle": r["libelle"],
                   "debit": r["credit"], "credit": r["debit"], "solde": solde})
solde -= 12_500
releve.append({"date": "2025-12-31", "libelle": "Frais de tenue de compte T4",
               "debit": 12_500, "credit": 0, "solde": solde})

soldes_releve = [l["solde"] for l in releve]
assert min(soldes_releve) > 0, "Le compte bancaire ne doit jamais être à découvert."
# Le moteur extrait « le plus grand montant » du relevé comme solde : ce doit être
# le solde du 31/12 avant frais (clôture + 12 500). L'écart de rapprochement
# détecté par TRESOR-RAPPROCH sera donc de 850 000 (chèque seul) ; l'auditeur
# doit retrouver les 12 500 de frais en analysant le relevé (A1).
assert max(soldes_releve) == releve[-1]["solde"] + 12_500, \
    "Le solde 31/12 avant frais doit être le maximum du relevé."
mx_transac = max(max(l["debit"], l["credit"]) for l in releve)
assert mx_transac < releve[-1]["solde"], "Aucun mouvement ne doit dépasser le solde de clôture."
assert releve[-1]["solde"] == soldes["512"] + 850_000 - 12_500

with open(OUT / "releve_bancaire_2025.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["date", "libelle", "debit", "credit", "solde"])
    w.writeheader()
    w.writerows(releve)

# ─── Synthèse console ────────────────────────────────────────────────────────
print(f"Grand livre 2025 : {len(GL)} lignes, pièces {GL[0]['numero_piece']}–{max(int(r['numero_piece']) for r in GL)}")
print(f"Balance 2025     : {len(soldes)} comptes, CA 701+706 = {-(soldes['701'] + soldes['706']):,} FDJ")
print(f"Balance 2024     : {len(b24)} comptes, CA 2024 = {-(b24['701'] + b24['706']):,} FDJ")
print(f"Solde 512 GL     : {soldes['512']:,} | Relevé : {releve[-1]['solde']:,} | Écart attendu : {releve[-1]['solde'] - soldes['512']:,}")
print(f"Clients 411 au 31/12 : {soldes['411']:,} (dont facture A6 impayée 2 447 350)")
print(f"Résultat 2025    : {-sum(v for k, v in soldes.items() if k[0] in '67'):,} FDJ")

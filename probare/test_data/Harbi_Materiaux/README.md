# Jeu de test « HARBI MATÉRIAUX SARL » — société fictive

Dossier comptable complet construit pour le test de bout en bout de Probare
(les données publiques réelles de ce niveau de détail — grand livre + balances
N/N-1 + relevé bancaire — n'existent pas en libre accès ; ce jeu est donc
construit, cohérent en partie double, et distinct des jeux Marsa/Dalol déjà
présents dans le dépôt).

## Profil de l'entité (à saisir au cadrage / fiche entité)

| Champ | Valeur |
|---|---|
| Raison sociale | HARBI MATÉRIAUX SARL |
| Forme juridique | SARL |
| Date de création | 2014-03-18 |
| Activité | Négoce de matériaux de construction (import-revente) |
| Marchés | Local (Djibouti ville) ; approvisionnement import via le port |
| Effectif | 14 |
| Système d'information | Logiciel comptable simple + facturation Excel |
| Gérant | M. Ahmed Harbi (gérant majoritaire, 65 % des parts) |
| Banque | BCIMR (compte courant unique 512) |
| Exercice audité | 2025 (01/01 → 31/12), comparatif 2024 |
| Monnaie | FDJ (Franc Djibouti) |
| Capital social | 40 000 000 FDJ |

## Fichiers

- `grand_livre_2025.csv` — 492 lignes, à-nouveaux du 01/01 inclus, pièces 5001–5237
- `balance_2025.csv` — 29 comptes, dérivée du grand livre (cohérence GL/balance garantie)
- `balance_2024.csv` — balance N-1 équilibrée (bilan avant affectation + comptes de gestion)
- `releve_bancaire_2025.csv` — relevé BCIMR (date, libellé, débit, crédit, solde progressif)
- `Harbi_Materiaux_Dossier_Permanent.docx` — annexe : présentation de la société
- `generer_harbi.py` — générateur (rejouable, déterministe)

## Oracle : anomalies plantées et détection attendue

| # | Anomalie | Contrôle attendu | Valeur attendue |
|---|---|---|---|
| A1 | Chèque n°5138 (850 000) émis le 30/12 non débité + frais bancaires 12 500 non comptabilisés | TRESOR-RAPPROCH | Écart détecté ≈ 850 000 (le moteur extrait le solde du relevé avant frais) ; le vrai écart de rapprochement est 837 500 |
| A2 | Facture ETS OMAR & FRÈRES saisie 2 fois (pièce 5115, 2 340 000, comptes 601/401, 14/08 et 11/09) | ACHAT-DOUBLON + SEQ (doublon) | 1 doublon exact (compte+montant+pièce) |
| A3 | Numéro de pièce 5087 jamais utilisé | TRESOR/ACHAT/VENTE-SEQ | 1 trou dans la séquence |
| A4 | 12 factures de vente sur les 15 derniers jours de décembre (12/36 lignes 70x = 33 %) | VENTE-CUT-OFF | ratio ≥ 30 % |
| A5 | Compte 218 (9 900 000 brut) sans amortissement cumulé 2818 | IMO-AMORTISSEMENT | immobilisation non amortie |
| A6 | Facture client du 12/02/2025 (2 447 350) impayée au 31/12 + clients douteux 416 (1 200 000) sans dépréciation | VENTE-CREANCES-ECHUES | créance > 90 jours |
| A7 | Variations N/N-1 : CA +30,5 %, clients +40,8 %, stocks +37,8 %, marge nette 4,6 % → 11,3 % | *-VARIATION + procédures analytiques (NEP 520) | variations > seuil |

Contrôles qui doivent ressortir SANS exception (contre-épreuve) :
équilibre des balances (TRESOR-BAL-EQUIL), cohérence GL/balance (tous cycles,
par construction), ratio CNSS/salaires 20 % (PAIE-RATIO-SOCIAL), montants
ronds (minoritaires), soldes anormaux (aucun compte à l'envers).

Particularité assumée : le grand livre est en **partie double réelle** — chaque
pièce apparaît sur ses 2 lignes (débit/crédit). C'est le format d'un vrai
export comptable (type FEC) et cela met à l'épreuve les contrôles de séquence,
qui considèrent chaque numéro répété comme un doublon.

## Chiffres clés

| Agrégat | 2025 | 2024 |
|---|---|---|
| Chiffre d'affaires (701+706) | 206 845 030 | 158 500 000 |
| Clients (411) | 30 986 870 | 22 000 000 |
| Stocks (310) | 34 450 000 | 25 000 000 |
| Banque (512) | 32 714 930 | 20 000 000 |
| Résultat net | 23 384 095 | 7 310 000 |

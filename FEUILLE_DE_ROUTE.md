# Feuille de route — Probare

Diagnostic du 2026-06-24 · Référentiel : cahier des charges contractuel + légal

---

## Légende

| Statut | Signification |
|---|---|
| LIVRÉ | Fonctionnel en production |
| EN COURS | Implémenté partiellement |
| PLANIFIÉ | À implémenter |

| Priorité | Signification |
|---|---|
| P0 | Critique — bloque l'usage |
| P1 | Haute — forte valeur ajoutée |
| P2 | Moyenne — améliore le confort |
| P3 | Basse — confort / cosmétique |

---

## Piste 1 — Agrégation des anomalies & formation d'opinion (ANO-03/04 + OPI-01/02)

**Priorité : P1 | Complexité : Moyenne | Statut : PLANIFIÉ**

### Problème
Les exceptions sont tranchées individuellement mais jamais agrégées pour former une opinion globale. La phase `opinion` du pipeline est déclarée dans la machine d'état mais n'a aucun support fonctionnel (pas de table, pas de route, pas d'UI).

### Valeur ajoutée
- Calcul Python déterministe du type d'opinion (propre / réserve / propre avec observation / refus)
- Comparaison automatique cumul anomalies / seuil de signification
- Narrative d'opinion rédigée par Sonnet (à la 1ère personne, prête à signer)
- L'auditeur valide ou modifie en un clic — conformité NEP 450 + OPI du cahier des charges

### Réalisation
- `controls/opinion.py` : `agreger_anomalies()` + `determiner_type_opinion()` (pur Python)
- Table `opinion` dans `db.py` + méthodes `save_or_update_opinion()` / `get_opinion()`
- `llm/claude.py` : méthode `generer_narrative_opinion()`
- Routes : `GET/POST/PATCH /projets/{id}/opinion/...`
- Section dédiée dans `Rapport.tsx`
- Tests : `tests/test_opinion.py`

---

## Piste 2 — Cycle Immobilisations (IAS 16 / PCG 200) (IMM-01 à IMM-07)

**Priorité : P1 | Complexité : Moyenne | Statut : PLANIFIÉ**

### Problème
Le registre déclare 7 contrôles pour les immobilisations mais aucun n'est implémenté dans le moteur Python. Le cycle est sélectionnable dans le cadrage mais les contrôles renvoient une erreur.

### Valeur ajoutée
Couvre un cycle majeur de l'audit légal : amortissements, cessions, tests de dépréciation, cohérence avec la liasse fiscale.

### Réalisation
- `controls/immobilisations.py` : 7 contrôles déterministes
- Tests unitaires avec données équilibrées et déséquilibrées
- Intégration dans le registre `controls/registry.py`

---

## Piste 3 — Cycle Stocks (PCG 3xx / IAS 2) (STK-01 à STK-06)

**Priorité : P1 | Complexité : Moyenne | Statut : PLANIFIÉ**

### Problème
Même situation que les immobilisations : 6 contrôles stocks déclarés, non implémentés.

### Valeur ajoutée
Valorisation des stocks, test de dépréciation, cohérence inventaire, rotation des stocks.

### Réalisation
- `controls/stocks.py` : 6 contrôles déterministes
- Tests unitaires
- Intégration dans le registre

---

## Piste 4 — Circularisation — suivi des relances (CIR-04/05)

**Priorité : P2 | Complexité : Faible | Statut : EN COURS**

### Problème
La circularisation (NEP 505) est implémentée mais le suivi des relances est incomplet : pas de tableau de bord des taux de réponse, pas d'alerte automatique pour les non-réponses en retard, pas d'export des lettres en .docx.

### Valeur ajoutée
Pilotage du taux de couverture de circularisation, relances automatisées, conformité NEP 505.

### Réalisation
- Colonne `date_relance` déjà migrée en DB
- Ajouter : alerte automatique si `date_envoi` > 30 jours sans réponse
- Export groupé des lettres de circularisation en .docx
- Tableau de synthèse : taux de réponse par cycle

---

## Piste 5 — Interface Sondages / Échantillonnage (ECH-01 à ECH-04)

**Priorité : P1 | Complexité : Faible (UI seulement) | Statut : PLANIFIÉ**

### Problème
Le backend sondages (NEP 530) est entièrement implémenté (routes, DB, calculs Python : formule Neyman, projection d'erreur). Il n'existe aucune interface utilisateur pour y accéder.

### Valeur ajoutée
Accès complet à l'échantillonnage statistique depuis l'UI : création, sélection, marquage des anomalies, projection, conclusion IA.

### Réalisation
- Fix seed non-déterministe dans `routes.py` (hashlib.sha256)
- `pages/Sondages.tsx` : page complète
- Route `/projet/:projetId/sondages` dans `App.tsx`
- Lien sidebar dans `Sidebar.tsx`

---

## Piste 6 — Export PDF (EXP-03)

**Priorité : P2 | Complexité : Faible | Statut : PLANIFIÉ**

### Problème
L'export du dossier de travail est disponible uniquement en .docx. Le cahier des charges prévoit également un export PDF (EXP-03 — SHOULD). Les clients et régulateurs exigent souvent du PDF pour l'archivage.

### Valeur ajoutée
Dossier de travail en PDF signable électroniquement, compatible avec les GED (archivage légal).

### Réalisation
- Dépendance `fpdf2>=2.7.0` dans `pyproject.toml`
- `reporting/pdf_export.py` : génération PDF (même structure que le .docx)
- Route `GET /projets/{id}/exporter-dossier-pdf`
- Bouton "Rapport d'audit (PDF)" dans `Rapport.tsx`

---

## Piste 7 — Badges visuels calculé/IA (TRA-05)

**Priorité : P2 | Complexité : Très faible | Statut : PLANIFIÉ**

### Problème
L'interface ne distingue pas visuellement l'origine des données affichées (calculé par Python / proposé par IA / validé par l'auditeur / importé). Cette traçabilité est une exigence du cahier des charges (TRA-05 — MUST).

### Valeur ajoutée
Conformité TRA-05. L'auditeur voit immédiatement ce qui est un fait (calcul Python) vs une proposition (IA) vs une décision (saisie auditeur).

### Réalisation
- `components/ui/OriginBadge.tsx` : composant badge compact (4 variantes)
- Application dans `Controles.tsx`, `Exceptions.tsx`, `Rapport.tsx`

---

## Piste 8 — Dashboard analytique de mission (DASH-01 à DASH-04)

**Priorité : P2 | Complexité : Faible | Statut : PLANIFIÉ**

### Problème
Le tableau de bord actuel liste les projets mais n'offre pas de vue analytique sur l'avancement d'une mission ouverte : taux de couverture des contrôles, ratio exceptions tranchées/ouvertes, progression par cycle, alertes de deadline.

### Valeur ajoutée
Vision d'ensemble pour le chef de mission : KPIs temps réel, identification des cycles en retard, alerte sur exceptions critiques non tranchées.

### Réalisation
- Nouvelle section "Vue mission" sur la page `Dashboard.tsx` ou `Controles.tsx`
- KPIs calculés Python : taux couverture, ratio exceptions, nb contrôles ok/ko par cycle
- Jauge de progression de la mission (pipeline)
- Alerte visuelle si exceptions critiques > 0 depuis > 7 jours

---

## Synthèse

| Piste | Thème | Priorité | Complexité | Statut |
|---|---|---|---|---|
| 1 | Agrégation anomalies + opinion | P1 | Moyenne | PLANIFIÉ |
| 2 | Cycle Immobilisations | P1 | Moyenne | PLANIFIÉ |
| 3 | Cycle Stocks | P1 | Moyenne | PLANIFIÉ |
| 4 | Circularisation — relances | P2 | Faible | EN COURS |
| 5 | Interface Sondages | P1 | Faible | PLANIFIÉ |
| 6 | Export PDF | P2 | Faible | PLANIFIÉ |
| 7 | Badges visuels calculé/IA | P2 | Très faible | PLANIFIÉ |
| 8 | Dashboard analytique | P2 | Faible | PLANIFIÉ |

**Sprint 1 (en cours)** : Pistes 1, 5, 6, 7

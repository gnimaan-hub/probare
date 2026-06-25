# Guide d'utilisation complet de Probare

## Logiciel d'audit comptable assisté par IA

---

## Table des matières

1. [Présentation générale](#1-présentation-générale)
2. [Philosophie et principes fondamentaux](#2-philosophie-et-principes-fondamentaux)
3. [Installation et configuration initiale](#3-installation-et-configuration-initiale)
4. [Vue d'ensemble de l'interface](#4-vue-densemble-de-linterface)
5. [Cycle de vie d'un projet d'audit](#5-cycle-de-vie-dun-projet-daudit)
6. [Phase 1 — Cadrage](#6-phase-1--cadrage)
7. [Phase 2 — Ingestion des fichiers](#7-phase-2--ingestion-des-fichiers)
8. [Phase 3 — Contrôles d'audit](#8-phase-3--contrôles-daudit)
9. [Phase 4 — Questionnaire de contrôle interne (QCI)](#9-phase-4--questionnaire-de-contrôle-interne-qci)
10. [Phase 5 — Revue des exceptions](#10-phase-5--revue-des-exceptions)
11. [Phase 6 — Génération des documents](#11-phase-6--génération-des-documents)
12. [Phase 7 — Opinion](#12-phase-7--opinion)
13. [Les 52 règles de contrôle par cycle](#13-les-52-règles-de-contrôle-par-cycle)
14. [Traçabilité et provenance des données](#14-traçabilité-et-provenance-des-données)
15. [Fonctionnalités IA — Ce que fait Claude](#15-fonctionnalités-ia--ce-que-fait-claude)
16. [Sécurité et anonymisation](#16-sécurité-et-anonymisation)
17. [Journal d'audit (piste d'audit)](#17-journal-daudit-piste-daudit)
18. [Export et rapports](#18-export-et-rapports)
19. [Référence technique](#19-référence-technique)
20. [Questions fréquentes](#20-questions-fréquentes)

---

## 1. Présentation générale

**Probare** est un logiciel d'audit comptable de bureau (application desktop) conçu pour les cabinets d'audit et les professionnels de la conformité financière. Il modernise le processus d'audit en automatisant les calculs répétitifs tout en gardant l'auditeur humain au centre de chaque décision significative.

### À qui s'adresse Probare ?

- Auditeurs légaux et contractuels
- Experts-comptables réalisant des missions de commissariat aux comptes
- Collaborateurs de cabinets d'audit chargés d'exécuter les diligences
- Responsables qualité vérifiant la conformité des dossiers d'audit

### Ce que Probare fait concrètement

- **Importe** les fichiers comptables du client (grand livre, balance, relevés bancaires) au format Excel ou CSV
- **Exécute automatiquement** 52 règles de contrôle réparties sur 8 cycles d'audit
- **Signale** les anomalies (exceptions) et propose une interprétation assistée par IA
- **Évalue** l'environnement de contrôle interne du client via un questionnaire structuré
- **Génère** les dossiers de travail, rapports d'audit et tableaux d'anomalies au format Word et Excel
- **Conserve** une piste d'audit complète de chaque action, calcul et appel à l'IA

### Cadre normatif

Probare est conçu dans le respect des **NEP (Normes d'Exercice Professionnel)** françaises, applicables aux missions d'audit menées sous l'autorité **H2A** à Djibouti. Chaque règle de contrôle référence la NEP applicable.

---

## 2. Philosophie et principes fondamentaux

La conception de Probare repose sur un principe central et non négociable :

> **Calcul = Python | Interprétation = IA | Supervision = Humain**

### Ce que cela signifie en pratique

| Tâche | Qui la fait | Pourquoi |
|-------|------------|----------|
| Additionner, comparer, calculer des ratios | Python (déterministe) | Reproductible, vérifiable, auditab |
| Expliquer une anomalie, rédiger un rapport | IA Claude (interprétatif) | Gain de temps, cohérence du langage |
| Décider du sort d'une exception, signer l'opinion | L'auditeur humain | Responsabilité professionnelle |

### Pourquoi l'IA ne calcule jamais

Dans un dossier d'audit, chaque chiffre doit être traçable jusqu'à sa source. Un modèle de langage (LLM) peut produire des résultats légèrement différents d'une exécution à l'autre (non-déterminisme). Pour cette raison, **Probare interdit formellement à l'IA de produire des chiffres qui entrent dans le dossier d'audit**. L'IA intervient uniquement pour :

- Comprendre et classifier les documents importés
- Expliquer pourquoi une règle a signalé une anomalie
- Rédiger les synthèses et rapports en français professionnel
- Évaluer le questionnaire de contrôle interne

### La règle de provenance

Chaque valeur numérique dans Probare est associée à une `DonneeSourcee` — un objet qui mémorise :
- Le fichier source exact (grand livre, balance, etc.)
- La cellule ou la ligne exacte dans ce fichier
- La méthode d'extraction (import direct, assistance IA, calcul)
- L'horodatage de l'extraction
- Un niveau de confiance (1,0 pour les imports directs)

Si un rapport tente d'inclure un chiffre sans provenance traçable, **Probare refuse de le générer**. C'est une garantie de qualité inscrite dans le code.

---

## 3. Installation et configuration initiale

### Prérequis

| Composant | Version minimale | Rôle |
|-----------|-----------------|------|
| Python | 3.10+ | Moteur de calcul (backend) |
| Node.js | 18+ | Interface utilisateur (frontend) |
| npm | Inclus avec Node.js | Gestion des dépendances JS |
| Clé API Anthropic | — | Accès aux fonctions IA (Claude) |

### Étape 1 — Cloner le projet

```bash
git clone <url-du-dépôt> probare
cd probare
```

### Étape 2 — Créer le fichier de configuration

Dans le dossier racine `/probare/`, créez un fichier `.env` :

```bash
# Obligatoire : clé d'accès à l'API Claude
ANTHROPIC_API_KEY=sk-ant-votre-cle-ici

# Optionnel : répertoire de stockage des projets (par défaut : ~/.probare/projets)
PROBARE_DATA_DIR=/chemin/vers/vos/projets

# Optionnel : port du serveur Python (par défaut : 5000)
UVICORN_PORT=5000
```

> **Important :** Ce fichier `.env` ne doit jamais être versionné (il est déjà dans `.gitignore`). Ne partagez jamais votre clé API.

### Étape 3 — Installer le moteur Python

```bash
cd probare/apps/engine
pip install -e ".[dev]"
```

### Étape 4 — Installer les dépendances frontend

```bash
cd probare/apps/desktop
npm install
```

### Lancement en mode développement

**Terminal 1 — Démarrer le backend Python :**

```bash
cd probare/apps/engine
python -m uvicorn probare_engine.main:app --host 127.0.0.1 --port 5000 --reload
```

Une fois démarré, l'interface de documentation interactive est disponible à l'adresse `http://127.0.0.1:5000/docs`.

**Terminal 2 — Démarrer l'interface Electron :**

```bash
cd probare/apps/desktop
npm run dev
```

La fenêtre de l'application s'ouvre automatiquement.

### Lancer les tests

```bash
cd probare/apps/engine
pytest tests/ -v
```

Les tests sont 100 % déterministes et ne nécessitent pas de clé API.

---

## 4. Vue d'ensemble de l'interface

Probare est une application desktop (Electron) avec une interface React. Elle se compose de **14 pages** accessibles depuis la barre de navigation latérale.

### Navigation principale

| Page | Rôle |
|------|------|
| **Accueil** | Tableau de bord — liste des projets, création d'un nouveau projet |
| **Cadrage** | Configuration du périmètre de la mission |
| **Ingestion** | Import des fichiers comptables |
| **Documents requis** | Checklist des documents nécessaires par cycle |
| **Contrôles** | Lancement et visualisation des résultats des règles |
| **QCI** | Questionnaire de contrôle interne |
| **Exceptions** | Revue et traitement des anomalies détectées |
| **Annexes** | Gestion des pièces justificatives |
| **Circularisation** | Procédures de confirmation externe |
| **Sondages** | Échantillonnage statistique |
| **Rapport** | Génération des documents de sortie |
| **Journal** | Piste d'audit complète |
| **Paramètres** | Configuration de l'application |

### Barre de statut du projet

En haut de chaque page, une barre indique l'état actuel du projet dans le pipeline :

```
Cadrage → Ingestion → Extraction → Contrôles → Revue → Génération → Opinion
```

Chaque étape se déverrouille automatiquement quand les prérequis de l'étape précédente sont remplis.

---

## 5. Cycle de vie d'un projet d'audit

Un projet Probare suit un **pipeline linéaire à 7 états**. Il n'est pas possible de sauter une étape, et certaines transitions ne sont possibles que lorsque des conditions précises sont remplies.

```
cadrage
   ↓ (client configuré + consent obtenu)
ingestion
   ↓ (fichiers importés)
extraction
   ↓ (données extraites)
controles
   ↓ (contrôles exécutés)
revue
   ↓ (toutes les exceptions tranchées)
generation
   ↓ (documents générés)
opinion
```

### Conditions de transition

| De → À | Condition requise |
|--------|-------------------|
| cadrage → ingestion | Client configuré, consentement client accordé |
| ingestion → extraction | Au moins un fichier importé |
| extraction → controles | Données extraites avec succès |
| controles → revue | Au moins un cycle de contrôles exécuté |
| revue → generation | Toutes les exceptions ont un statut "tranchée" |
| generation → opinion | Documents générés |

---

## 6. Phase 1 — Cadrage

Le cadrage est la première étape de chaque mission. C'est ici que vous définissez le périmètre et les paramètres de l'audit.

### Créer un nouveau projet

Depuis l'accueil, cliquez sur **"Nouveau projet"**. Remplissez les informations :

| Champ | Description | Exemple |
|-------|-------------|---------|
| Nom du projet | Nom interne du dossier | "Audit MARSA 2025" |
| Client | Raison sociale du client | "Société Marsa" |
| NIF | Numéro d'identification fiscale | "DJ123456" |
| Exercice | Année ou période auditée | "2025" |
| Nature de la mission | Type d'engagement | Contractuelle / Légale |

### Sélectionner les cycles d'audit

Cochez les cycles à couvrir dans votre mission :

- [x] Trésorerie (comptes 5xx)
- [x] Achats-Fournisseurs (comptes 40x, 60x–63x)
- [x] Ventes-Clients (comptes 41x, 70x–73x)
- [x] Immobilisations (comptes 2xx)
- [x] Stocks (comptes 3xx)
- [x] Paie-Personnel (comptes 42x, 64x)
- [x] Impôts & Taxes (comptes 44x, 63x)
- [x] Capitaux Propres (comptes 10x–15x)

Vous pouvez sélectionner uniquement les cycles pertinents pour votre mission. Les contrôles et les documents requis s'adaptent automatiquement à votre sélection.

### Définir les seuils

| Seuil | Description |
|-------|-------------|
| **Seuil de signification** | Montant au-delà duquel une anomalie est considérée comme significative |
| **Seuil de planification** | Seuil interne plus bas, utilisé pour les contrôles analytiques |

Ces seuils sont utilisés par les règles de contrôle pour filtrer les alertes pertinentes.

### Consentement client — étape obligatoire

> **Cette étape est bloquante.** Sans le consentement du client, aucune fonctionnalité IA ne sera activée.

Probare envoie des données (anonymisées) à l'API Anthropic (Claude) pour les fonctions d'interprétation et de génération. Avant cela, vous devez :

1. Obtenir l'accord explicite de votre client
2. Cocher la case **"Le client a donné son consentement à l'utilisation de l'IA"**
3. La date et l'heure du consentement sont automatiquement enregistrées dans le journal

Si le consentement n'est pas accordé, Probare fonctionne entièrement en mode déterministe (calculs Python seulement, sans interprétation IA ni génération de rapports).

---

## 7. Phase 2 — Ingestion des fichiers

L'ingestion est l'import des données comptables du client dans Probare. C'est la seule étape où des données extérieures entrent dans le système.

### Formats acceptés

| Format | Extension | Notes |
|--------|-----------|-------|
| Excel moderne | `.xlsx` | Recommandé |
| Excel ancien | `.xls` | Pris en charge |
| Excel avec macros | `.xlsm` | Macros ignorées à l'import |
| CSV | `.csv` | Séparateur auto-détecté |

### Types de documents

| Type | Description | Cycles concernés |
|------|-------------|-----------------|
| **Grand livre** | Journal de toutes les écritures comptables avec date, pièce, débit, crédit | Tous |
| **Balance** | Soldes par compte à une date donnée | Tous |
| **Relevé bancaire** | Extraits de compte bancaire | Trésorerie |
| **Annexe** | Documents justificatifs, tableaux d'amortissement, etc. | Variable |

### Importer un fichier

1. Cliquez sur **"Ajouter un fichier"** ou glissez-déposez le fichier dans la zone prévue
2. Sélectionnez le type de document (Grand livre, Balance, etc.)
3. Probare analyse automatiquement le fichier et crée des `DonneeSourcee` pour chaque valeur

### Import intelligent de fichiers Excel multi-onglets

Si votre fichier Excel contient plusieurs onglets, Probare active son analyse IA :

1. L'IA (modèle Haiku) analyse chaque onglet (nom, colonnes, aperçu des données)
2. Elle identifie et classe chaque onglet (grand livre, balance, tableau d'amortissement, etc.)
3. Elle calcule un score de confiance pour chaque classification
4. L'interface affiche les recommandations d'import avec les onglets suggérés
5. Vous pouvez valider les suggestions ou modifier manuellement

**Exemple de résultat IA :**
```
Onglet "GL 2025"     → Grand livre (confiance : 0,97)  ✓ Importer
Onglet "BAL DEC"     → Balance au 31/12 (confiance : 0,94)  ✓ Importer
Onglet "Paramètres"  → Non comptable (confiance : 0,89)  ✗ Ignorer
```

### Décomposition de liasse (bundle de documents)

Si vous disposez d'un fichier regroupant plusieurs documents (liasse fiscale, dossier complet), Probare peut le décomposer automatiquement :

1. Importez le fichier bundle
2. Cliquez sur **"Décomposer la liasse"**
3. L'IA identifie les différents documents à l'intérieur
4. Elle crée autant de documents distincts que nécessaire

### Checklist des documents requis

La page **"Documents requis"** affiche la liste de tous les fichiers nécessaires en fonction des cycles sélectionnés. Chaque ligne indique :

- Le document attendu
- Le cycle qui en a besoin
- Le statut : `manquant` / `importé` / `validé`

La transition vers l'étape suivante n'est possible que si les documents critiques sont tous présents.

### Traçabilité à l'import

Pour chaque valeur importée, Probare crée une `DonneeSourcee` avec :
- L'identifiant du fichier source
- La localisation exacte (ex. : `"Balance!B5"` ou `"grand_livre.csv:ligne:42:col:Debit"`)
- La méthode d'extraction : `ingestion-directe`
- Un niveau de confiance de `1,0`
- L'horodatage de l'import

---

## 8. Phase 3 — Contrôles d'audit

C'est le cœur du moteur Probare. Une fois les données importées, vous lancez les contrôles par cycle.

### Lancer les contrôles

Dans la page **"Contrôles"**, sélectionnez un cycle et cliquez sur **"Lancer les contrôles"**. Probare exécute toutes les règles du cycle en quelques secondes.

Vous pouvez lancer les cycles dans n'importe quel ordre, et les relancer si vous importez de nouveaux fichiers.

### Résultats d'un contrôle

Chaque règle de contrôle produit un résultat avec :

| Champ | Valeur possible | Description |
|-------|----------------|-------------|
| Statut | `ok` / `exception` | La règle est-elle respectée ? |
| Valeur calculée | Nombre ou texte | Le résultat brut du calcul |
| Détails | Texte | Description lisible du résultat |
| Sources | Liste de DonneeSourcee | Quelles données ont alimenté ce calcul |
| Référence NEP | Ex. : `NEP 500` | Norme applicable |
| Sévérité | `critique` / `significative` / `mineure` | Niveau d'alerte si exception |

### Comprendre les exceptions

Une **exception** est déclenchée quand une règle détecte une anomalie. Ce n'est pas nécessairement une erreur — cela demande une investigation par l'auditeur.

Exemples d'exceptions :
- Une facture dont le numéro est dans la séquence mais absente du grand livre (rupture de séquence)
- Un solde fournisseur débiteur (anomalie de position)
- Un montant identique facturé deux fois au même tiers le même jour (doublon probable)
- Une concentration anormale de montants ronds (risque de manipulation)

### Interprétation IA des exceptions

Si le consentement client est accordé et qu'une clé API est configurée, Probare interprète automatiquement chaque exception via Claude (Sonnet) :

**Ce que l'IA fournit :**
1. **Explication** : Pourquoi cette règle a-t-elle été déclenchée ? En langage professionnel, à la première personne
2. **Hypothèses** : Quelles pourraient être les causes probables (erreur de saisie, fraude, anomalie de classement, etc.)
3. **Diligences proposées** : Quelles procédures d'audit appliquer pour investiguer (demande d'explication, réconciliation, vérification de pièces, etc.)

> **Important :** L'IA propose des pistes d'investigation. Elle ne décide pas. L'auditeur reste seul maître de ses conclusions.

### Adaptatif selon le risque de contrôle interne

Les seuils des règles s'adaptent automatiquement au niveau de risque du contrôle interne évalué dans le QCI :

| Niveau de risque CI | Effet sur les seuils |
|--------------------|---------------------|
| Risque élevé | Seuils plus stricts → plus d'exceptions détectées |
| Risque moyen | Seuils standards |
| Risque faible | Seuils plus souples → filtrage des anomalies mineures |

---

## 9. Phase 4 — Questionnaire de contrôle interne (QCI)

Le QCI évalue la qualité de l'environnement de contrôle interne du client. Il est structuré par cycle d'audit.

### Fonctionnement

1. Accédez à la page **"QCI"**
2. Sélectionnez un cycle (ex. : Trésorerie)
3. Répondez à chaque question avec `Oui`, `Non`, ou `N/A`
4. Ajoutez un commentaire si nécessaire
5. Cliquez sur **"Évaluer"**

### Exemple de questions (cycle Trésorerie)

- Les chèques sont-ils signés par deux personnes distinctes ?
- Les rapprochements bancaires sont-ils réalisés mensuellement ?
- L'accès aux comptes bancaires est-il restreint ?
- Les mouvements de caisse font-ils l'objet d'un contrôle physique régulier ?

### Calcul du niveau de risque

Probare calcule un score de risque (0,0 à 1,0) en fonction des réponses :
- `Oui` → réduit le risque
- `Non` à une question à risque → augmente le risque
- `N/A` → neutre

Niveaux de risque :

| Score | Niveau | Impact sur les contrôles |
|-------|--------|--------------------------|
| 0,0 – 0,3 | Faible | Seuils relâchés, contrôles allégés |
| 0,3 – 0,6 | Moyen | Seuils standards |
| 0,6 – 1,0 | Élevé | Seuils stricts, contrôles renforcés |

### Synthèse IA du QCI

Après soumission des réponses, si l'IA est disponible, Probare génère une synthèse automatique :

- **Forces** de l'environnement de contrôle
- **Faiblesses** identifiées
- **Recommandations** pour améliorer le contrôle interne
- **Conclusion générale** sur le niveau de fiabilité

Cette synthèse est incluse dans le dossier de travail.

---

## 10. Phase 5 — Revue des exceptions

La revue des exceptions est l'étape où l'auditeur examine chaque anomalie signalée et prend une décision documentée.

### Liste des exceptions

La page **"Exceptions"** affiche toutes les anomalies détectées, triables par :
- Cycle d'audit
- Sévérité (critique en premier)
- Statut (ouverte / tranchée)

### Traiter une exception

Pour chaque exception, l'auditeur doit :

1. **Lire l'anomalie** : quelle règle, quelle NEP, quelle valeur calculée
2. **Consulter l'interprétation IA** (si disponible) : explication, hypothèses, diligences suggérées
3. **Accéder à la source** : cliquez sur le lien de provenance pour voir la cellule exacte dans le fichier source
4. **Prendre une décision** et la documenter :
   - *"Erreur de saisie confirmée, montant corrigé par le client"*
   - *"Explication obtenue du client — anomalie justifiée"*
   - *"Pas d'incidence sur les comptes — anomalie non significative"*
5. **Marquer comme tranchée** (`statut = "tranchee"`)

Toutes les décisions sont horodatées et enregistrées dans le journal d'audit avec le nom du décideur.

### Condition de passage

**La transition vers la génération de documents est bloquée tant qu'une exception reste en statut "ouverte".**

Cela garantit qu'aucun rapport ne peut être produit sans que l'auditeur ait pris position sur chaque anomalie.

---

## 11. Phase 6 — Génération des documents

Une fois toutes les exceptions tranchées, Probare peut générer les documents de sortie.

### Dossier de travail (Working Paper)

Le dossier de travail est généré au format **DOCX** (Word), un fichier par cycle. Il contient :

- En-tête de mission (client, exercice, cycle, auditeur)
- Tableau des contrôles exécutés avec résultats
- Liste des exceptions avec leur traitement
- Diligences réalisées
- Références NEP
- Pour chaque chiffre : lien de provenance vers le document source

### Rapport d'audit

Le rapport d'audit est une synthèse globale au format **DOCX**. Il contient :

- Résumé exécutif de la mission
- Anomalies significatives détectées et leur traitement
- Niveau de risque par cycle (issu du QCI)
- Conclusions préliminaires par cycle
- Qualité de l'environnement de contrôle interne

> **Note :** Ce rapport est un **projet** (draft). L'opinion finale est toujours rédigée et signée manuellement par l'auditeur. Probare ne signe jamais à votre place.

### Tableau des exceptions (Excel)

Export au format **XLSX** avec :
- Toutes les exceptions détectées
- Statut et décision de l'auditeur
- Sévérité et cycle
- Référence NEP

### Journal d'audit

Export du journal complet au format **JSON** comprenant :
- Toutes les transitions d'état
- Tous les appels à l'IA (modèle utilisé, tokens consommés, horodatage)
- Toutes les actions humaines (décisions, consentement, etc.)

---

## 12. Phase 7 — Opinion

L'état `opinion` est le dernier état du pipeline. Il marque la clôture du projet dans Probare.

### Ce que Probare ne fait pas à cette étape

Probare **ne génère pas l'opinion d'audit**. Par principe, l'opinion finale engage la responsabilité professionnelle de l'auditeur signataire. Elle doit être rédigée, revue et signée manuellement.

### Ce que vous faites à cette étape

1. Relire l'ensemble des documents générés
2. Vérifier que toutes les exceptions ont été correctement tranchées
3. Rédiger l'opinion d'audit (certification, refus, réserves, etc.)
4. Signer le rapport final
5. Archiver le dossier

Le projet peut rester en état `opinion` comme archive consultable.

---

## 13. Les 52 règles de contrôle par cycle

### Cycle Trésorerie — 8 contrôles (comptes 5xx)

| Référence | Nom | Description |
|-----------|-----|-------------|
| TRESOR-BAL-EQUIL | Équilibre de la balance | Vérifie que la somme des débits = somme des crédits |
| TRESOR-GL-BAL | Cohérence GL/Balance | Les soldes du grand livre correspondent-ils à la balance ? |
| TRESOR-SEQ-RECETTES | Séquence des recettes | Recherche des ruptures dans la numérotation des reçus de caisse |
| TRESOR-SOLDES-ANORM | Soldes anormaux | Détecte les comptes de trésorerie avec un solde créditeur (anormal pour un actif) |
| TRESOR-MONTANTS-RONDS | Concentration de montants ronds | Taux élevé de montants se terminant par 000 ou 00000 (risque de manipulation) |
| TRESOR-CUTOFF | Concentration en fin de période | Pic d'écritures dans les derniers jours de l'exercice (risque de cut-off) |
| TRESOR-VARIATION | Variation N/N-1 | Écart entre l'exercice en cours et l'exercice précédent (analytique) |
| TRESOR-RAPPROCH | Rapprochement bancaire | Le solde comptable correspond-il au relevé bancaire ? |

### Cycle Achats-Fournisseurs — 9 contrôles (comptes 40x, 60x–63x)

| Référence | Nom | Description |
|-----------|-----|-------------|
| ACHATS-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| ACHATS-SEQ-FACTURES | Séquence des factures | Ruptures dans la numérotation des factures fournisseurs |
| ACHATS-SOLDES-ANORM | Soldes anormaux | Comptes fournisseurs avec solde débiteur (avoirs ou erreurs) |
| ACHATS-DOUBLONS | Doublons de factures | Même montant, même fournisseur, même date → doublon probable |
| ACHATS-CONCENTRATION | Concentration fournisseurs | Dépendance excessive envers un petit nombre de fournisseurs |
| ACHATS-AVOIRS-RATIO | Ratio avoirs anormal | Proportion élevée d'avoirs par rapport aux achats (retours, erreurs, fraude) |
| ACHATS-MONTANTS-RONDS | Montants ronds | Concentration de factures à montants ronds |
| ACHATS-CUTOFF | Cut-off achats | Factures enregistrées hors période |
| ACHATS-VARIATION | Variation N/N-1 | Écart analytique achats vs. exercice précédent |

### Cycle Ventes-Clients — 10 contrôles (comptes 41x, 70x–73x)

| Référence | Nom | Description |
|-----------|-----|-------------|
| VENTES-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| VENTES-SEQ-FACTURES | Séquence des factures | Ruptures dans la numérotation des factures clients |
| VENTES-SOLDES-ANORM | Soldes anormaux | Comptes clients avec solde créditeur (avoirs non utilisés ou erreurs) |
| VENTES-DOUBLONS | Doublons de factures | Même montant, même client, même date |
| VENTES-CONCENTRATION | Concentration clients | Dépendance excessive envers peu de clients |
| VENTES-AVOIRS-RATIO | Ratio avoirs anormal | Proportion d'avoirs clients élevée |
| VENTES-MONTANTS-RONDS | Montants ronds | Concentration sur des montants ronds |
| VENTES-CUTOFF | Cut-off ventes | Factures enregistrées hors période |
| VENTES-CREANCES-AGEES | Créances âgées | Créances de plus de 90 jours non provisionnées |
| VENTES-VARIATION | Variation N/N-1 | Écart analytique ventes vs. exercice précédent |

### Cycle Immobilisations — 5 contrôles (comptes 2xx)

| Référence | Nom | Description |
|-----------|-----|-------------|
| IMMO-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| IMMO-SOUS-AMORT | Sous-amortissement | Actifs dont la dotation aux amortissements semble insuffisante |
| IMMO-SUR-AMORT | Sur-amortissement | Actifs amortis au-delà de leur valeur nette comptable |
| IMMO-SOLDES-ANORM | Soldes anormaux | Immobilisations avec solde créditeur (impossible pour un actif) |
| IMMO-VARIATION | Variation N/N-1 | Entrées et sorties d'immobilisations vs. exercice précédent |

### Cycle Stocks — 5 contrôles (comptes 3xx)

| Référence | Nom | Description |
|-----------|-----|-------------|
| STOCKS-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| STOCKS-SOLDES-CREDIT | Soldes créditeurs | Stocks avec solde créditeur (impossible pour un actif) |
| STOCKS-VARIATION | Variation N/N-1 | Variation du stock vs. exercice précédent |
| STOCKS-MONTANTS-RONDS | Montants ronds | Valorisation avec concentration de montants ronds |
| STOCKS-CUTOFF | Cut-off stocks | Mouvements de stocks enregistrés hors période |

### Cycle Paie-Personnel — 5 contrôles (comptes 42x, 64x)

| Référence | Nom | Description |
|-----------|-----|-------------|
| PAIE-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| PAIE-VARIATION | Variation N/N-1 | Variation de la masse salariale vs. exercice précédent |
| PAIE-CHARGES-SOCIALES | Ratio charges sociales | Charges sociales incohérentes avec la masse salariale |
| PAIE-REGULARITE | Régularité des salaires | Variations mensuelles anormalement élevées ou basses |
| PAIE-DETTES-ANORM | Dettes sociales anormales | Soldes de dettes envers le personnel ou les organismes sociaux anormalement élevés |

### Cycle Impôts & Taxes — 5 contrôles (comptes 44x, 63x)

| Référence | Nom | Description |
|-----------|-----|-------------|
| IMPOTS-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| IMPOTS-VARIATION | Variation N/N-1 | Variation des charges fiscales vs. exercice précédent |
| IMPOTS-TVA-COHERENCE | Cohérence TVA | TVA collectée et TVA déductible cohérentes avec l'activité |
| IMPOTS-TVA-SOLDE | Solde TVA normal | Solde du compte TVA cohérent (crédit d'impôt anormal ?) |
| IMPOTS-CUTOFF | Cut-off fiscal | Charges fiscales hors période |

### Cycle Capitaux Propres — 5 contrôles (comptes 10x–15x)

| Référence | Nom | Description |
|-----------|-----|-------------|
| CP-GL-BAL | Cohérence GL/Balance | Soldes grands livre vs. balance |
| CP-CAPITAL-VARIATION | Variation du capital | Mouvements du capital social non expliqués |
| CP-PROVISIONS | Mouvement des provisions | Dotations et reprises de provisions cohérentes |
| CP-RESULTAT | Cohérence résultat | Pas simultanément un compte bénéfice et un compte perte |
| CP-CAPITAUX-NEGATIFS | Capitaux propres négatifs | Situation nette négative (signal de difficulté financière grave) |

---

## 14. Traçabilité et provenance des données

La traçabilité est l'un des piliers architecturaux de Probare. Voici comment elle fonctionne de bout en bout.

### Le modèle DonneeSourcee

Chaque valeur dans Probare est encapsulée dans un objet `DonneeSourcee` immuable :

```
DonneeSourcee {
  id           : identifiant unique
  valeur       : la valeur (montant, texte, date, etc.)
  type         : montant | texte | date | compte | numero_piece
  localisation : "Balance!B5" ou "grand_livre.csv:ligne:42:col:Debit"
  fichier_id   : identifiant du fichier source
  confiance    : 0.0 → 1.0 (1.0 pour import direct)
  extrait_par  : ingestion-directe | llm-assisted | calculé
  horodatage   : date et heure de l'extraction
}
```

### Chaîne de traçabilité

```
Fichier Excel (cellule B5)
      ↓ import
DonneeSourcee (localisation: "Balance!B5", confiance: 1.0)
      ↓ calcul
ResultatCalcul (sources: [DonneeSourcee#1, DonneeSourcee#3])
      ↓ si anomalie
Exception (controle_ref: "TRESOR-BAL-EQUIL", nep_ref: "NEP 500")
      ↓ inclus dans
FeuilleTravail (sources vérifiées = présentes)
```

### Immuabilité

L'objet `DonneeSourcee` est **gelé** (frozen) : une fois créé, il ne peut pas être modifié. Cela garantit l'intégrité des données d'audit sur toute la durée du projet.

### Accès à la source depuis l'interface

Dans la page Exceptions, chaque anomalie affiche un lien cliquable vers sa source. En cliquant, vous obtenez :
- Le fichier exact
- La feuille (si Excel)
- La ligne et la colonne
- La valeur brute extraite

---

## 15. Fonctionnalités IA — Ce que fait Claude

Probare utilise trois modèles Claude selon la complexité de la tâche :

| Modèle | Utilisation dans Probare |
|--------|--------------------------|
| **Claude Haiku** | Classification rapide (colonnes, onglets, types de documents) |
| **Claude Sonnet** | Interprétation des exceptions, rédaction des rapports, QCI |
| **Claude Opus** | Réservé aux jugements complexes et escalades |

### 1. Analyse de document à l'import

**Déclenchement :** Import d'un nouveau fichier

**Ce que l'IA reçoit :** Nom du fichier + aperçu des 5 000 premiers caractères

**Ce qu'elle produit :**
```json
{
  "type_comptable": "grand_livre",
  "description": "Grand livre général exercice 2025",
  "nature": "Fichier de comptabilité détaillée",
  "correspond_a": "Cycle Trésorerie - Comptes 5xx",
  "confiance": 0.96
}
```

### 2. Intelligence sur les onglets Excel

**Déclenchement :** Import d'un fichier Excel multi-onglets

**Ce que l'IA reçoit :** Nom de chaque onglet + liste des colonnes + aperçu des premières lignes

**Ce qu'elle produit :** Pour chaque onglet, type comptable détecté, description, recommandation d'import (oui/non), confiance

### 3. Décomposition de liasse

**Déclenchement :** Clic sur "Décomposer la liasse"

**Ce que l'IA reçoit :** Contenu du document bundle

**Ce qu'elle produit :**
```json
{
  "nb_documents": 3,
  "documents": [
    {"type": "balance", "description": "Balance au 31/12/2025"},
    {"type": "grand_livre", "description": "GL Trésorerie 2025"},
    {"type": "annexe", "description": "Tableau des immobilisations"}
  ]
}
```

### 4. Interprétation des exceptions

**Déclenchement :** Automatique après chaque contrôle (si consentement accordé)

**Ce que l'IA reçoit :** Référence du contrôle, NEP, description de l'anomalie, valeurs sources (anonymisées)

**Ce qu'elle produit :**
```json
{
  "explication": "J'observe une rupture dans la séquence de numérotation des factures fournisseurs entre les numéros 1043 et 1047. Trois numéros consécutifs sont absents du grand livre.",
  "hypotheses": [
    "Factures annulées sans être enregistrées en avoir",
    "Factures non comptabilisées (omission volontaire ou involontaire)",
    "Numérotation externe non séquentielle"
  ],
  "diligences_proposees": [
    "Demander au client de justifier les numéros 1044, 1045 et 1046",
    "Vérifier dans le registre des factures fournisseurs papier",
    "Contrôler les avoirs correspondants éventuels"
  ]
}
```

### 5. Évaluation QCI

**Déclenchement :** Après soumission du questionnaire d'un cycle

**Ce que l'IA reçoit :** Toutes les questions et réponses du cycle (anonymisées)

**Ce qu'elle produit :**
```json
{
  "synthese": "L'environnement de contrôle interne de la trésorerie présente des lacunes importantes dans la séparation des tâches...",
  "forces": ["Rapprochements bancaires réalisés mensuellement", "Accès aux comptes restreint"],
  "faiblesses": ["Absence de double signature", "Pas de validation hiérarchique des virements"],
  "recommandations": ["Instaurer une procédure de double validation", "Mettre en place une liste blanche de bénéficiaires"],
  "niveau_risque": "eleve",
  "score": 0.72
}
```

### 6. Analyse des annexes

**Déclenchement :** Clic sur "Analyser" dans la page Annexes

**Ce que l'IA reçoit :** Nom et contenu partiel du document

**Ce qu'elle produit :**
```json
{
  "resume": "Tableau d'amortissement linéaire sur 15 immobilisations...",
  "points_cles": ["Taux d'amortissement de 20% sur le matériel informatique", "3 immobilisations en fin de vie économique"],
  "alertes": ["Le véhicule immatriculé DJ-1234 est amorti à 100% mais toujours en service"]
}
```

### Ce que l'IA ne fait JAMAIS

- Produire un chiffre qui entre dans le calcul d'un contrôle
- Modifier une valeur de la base de données
- Prendre une décision sur une exception
- Signer ou valider un rapport
- Accéder à des données non anonymisées

---

## 16. Sécurité et anonymisation

### Anonymisation avant tout appel IA

Avant d'envoyer quoi que ce soit à l'API Anthropic, Probare remplace les données nominatives par des jetons neutres :

| Donnée réelle | Jeton envoyé à l'API |
|---------------|---------------------|
| "Société Marsa SARL" | "[ENTITE_001]" |
| "DJ123456789" | "[NIF_001]" |
| "Ahmed Mohamed" | "[TIERS_042]" |

La correspondance jeton ↔ valeur réelle est conservée **localement** sur votre machine. Elle n'est jamais transmise à Anthropic.

Quand l'IA retourne une réponse contenant `[ENTITE_001]`, Probare la remplace automatiquement par le nom réel avant affichage.

### Clé API — règles absolues

- La clé API est lue exclusivement depuis la variable d'environnement `ANTHROPIC_API_KEY`
- Elle n'est jamais écrite dans le code source
- Elle n'est jamais écrite dans la base de données
- Elle n'est jamais commitée dans Git
- Le fichier `.env` est dans `.gitignore`

### Consentement client

Le système vérifie le consentement à chaque appel IA :

```python
if not projet.consentement_client:
    raise ConsentementManquantError("Appel IA impossible sans consentement client")
```

Sans consentement, aucun appel n'est effectué, même si la clé API est configurée.

### Intégrité des données

- Chaque fichier importé est haché (SHA256) à l'import
- Le hash est stocké dans `fichier_source.hash`
- En cas de modification accidentelle du fichier source, le hash permet de le détecter

---

## 17. Journal d'audit (piste d'audit)

Probare enregistre automatiquement chaque événement significatif dans un journal immuable.

### Types d'entrées de journal

| Type | Déclenché par | Informations enregistrées |
|------|--------------|--------------------------|
| `transition_etat` | Passage d'une phase à l'autre | État précédent, nouvel état, horodatage |
| `appel_llm` | Tout appel à l'API Claude | Modèle, tokens utilisés, durée, tâche, horodatage |
| `action_humaine` | Décision de l'auditeur | Action, description, auteur, horodatage |
| `erreur_llm` | Échec d'un appel IA | Message d'erreur, contexte |
| `avertissement_llm` | Réponse IA atypique | Nature de l'avertissement |

### Consulter le journal

Dans la page **"Journal"**, vous pouvez :
- Voir les 50 dernières entrées par défaut
- Filtrer par type d'événement
- Rechercher par date
- Exporter en JSON

### Valeur légale du journal

Le journal peut servir de **preuve** en cas de litige ou de contrôle qualité :
- Qui a accordé le consentement client, et quand
- Quels contrôles ont été lancés, dans quel ordre
- Quelles exceptions ont été tranchées, par qui, avec quelle justification
- Combien d'appels à l'IA ont été effectués et quels modèles ont été utilisés

---

## 18. Export et rapports

### Formats d'export

| Document | Format | Contenu |
|----------|--------|---------|
| Dossier de travail | DOCX (Word) | Un fichier par cycle, contrôles + exceptions + diligences |
| Rapport d'audit draft | DOCX (Word) | Synthèse globale, conclusions préliminaires |
| Tableau des exceptions | XLSX (Excel) | Toutes les exceptions avec statuts et décisions |
| Journal d'audit | JSON | Trace complète de tous les événements |

### Comment exporter

Dans la page **"Rapport"** :

1. Cliquez sur **"Générer le dossier de travail"** → téléchargement automatique du DOCX
2. Cliquez sur **"Générer le rapport"** → téléchargement automatique du DOCX
3. Cliquez sur **"Exporter les exceptions"** → téléchargement automatique du XLSX
4. Cliquez sur **"Télécharger le journal"** → téléchargement du JSON

### Ce que contient le dossier de travail

Pour chaque cycle (ex. Trésorerie) :

```
DOSSIER DE TRAVAIL — TRÉSORERIE
Client : [Nom du client]         Exercice : 2025
Auditeur : [Nom]                 Date : 25/06/2026

CONTRÔLES EXÉCUTÉS
─────────────────────────────────────────────
TRESOR-BAL-EQUIL    OK      Σ Débits = Σ Crédits = 12 345 678 DJF
TRESOR-GL-BAL       OK      Écart GL/Balance = 0 DJF
TRESOR-SEQ-RECETTES EXCEPTION  Numéros manquants : 1044, 1045, 1046
...

EXCEPTIONS ET TRAITEMENT
─────────────────────────────────────────────
Exception : TRESOR-SEQ-RECETTES (NEP 500 — Significative)
Description : Rupture de séquence — 3 numéros de reçus manquants
Décision auditeur : "Explication obtenue — reçus annulés pour erreur"
Décideur : Jean Dupont        Date : 24/06/2026

SOURCES
─────────────────────────────────────────────
[1] grand_livre_2025.xlsx — Feuille "GL Tréso" — Ligne 142 — Compte 512
[2] grand_livre_2025.xlsx — Feuille "GL Tréso" — Ligne 143 — Compte 512
```

---

## 19. Référence technique

### Architecture

```
probare/
├── apps/
│   ├── desktop/           # Interface utilisateur (Electron + React + TypeScript)
│   │   ├── src/main/      # Processus principal Electron
│   │   └── src/renderer/  # Interface React
│   │       ├── pages/     # 14 pages de l'application
│   │       ├── components/ # Composants UI réutilisables
│   │       ├── stores/    # État global (Zustand)
│   │       └── hooks/     # Hooks React (useApi, useProjet, useToast)
│   │
│   └── engine/            # Moteur de calcul (Python + FastAPI)
│       └── probare_engine/
│           ├── api/       # 50+ endpoints REST
│           ├── controls/  # 52 règles de contrôle
│           ├── ingestion/ # Lecture Excel/CSV
│           ├── provenance/ # Modèle DonneeSourcee
│           ├── llm/       # Intégration Claude
│           ├── storage/   # Base de données SQLite
│           ├── anonymization/ # Anonymiseur
│           └── reporting/ # Génération DOCX/XLSX
│
├── test_data/             # Données de test (Marsa, Dalol_trading)
└── CLAUDE.md              # Règles de développement
```

### Base de données

Probare utilise **SQLite** — une base légère sans serveur, stockée dans un unique fichier par projet. Elle contient 20 tables :

| Table | Description |
|-------|-------------|
| `projet` | Informations du projet d'audit |
| `fichier_source` | Fichiers importés |
| `donnee_sourcee` | Toutes les valeurs avec provenance |
| `resultat_calcul` | Résultats des règles de contrôle |
| `exception` | Anomalies détectées |
| `feuille_travail` | Documents de travail générés |
| `document_annexe` | Pièces justificatives |
| `qci_reponse` | Réponses au questionnaire QCI |
| `qci_evaluation` | Synthèse IA du QCI |
| `journal` | Piste d'audit complète |

Localisation par défaut :
```
~/.probare/projets/{projet_id}/audit.db
```

### Technologies utilisées

**Backend (moteur de calcul)**
- Python 3.10+, FastAPI, Uvicorn
- Pandas, NumPy (traitement des données)
- openpyxl (lecture Excel), python-docx (génération Word)
- Pydantic (validation des données), SQLite
- anthropic SDK (API Claude)

**Frontend (interface)**
- Electron 33+, React 18+, TypeScript 5+
- Tailwind CSS (styles), Radix UI (composants accessibles)
- Zustand (état global), React Router (navigation)
- Framer Motion (animations), Lucide React (icônes)

### API REST disponibles

Le moteur expose une API REST documentée à l'adresse `http://127.0.0.1:5000/docs` (en développement).

Principales familles d'endpoints :

| Préfixe | Description |
|---------|-------------|
| `GET/POST /api/projets` | Gestion des projets |
| `POST /api/projets/{id}/fichiers` | Import de fichiers |
| `POST /api/projets/{id}/controles/{cycle}` | Lancement des contrôles |
| `GET /api/projets/{id}/exceptions` | Consultation des exceptions |
| `PATCH /api/projets/{id}/exceptions/{id}` | Traitement d'une exception |
| `GET/POST /api/projets/{id}/qci` | Questionnaire QCI |
| `GET /api/projets/{id}/dossier-travail` | Export dossier de travail |
| `GET /api/projets/{id}/rapport` | Export rapport d'audit |
| `GET /api/projets/{id}/journal` | Consultation du journal |

---

## 20. Questions fréquentes

### Fonctionnement général

**Q : Probare remplace-t-il l'auditeur ?**

Non. Probare assiste l'auditeur en automatisant les tâches répétitives (calculs, vérifications mécaniques, rédaction de rapports). Toutes les décisions significatives — traitement des exceptions, choix des procédures, opinion finale — restent entre les mains de l'auditeur. La responsabilité professionnelle ne se délègue pas à un logiciel.

**Q : Que se passe-t-il si je n'ai pas de connexion internet ?**

Les 52 règles de contrôle fonctionnent entièrement hors ligne. Seules les fonctionnalités IA nécessitent une connexion (interprétation des exceptions, génération de rapports, analyse de documents). Sans connexion, Probare reste pleinement fonctionnel pour les calculs et la gestion du dossier.

**Q : Que se passe-t-il si l'API Claude est indisponible ?**

Le moteur de calcul fonctionne de manière indépendante. En cas d'indisponibilité de l'API, les contrôles sont exécutés normalement, les exceptions sont signalées, mais sans interprétation IA. Vous pouvez traiter les exceptions manuellement et générer les rapports ultérieurement.

**Q : Puis-je utiliser Probare sans clé API Anthropic ?**

Oui. Sans clé API, Probare fonctionne en mode purement déterministe : calculs Python complets, détection d'anomalies, mais aucune fonctionnalité IA (pas d'interprétation, pas de génération automatique de rapports rédigés). Idéal pour tester l'outil ou pour les missions ne nécessitant pas de génération automatique.

### Données et sécurité

**Q : Mes données clients sont-elles envoyées à Anthropic ?**

Partiellement et anonymisées. Avant chaque appel à l'API, Probare remplace tous les identifiants (noms, NIF, noms de tiers) par des jetons neutres. Les données brutes (montants, dates, numéros de compte) peuvent être transmises dans ce contexte anonymisé. La correspondance jeton ↔ identité réelle reste sur votre machine.

**Q : Où sont stockées les données de mes projets ?**

Par défaut dans `~/.probare/projets/` sur votre machine locale. Vous pouvez modifier ce chemin dans le fichier `.env`. Aucune donnée n'est stockée en dehors de votre machine (sauf les extraits anonymisés envoyés à l'API pour les fonctions IA).

**Q : Mes projets sont-ils sauvegardés automatiquement ?**

Probare sauvegarde chaque action immédiatement dans la base SQLite. Il n'y a pas de notion de "Sauvegarder" manuel — chaque import, chaque réponse QCI, chaque décision sur une exception est persistée en temps réel. En revanche, **Probare ne sauvegarde pas vers le cloud** — la sauvegarde externe est de votre responsabilité.

### Contrôles et anomalies

**Q : Toutes les exceptions sont-elles des erreurs ?**

Non. Une exception signale une anomalie statistique ou logique qui mérite attention. Elle peut avoir une explication légitime : une saisie inhabituelle mais correcte, une opération exceptionnelle documentée, ou simplement un seuil trop sensible. L'auditeur documente sa position sur chaque exception.

**Q : Puis-je relancer les contrôles après avoir importé de nouveaux fichiers ?**

Oui. Vous pouvez relancer les contrôles d'un cycle à tout moment pendant la phase "Contrôles". Les nouveaux résultats remplacent les anciens. Probare archive les résultats antérieurs dans le journal.

**Q : Peut-on modifier les seuils des règles de contrôle ?**

Les seuils s'adaptent automatiquement selon le niveau de risque du QCI. Pour une personnalisation manuelle avancée, contactez le support — cette option est prévue dans les développements futurs.

### Import de données

**Q : Mon grand livre a des colonnes avec des noms non standard. Probare peut-il les comprendre ?**

Oui. Probare utilise une détection automatique des colonnes (via l'IA pour les cas ambigus). Si la détection automatique échoue, une interface de mapping manuel vous permet d'associer chaque colonne de votre fichier au champ attendu (Compte, Libellé, Date, Débit, Crédit, etc.).

**Q : Combien de lignes peut traiter Probare ?**

Probare a été testé avec des grands livres de plusieurs centaines de milliers de lignes. Les performances dépendent de votre machine, mais le moteur Python (Pandas) est optimisé pour le traitement en mémoire de volumes comptables standards.

**Q : Mon fichier Excel contient des formules. Sont-elles prises en compte ?**

Probare lit les **valeurs calculées** (ce que vous voyez à l'écran dans Excel), pas les formules elles-mêmes. Si une formule produit un résultat erroné dans Excel, Probare importera ce résultat erroné. Il est recommandé de vérifier l'intégrité de vos fichiers avant import.

### Rapports et exports

**Q : Le rapport généré est-il directement utilisable comme rapport d'audit final ?**

Non. Probare génère un **projet de rapport** (draft) conçu pour servir de base de travail. L'auditeur doit relire, compléter, et signer le rapport final. L'opinion d'audit ne peut pas être déléguée à un logiciel.

**Q : Puis-je exporter dans d'autres formats que Word et Excel ?**

Dans la version actuelle, les formats disponibles sont DOCX (Word) et XLSX (Excel). Le format PDF est prévu dans les développements futurs. Pour convertir en PDF, vous pouvez utiliser la fonction "Enregistrer au format PDF" de Microsoft Word ou LibreOffice.

---

## Annexe — Glossaire

| Terme | Définition |
|-------|-----------|
| **Balance** | Tableau récapitulatif des soldes de tous les comptes à une date donnée |
| **Circularisation** | Procédure de confirmation externe (clients, banques, avocats) |
| **Cut-off** | Anomalie de rattachement des opérations à la bonne période comptable |
| **DonneeSourcee** | Objet Probare représentant une valeur comptable avec sa provenance complète |
| **Exception** | Anomalie signalée par une règle de contrôle, nécessitant investigation |
| **Grand livre (GL)** | Enregistrement détaillé de toutes les écritures comptables par compte |
| **H2A** | Autorité de contrôle légal des auditeurs à Djibouti |
| **Liasse** | Bundle de plusieurs documents comptables regroupés dans un seul fichier |
| **NEP** | Norme d'Exercice Professionnel — règles encadrant l'audit en France et à Djibouti |
| **NIF** | Numéro d'Identification Fiscale du client |
| **Opinion** | Rapport final signé par l'auditeur exprimant sa conclusion sur les comptes |
| **Pipeline** | Séquence ordonnée des phases d'audit dans Probare (cadrage → opinion) |
| **Provenance** | Traçabilité d'une valeur jusqu'à sa source exacte dans les documents comptables |
| **QCI** | Questionnaire de Contrôle Interne — évaluation de l'environnement de contrôle du client |
| **Seuil de signification** | Montant en-deçà duquel une anomalie est jugée non significative pour l'opinion |
| **Sondage** | Technique d'échantillonnage pour sélectionner des éléments à vérifier |
| **Token (anonymisation)** | Jeton neutre remplaçant un identifiant sensible avant transmission à l'IA |

---

*Guide d'utilisation Probare — Version 1.0 — Juin 2026*

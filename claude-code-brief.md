# Brief Claude Code — Probare

Ce document se lit en deux parties :
- **Partie A** : le prompt à donner à Claude Code — il décrit l'objectif final (version de production).
- **Partie B** : les instructions détaillées pour construire le **MVP** maintenant.

Donne d'abord la Partie A pour fixer le cap, puis travaille uniquement sur le périmètre de la Partie B.

---

# PARTIE A — Prompt : objectif final (production)

> Tu vas construire **Probare**, un logiciel de bureau (desktop) d'audit comptable assisté par IA, destiné à un cabinet d'audit. Sa raison d'être : un cabinet utilise déjà l'IA dans ses audits, mais le modèle invente des chiffres, oublie des éléments et exige une supervision permanente. Probare résout cela non pas en retirant l'humain — l'opinion d'audit engage juridiquement un professionnel habilité — mais en rendant **chaque erreur détectable et traçable** et en réduisant la supervision à quelques décisions de jugement.
>
> **Principe directeur absolu :** séparer le déterministe du probabiliste. Tout calcul (totaux, rapprochements, ratios, réconciliations, variations) est exécuté par du code Python. Le LLM (Claude API) sert seulement à extraire des données depuis des documents, interpréter des anomalies déjà levées par le code, et rédiger des feuilles de travail. **Le LLM ne produit jamais un nombre destiné au dossier d'audit.**
>
> **Règle de provenance :** aucune valeur n'existe dans le système sans un lien vers sa source (fichier, localisation précise, confiance d'extraction). Tout résultat calculé conserve la trace des données sources qui l'ont produit. Le rapport final relie chaque chiffre affiché à sa preuve.
>
> En production, Probare couvre plusieurs types d'audit et secteurs, ingère des pièces structurées (Excel/CSV) et non structurées (PDF/images via OCR), applique les **NEP** (Normes d'Exercice Professionnel, autorité H2A, référentiel applicable à Djibouti) comme jeu de règles configurable et versionné, gère le cadrage (planification NEP 300, connaissance de l'entité NEP 315, seuil de signification NEP 320), exécute les procédures par cycle, lève et fait trancher les exceptions (NEP 450), produit le dossier de travail (NEP 230) et un projet de rapport — l'opinion et la signature restant humaines.
>
> Architecture cible : coquille **Electron** + interface **React/TypeScript/Tailwind** + backend **Python/FastAPI** en sidecar, persistance **SQLite par projet**, **Claude API** (tout cloud, avec consentement client et anonymisation des données nominatives avant envoi), pipeline en **machine à états** journalisée.
>
> Tu construiras d'abord le MVP décrit en Partie B. Ne déborde pas du périmètre MVP sans qu'on te le demande, mais conçois chaque brique pour qu'elle s'étende vers cette cible (interfaces propres, règles et NEP en données, fournisseur LLM derrière une abstraction).

---

# PARTIE B — Instructions de construction du MVP

## B.0 Périmètre MVP (à respecter strictement)

- Un seul type d'audit : révision / audit des états financiers.
- Cycles : **trésorerie**, puis **achats-fournisseurs**, puis **ventes-clients**.
- Entrées : **Excel/CSV uniquement** (grand livre + balance). Pas d'OCR au MVP.
- Cadrage minimal avec **seuil de signification saisi par l'humain**.
- Provenance complète, contrôles déterministes, revue des exceptions, couche LLM, export dossier + rapport.
- Hors périmètre : OCR, circularisation, échantillonnage statistique, multi-secteurs, multi-utilisateur, modèles locaux, comptes de groupe.

## B.1 Conventions et règles non négociables

1. **Le LLM ne calcule jamais.** Toute arithmétique est en Python. Si tu es tenté de demander un nombre à Claude pour le dossier, c'est une erreur de conception : demande-lui plutôt d'extraire des nombres sourcés, et calcule en code.
2. **Pas de valeur sans provenance.** Toute donnée entrant dans un calcul est une `DonneeSourcee` (cf. B.4).
3. **Clé API en variable d'environnement** `ANTHROPIC_API_KEY`. Jamais en dur, jamais committée, jamais en base.
4. **Fournisseur LLM derrière une interface** (`LLMClient`) pour pouvoir changer d'implémentation plus tard.
5. **NEP en données, pas en dur** : chaque contrôle porte un champ `nep_ref`. Les contrôles sont déclarés dans un registre, pas dispersés dans le code.
6. **Tout est journalisé** : chaque transition d'état et chaque appel LLM est écrit dans la piste d'audit.
7. **Tests** : chaque contrôle déterministe a un test unitaire avec un jeu de données minimal (équilibré / déséquilibré).
8. Langue de l'UI et des livrables : **français**.

## B.2 Structure du dépôt

```
probare/
├── apps/
│   ├── desktop/              # Electron + React/TS/Tailwind
│   │   ├── src/main/         # process principal Electron (spawn du sidecar)
│   │   ├── src/renderer/     # UI React
│   │   └── package.json
│   └── engine/               # backend Python (FastAPI sidecar)
│       ├── probare_engine/
│       │   ├── api/          # routes FastAPI
│       │   ├── ingestion/    # lecture Excel/CSV -> DonneeSourcee
│       │   ├── provenance/   # modèle + stockage provenance
│       │   ├── controls/     # moteur de règles + registre des contrôles
│       │   ├── cycles/       # logique par cycle (trésorerie, achats, ventes)
│       │   ├── llm/          # LLMClient (abstraction) + impl Claude
│       │   ├── anonymization/
│       │   ├── statemachine/ # pipeline
│       │   ├── reporting/    # export docx/xlsx
│       │   ├── storage/      # SQLite (un fichier par projet)
│       │   └── audit_trail/  # journalisation
│       ├── tests/
│       └── pyproject.toml
├── packages/
│   └── shared-types/         # types partagés (générés depuis schémas)
├── README.md
└── CLAUDE.md                 # règles ci-dessus, à respecter en permanence
```

Crée un `CLAUDE.md` à la racine reprenant B.1 pour que les règles persistent entre sessions.

## B.3 Stack et mise en place

- Backend : Python 3.11+, FastAPI, uvicorn, pandas, numpy, openpyxl, python-docx, pydantic, SQLite (module `sqlite3` ou SQLModel).
- SDK LLM : `anthropic` (Python).
- Desktop : Electron + Vite + React + TypeScript + Tailwind.
- Communication : Electron spawn le sidecar Python (uvicorn sur `127.0.0.1`, port libre), l'UI appelle l'API en HTTP local. Gère proprement le démarrage/arrêt du sidecar avec le cycle de vie de l'app.
- Packaging (à préparer dès le début, c'est le risque technique principal) : PyInstaller pour le sidecar, electron-builder pour l'app, le binaire Python embarqué comme ressource.

**Première tâche : un « hello world » de bout en bout** — Electron lance le sidecar, l'UI affiche une donnée renvoyée par FastAPI. Ne va pas plus loin tant que ça ne tourne pas.

## B.4 Modèle de données (SQLite, un fichier par projet)

Tables minimales :

- `projet` : id, nom, client (chiffré/pseudonymisé), nif (pseudonymisé), exercice, seuil_signification, seuil_planification, consentement_client (bool + horodatage), etat_courant.
- `fichier_source` : id, nom, chemin_relatif, type, hash, importe_le.
- `donnee_sourcee` : id, projet_id, fichier_source_id, valeur, type, localisation, confiance_extraction, extrait_par, horodatage.
- `resultat_calcul` : id, projet_id, controle_ref, valeur, statut (ok | exception), details, sources (liste de donnee_sourcee.id).
- `exception` : id, projet_id, controle_ref, nep_ref, severite, description, statut (ouverte | tranchée), decision_humaine, decideur, horodatage.
- `feuille_travail` : id, projet_id, cycle, contenu_redige, sources, nep_ref.
- `journal` : id, projet_id, type (transition_etat | appel_llm | action_humaine), payload, horodatage.

`DonneeSourcee` (pydantic) reste la seule porte d'entrée des nombres dans le moteur de calcul.

## B.5 Machine à états du pipeline

États : `cadrage → ingestion → extraction → controles → revue → generation → opinion`.

- Chaque transition est journalisée et persistée (reprise possible après coupure).
- On ne passe à `generation` que si toutes les exceptions sont à l'état `tranchée`.
- `opinion` est un état **manuel** (l'humain valide ; Probare ne signe pas).

## B.6 Ingestion et provenance

- Lire les exports Excel/CSV (grand livre, balance) avec pandas/openpyxl.
- Pour chaque cellule pertinente, créer une `DonneeSourcee` avec `localisation = "feuille!cellule"` et `extrait_par = "ingestion-directe"` (confiance = 1.0 pour les entrées structurées).
- Les nombres extraits sont stockés tels quels ; aucune transformation non tracée.

## B.7 Moteur de contrôles déterministes

Registre de contrôles, chacun : `ref`, `libelle`, `nep_ref`, `cycle`, `fonction`. Chaque fonction prend des `DonneeSourcee`, renvoie un `resultat_calcul` et, si échec, lève une `exception` rattachée à sa NEP.

Contrôles du MVP (tous en code, jamais via LLM) :

- **Équilibre de la balance** : Σ débits = Σ crédits. (NEP 500)
- **Cohérence grand livre / balance** : Σ mouvements du grand livre par compte = solde de la balance. (NEP 500)
- **Contrôle d'addition (foliotage)** : recalcul des totaux affichés. (NEP 500)
- **Continuité des séquences** de numéros de factures par cycle (détection de trous/doublons). (NEP 330 — exhaustivité)
- **Rapprochement bancaire** (cycle trésorerie) si relevé fourni : solde comptable vs solde relevé, écarts. (NEP 500)
- **Variations N/N-1** au-delà du seuil de signification → exception analytique. (NEP 520)
- **Ratios de cohérence** simples par cycle. (NEP 520)

Chaque échec = une exception avec `severite`, `description`, `sources` (les `DonneeSourcee` concernées), `nep_ref`.

## B.8 Couche LLM (Claude API)

**Abstraction `LLMClient`** avec une implémentation Claude (SDK `anthropic`). Endpoint Messages, `anthropic-version: 2023-06-01`, clé via `ANTHROPIC_API_KEY`.

**Routage des modèles** (les IDs sont des snapshots fixes, pas des pointeurs évolutifs) :

- `claude-sonnet-4-6` — par défaut : interprétation des exceptions, rédaction des feuilles de travail.
- `claude-opus-4-8` — escalade pour les points de jugement difficiles et la revue de cohérence du raisonnement.
- `claude-haiku-4-5` — tâches simples de classification/typage de colonnes si besoin.

**Sorties structurées** : utiliser la capacité de structured outputs (JSON contraint par schéma) pour toute donnée que le code va consommer. Imposer un schéma strict ; ne jamais parser du texte libre pour récupérer des champs.

**Usages LLM autorisés au MVP :**

1. **Typage/mapping de colonnes** d'un export comptable inconnu (quelle colonne est le débit, le crédit, la date, le n° de pièce). Sortie : schéma de mapping, validé ensuite par l'humain.
2. **Interprétation d'une exception** déjà levée par le code : explication en langage clair, hypothèses de cause, piste de résolution. Entrée : l'exception + ses `DonneeSourcee`. Le LLM **ne recalcule rien**.
3. **Rédaction des feuilles de travail** à partir des résultats déjà calculés et de leurs sources.

**Interdits LLM :** produire/estimer un montant, « vérifier » des chiffres (c'est le rôle du code), trancher une exception (c'est le rôle de l'humain).

**Avant tout appel** : vérifier `consentement_client = vrai`, passer les données par la couche d'anonymisation (B.9), journaliser l'appel.

## B.9 Anonymisation

Avant envoi à l'API : pseudonymiser les identifiants nominatifs (raison sociale, NIF, noms de tiers/fournisseurs/clients) via une table de correspondance locale (`token ↔ valeur réelle`) stockée dans le projet et **jamais envoyée**. Ré-identifier localement au retour. Les montants et écritures peuvent transiter ; les identifiants nominatifs non.

## B.10 Revue des exceptions (UI)

Écran listant les exceptions ouvertes : pour chacune, le contrôle, la NEP, la sévérité, les `DonneeSourcee` (cliquables vers la source), l'interprétation LLM, et une action humaine (accepter / corriger / justifier). Une exception tranchée enregistre `decision_humaine`, `decideur`, horodatage dans le journal.

## B.11 Génération des livrables

- **Dossier de travail** (NEP 230) : par cycle, contrôles exécutés, résultats, exceptions et leur traitement, feuilles de travail rédigées — chaque chiffre accompagné de sa provenance.
- **Projet de rapport** : synthèse, anomalies non corrigées, **chaque chiffre lié à sa source**.
- Export `.docx` (python-docx) et tableaux `.xlsx` (openpyxl).
- Aucune valeur dans un livrable sans `DonneeSourcee` correspondante : ajoute une vérification automatique qui échoue la génération si un chiffre non sourcé est détecté.

## B.12 Ordre de construction (chaque étape doit être démontrable)

1. Squelette monorepo + `CLAUDE.md` + « hello world » Electron ↔ FastAPI.
2. Modèle SQLite + `DonneeSourcee` + ingestion Excel/CSV avec provenance.
3. Moteur de contrôles + registre + cycle **trésorerie** + tests unitaires.
4. Écran de revue des exceptions (sans LLM encore).
5. Couche `LLMClient` + Claude (mapping de colonnes, interprétation, rédaction) + anonymisation + journalisation.
6. Génération dossier de travail + rapport, avec contrôle « aucun chiffre non sourcé ».
7. Cadrage (seuil de signification, consentement) + machine à états complète.
8. Cycles **achats-fournisseurs** puis **ventes-clients**.
9. Packaging (PyInstaller + electron-builder).

**Démontrable sans LLM dès l'étape 4** : c'est voulu, ça prouve que la fiabilité du calcul ne dépend pas du modèle.

## B.13 Critères d'acceptation du MVP

- Importer un grand livre + une balance (Excel/CSV) et obtenir un dossier de travail pour le cycle trésorerie.
- Toute valeur du dossier et du rapport est cliquable jusqu'à sa source ; la génération échoue si un chiffre non sourcé existe.
- Une balance déséquilibrée produit une exception correcte rattachée à la NEP, présentée à l'humain.
- Le LLM ne produit aucun montant ; les tests le confirment (mock LLM dans les tests de calcul).
- Aucun appel API sans consentement enregistré ; identifiants nominatifs anonymisés dans les payloads (test de la couche d'anonymisation).
- `ANTHROPIC_API_KEY` lue depuis l'environnement ; rien de sensible committé.

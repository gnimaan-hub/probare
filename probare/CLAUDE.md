# Probare — Règles non négociables

Ces règles s'appliquent à toutes les sessions, sans exception.

## Philosophie fondamentale : Calcul = Python | Interprétation = IA | Supervision = Humain

Probare est un logiciel d'audit **IA-first**. L'IA interprète automatiquement chaque exception
dès qu'elle est levée et propose une décision documentée prête à signer. L'auditeur supervise
et valide — il n'initie pas manuellement les analyses.

Trois règles d'or :
1. **Le Python calcule.** Toute arithmétique, tout rapprochement, tout ratio est en code déterministe.
2. **L'IA interprète et rédige.** Dès qu'une exception est levée, Claude l'analyse, propose des hypothèses,
   des diligences et rédige une décision à la première personne de l'auditeur.
3. **L'humain supervise et signe.** L'auditeur valide (ou modifie) en un clic. Il ne fait aucune saisie
   que son nom pour entériner la décision de l'IA.

## Règles techniques non négociables

1. **Le LLM ne calcule jamais.** Toute arithmétique est en Python. Si une valeur numérique doit
   apparaître dans le dossier, elle vient d'une `DonneeSourcee`, jamais du LLM.

2. **Pas de valeur sans provenance.** Toute donnée entrant dans un calcul est une `DonneeSourcee`
   (projet_id, fichier_source_id, localisation précise, confiance = 1.0 pour les imports directs).

3. **Clé API en variable d'environnement.** `ANTHROPIC_API_KEY` uniquement via `.env` ou l'environnement.
   Jamais en dur, jamais committée, jamais en base.

4. **Fournisseur LLM derrière une interface.** `LLMClient` (abstraction). L'implémentation Claude
   est derrière cette interface. Ne jamais appeler `anthropic.Anthropic()` hors de `llm/claude.py`.

5. **NEP en données, pas en dur.** Chaque contrôle porte un champ `nep_ref`. Les contrôles sont
   déclarés dans le registre `controls/registry.py`, pas dispersés dans le code.

6. **Tout est journalisé.** Chaque transition d'état, chaque appel LLM et chaque action humaine
   est écrit dans la piste d'audit (`journal`).

7. **Tests unitaires pour chaque contrôle.** Chaque contrôle déterministe a un test avec des
   données équilibrées/correctes ET des données déséquilibrées/incorrectes.

8. **Langue.** UI et livrables en français.

## Structure du projet

```
probare/
├── apps/desktop/     # Electron + React/TS/Tailwind
├── apps/engine/      # Python/FastAPI sidecar
│   └── probare_engine/
│       ├── controls/    # Moteur de contrôles déterministes (cerveau)
│       ├── cycles/      # Logique par cycle
│       ├── llm/         # LLMClient (abstraction) + impl Claude
│       ├── storage/     # SQLite par projet
│       └── api/         # Routes FastAPI
└── packages/         # Types partagés
```

## Modèles LLM

- `claude-sonnet-4-6` : interprétation des exceptions, rédaction des feuilles de travail (défaut)
- `claude-opus-4-8` : escalade pour jugements difficiles (déclaré, pas encore utilisé)
- `claude-haiku-4-5-20251001` : mapping de colonnes (classification simple)

## Cycles couverts

8 cycles sélectionnables au cadrage (stockés dans `cycles_couverts`, défaut : tresorerie + achats + ventes) :

1. **Trésorerie** `tresorerie` (comptes 51-54, 58)
2. **Achats-Fournisseurs** `achats` (comptes 40x + 60x-62x)
3. **Ventes-Clients** `ventes` (comptes 41x + 70x-72x)
4. **Immobilisations** `immobilisations` (comptes 20x-23x, 28x)
5. **Stocks** `stocks` (comptes 31x-35x, 37x-38x)
6. **Paie / Personnel** `paie` (comptes 42x, 43x, 64x)
7. **Impôts & Taxes** `impots` (comptes 44x, 63x)
8. **Capitaux propres** `capitaux_propres` (comptes 10x-16x)

Chaque cycle correspond à des préfixes de comptes définis dans `_cycle_prefixes()` (api/routes.py).

## Contrôles de détail (NEP 505 / NEP 530)

En plus des contrôles automatiques de chaque cycle :
- **Circularisation (NEP 505)** — confirmation externe par les tiers (clients, fournisseurs, banques).
  Tables : `circularisation`. Calcul Python dans `controls/circularisation.py`.
- **Sondages sur pièces (NEP 530)** — sondage statistique (formule de Neyman + correction population finie).
  Tables : `sondage`, `sondage_element`. Calcul Python dans `controls/sondages.py`.

Ces éléments s'intègrent aux feuilles de travail et au dossier de travail (.docx).

## États du pipeline

`cadrage → ingestion → extraction → controles → revue → generation → opinion`

- On ne passe à `generation` que si toutes les exceptions sont `tranchee`.
- `opinion` est manuel — Probare ne signe pas.

## Référentiel NEP

NEP applicables à Djibouti (autorité H2A, référentiel français) :
- NEP 230 : Documentation des travaux (dossier de travail .docx)
- NEP 300 : Planification
- NEP 315 : Connaissance de l'entité
- NEP 320 : Seuil de signification
- NEP 330 : Procédures d'audit
- NEP 450 : Anomalies relevées
- NEP 500 : Caractère probant des éléments collectés
- NEP 505 : Circularisation des tiers (confirmation externe)
- NEP 520 : Procédures analytiques
- NEP 530 : Sondages sur pièces (échantillonnage statistique)

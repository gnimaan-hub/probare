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

5. **Normes en données, pas en dur.** Chaque contrôle porte un champ `nep_ref` (référence de
   norme, rendue dans le référentiel actif). Les contrôles sont déclarés dans le registre
   `controls/registry.py`, pas dispersés dans le code. Aucune référence « NEP nnn » / « ISA nnn »
   ne doit être écrite en dur dans un texte destiné à l'utilisateur : passer par
   `normes.norme(nnn)` / `normes.reformater_refs()` (backend) ou `normeLabel()` (frontend).

6. **Tout est journalisé.** Chaque transition d'état, chaque appel LLM et chaque action humaine
   est écrit dans la piste d'audit (table `journal`, affichée « Historique » dans l'UI — ne pas
   la confondre avec le journal comptable).

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

1. **Trésorerie** (comptes 5xx) — 8 contrôles
2. **Achats-Fournisseurs** (comptes 40x + 60x-62x) — 9 contrôles
3. **Ventes-Clients** (comptes 41x + 70x-72x) — 10 contrôles

## États du pipeline

`cadrage → evaluation_ci → ingestion → planification → travaux_substantifs → revue → generation → opinion`

(`extraction` et `controles` subsistent en rétrocompatibilité pour les anciens projets.)

- Les contrôles ne s'exécutent pas avant `planification` (garde `_exiger_etat_pour_controles`).
- On ne passe à `generation` que si toutes les exceptions sont `tranchee` et que le
  cumul des anomalies non corrigées respecte le seuil (NEP 450) ou est confirmé.
- `opinion` est manuel — Probare ne signe pas.

## Référentiel de normes : ISA (défaut) ou NEP (option)

Djibouti applique les normes ISA (IAASB). Les NEP françaises en sont la transposition et
conservent la même numérotation : l'équivalence est 1:1 sur les normes utilisées ici.
Le choix du référentiel se fait dans le paramétrage Cabinet (`~/.probare/config.json`,
module `probare_engine/normes.py`) ; il est chargé UNE FOIS au démarrage du moteur
(`REFERENTIEL_ACTIF`) — un changement exige un redémarrage de l'application. Les données
stockées sous un référentiel sont re-rendues dans l'actif à la lecture (pas de migration).

Normes utilisées (numérotation commune ISA/NEP) :
- 300 : Planification
- 315 : Connaissance de l'entité
- 320 : Seuil de signification
- 330 : Procédures d'audit
- 450 : Anomalies relevées
- 500 : Caractère probant des éléments collectés
- 505 : Confirmations externes (circularisation)
- 520 : Procédures analytiques
- 530 : Sondages
- 230 : Documentation des travaux

Diligences de périphérie (module `controls/peripherie.py`, page « Diligences ») :
- 210/220 : Acceptation et maintien de la mission
- 240 : Fraude (les risques proposés par l'IA alimentent la cartographie, non validés)
- 550 : Parties liées
- 560 : Événements postérieurs
- 570 : Continuité d'exploitation — indicateurs calculés depuis la balance ;
  **conclusion signée obligatoire avant l'étape `generation`** (garde pipeline)
- 580 : Déclarations écrites (projet de lettre d'affirmation généré par l'IA)
- 260/265 : Communication à la gouvernance (projet de lettre généré par l'IA)

## Couverture risque ↔ assertion (ISA 315 révisée — M4)

Chaque contrôle du registre déclare les **assertions** qu'il couvre
(`ControleDefinition.assertions`, vocabulaire canonique `ASSERTIONS` dans
`controls/registry.py` : existence, exhaustivite, evaluation, cut_off, droits,
presentation). Le module `planning/couverture.py` croise les **risques validés**
(cycle × assertions) avec les procédures disponibles — contrôles du registre,
sondages (ISA 530), circularisations (ISA 505) — et produit une **matrice de
couverture** (`GET /planification/couverture`) qui signale les assertions à
risque non couvertes (« trous »). L'IA peut proposer une procédure
complémentaire par trou, ajoutée au programme de travail. La matrice figure
dans la note de planification exportée.

## Écritures d'ajustement (ISA 450 — module `ajustements.py`)

Une exception chiffrée peut être matérialisée en **écriture d'ajustement**
(lignes compte/débit/crédit). Cycle de vie : `proposee → acceptee_client →
passee` ou `refusee` ; `passee` est terminal (contenu gelé, suppression
interdite). Le moteur impose l'équilibre débits = crédits. L'IA peut proposer
le SCHÉMA comptable depuis une exception, mais **le montant vient toujours du
code** (incidence ou montant estimé) et le moteur re-vérifie équilibre + montant.
Chaque ligne porte une `DonneeSourcee` (localisation `ajustement:…`,
`fichier_source_id` NULL — exclue des agrégats de la balance importée).
Les écritures **passées** construisent la **balance ajustée**
(`GET /balance-ajustee`) ; les non passées chiffrent l'état récapitulatif
ISA 450 (effets résultat / capitaux propres), versé au dossier exporté.

## Seuils (ISA 320/450)

Trois seuils calculés en planification (`planning/thresholds.py`) :
seuil de signification, seuil de planification (75 %), **seuil des anomalies
manifestement insignifiantes** (défaut 3 % du seuil, plafonné à 5 %). Une exception
non critique dont le montant est ≤ seuil d'insignifiance peut être tranchée
`insignifiante` : hors cumul 450, mais journalisée et listée au dossier.
Des **seuils spécifiques par cycle** (toujours INFÉRIEURS au seuil global,
justification obligatoire) remplacent le seuil global pour les contrôles du
cycle (`_seuil_cycle` dans les routes).

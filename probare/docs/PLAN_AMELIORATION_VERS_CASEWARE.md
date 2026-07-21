# Document de travail — Plan d'amélioration de Probare

## Rapprochement du périmètre « audit financier » de Caseware

**Statut :** document de travail — version 1.0 — juillet 2026
**Périmètre :** méthodologie d'audit, analyse de données, dossier de travail et revue, production des livrables.
**Hors périmètre :** gestion de cabinet (temps, budgets, facturation), gestion qualité ISQM 1, localisations multi-pays — non demandés et sans lien direct avec l'exécution d'une mission.

---

## 1. Objet et méthode

Ce document découle de l'analyse comparative Probare / Caseware (Working Papers, CaseView, IDEA,
AnalyticsAI, solutions de contenu ISA). Il liste les chantiers permettant à Probare de couvrir
l'essentiel du périmètre **audit financier** de Caseware, **sans renoncer à son ADN** :
calcul déterministe, interprétation IA automatique, supervision humaine, provenance obligatoire
de chaque chiffre.

Chaque chantier est présenté sous forme de **fiche** avec :

- une **priorité** (nécessité de mise en place) ;
- un **indice de difficulté** de mise en œuvre ;
- une **charge** estimée ;
- les **normes** concernées et les **dépendances** entre chantiers.

### Grille de lecture

**Priorité (nécessité de mise en place)**

| Code | Signification | Critère |
|---|---|---|
| **P0** | Indispensable | Sans ce chantier, le dossier produit par Probare n'est pas défendable comme dossier d'audit complet au regard des ISA. |
| **P1** | Nécessaire | Attendu de tout logiciel d'audit sérieux ; écart le plus visible face à Caseware. |
| **P2** | Important | Gain fort de productivité ou de qualité de revue ; peut attendre un ou deux cycles de release. |
| **P3** | Différable | Rapproche de la parité complète Caseware, mais coût élevé ou valeur marginale pour la cible actuelle (cabinet mono-poste, PME). |

**Indice de difficulté de mise en œuvre (1 → 5)**

| Indice | Signification |
|---|---|
| **1** | Trivial — paramétrage ou petit calcul supplémentaire dans l'existant. |
| **2** | Simple — nouveau module borné, patrons déjà présents dans le code (nouveau contrôle, nouveau questionnaire, nouvel export). |
| **3** | Moyen — nouveau sous-système (modèle de données + API + UI), mais sans remise en cause de l'architecture. |
| **4** | Difficile — touche l'architecture (modèle de données central, moteur de rendu, interactions riches). |
| **5** | Très difficile — change des hypothèses fondatrices (mono-poste, mono-entité, SQLite local). |

**Charge estimée** : S (< 1 semaine), M (1–3 semaines), L (1–2 mois), XL (> 2 mois) — pour un développeur connaissant la base de code.

---

## 2. Vue d'ensemble des chantiers

| Réf | Chantier | Axe | Priorité | Difficulté | Charge | Dépend de |
|---|---|---|---|---|---|---|
| M1 | Écritures d'ajustement et état récapitulatif ISA 450 | Méthodologie | **P0** | 3 | M | — |
| M2 | Seuils complémentaires (anomalies insignifiantes, seuils spécifiques) | Méthodologie | **P0** | 1 | S | — |
| M3 | Couverture des ISA de périphérie de mission (210, 220, 240, 550, 560, 570, 580, 260/265) | Méthodologie | **P0** | 2 | L | — |
| M4 | Cartographie contrôles ↔ assertions (ISA 315 révisée) | Méthodologie | **P0** | 2 | M | — |
| D1 | Tests des écritures de journal — Journal Entry Testing (ISA 240) | Analyse de données | **P0** | 3 | M | M3 (volet fraude) |
| D2 | Loi de Benford | Analyse de données | **P1** | 2 | S | — |
| D3 | Échantillonnage statistique complet (MUS, stratifié, attributs) | Analyse de données | **P1** | 3 | M | — |
| D4 | Balance âgée automatique (clients / fournisseurs) | Analyse de données | **P1** | 2 | S | — |
| D5 | Import élargi (FEC, formats logiciels comptables, auto-détection renforcée) | Analyse de données | **P1** | 2 | M | — |
| M5 | Feuilles maîtresses (leadsheets) par cycle | Dossier de travail | **P1** | 3 | M | M1 |
| M6 | Roll-forward de mission N → N+1 | Méthodologie | **P1** | 2 | M | — |
| C1 | Verrouillage du dossier conforme ISA 230 (gel, hash, délai d'assemblage) | Dossier & revue | **P1** | 2 | S | — |
| C2 | Dossier de travail interactif (indexation, références croisées, tickmarks) | Dossier & revue | **P2** | 4 | L | M5 |
| C3 | Workflow de revue et sign-off (rôles préparateur / réviseur / signataire) | Dossier & revue | **P2** | 3 | M | C2 souhaitable |
| D6 | Rapprochements génériques de fichiers (jointures type IDEA) | Analyse de données | **P2** | 3 | M | D5 |
| D7 | Passage aux gros volumes (DuckDB / Polars) | Analyse de données | **P2** | 3 | M | — |
| P1 | Circularisation : envoi et suivi intégrés | Production | **P2** | 3 | M | — |
| C4 | Multi-utilisateurs et synchronisation de dossier | Dossier & revue | **P3** | 5 | XL | C3 |
| P2 | États financiers liés à la balance (bilan, compte de résultat, annexes) | Production | **P3** | 4 | XL | M1 |
| P3 | Consolidation et multi-devises | Production | **P3** | 5 | XL | P2 |
| P4 | Portail client PBC (demandes de documents) | Production | **P3** | 4 | L | — |

Lecture rapide : **les P0 rendent le dossier normativement complet ; les P1 comblent les écarts
les plus visibles face à IDEA et Working Papers ; les P2 apportent la productivité de revue ;
les P3 relèvent de la parité plateforme.**

---

## 3. Fiches détaillées

### Axe M — Méthodologie d'audit

---

#### M1 — Écritures d'ajustement et état récapitulatif ISA 450 · **P0 · difficulté 3 · charge M**

**Ce que fait Caseware :** écritures d'ajustement proposées / validées / passées, reclassements,
recalcul instantané de la balance ajustée et de toutes les feuilles en aval ; état récapitulatif
des anomalies (SUM — Summary of Unadjusted Misstatements).

**Écart Probare :** Probare saisit le *montant d'incidence* des exceptions non corrigées et
cumule contre le seuil (déjà supérieur à Caseware sur le blocage), mais ne matérialise pas
l'anomalie en **écriture** (comptes débités/crédités), ne distingue pas anomalie factuelle /
de jugement / extrapolée, et ne produit pas de **balance ajustée**.

**Travaux :**
1. Modèle `EcritureAjustement` (lignes compte/débit/crédit, statut *proposée → acceptée client →
   passée / refusée*, rattachement à une exception ou saisie libre, type factuelle/jugement/extrapolée).
2. Calcul de la **balance ajustée** = balance importée + écritures passées ; toutes les vues
   comparatives affichent brut / ajustements / ajusté.
3. État récapitulatif ISA 450 enrichi : anomalies corrigées ET non corrigées, effet sur le résultat
   et sur les capitaux propres, comparaison au seuil — intégré au dossier Word.
4. Chaque ligne d'écriture est une `DonneeSourcee` (provenance = décision d'exception signée).

**Point d'attention :** ne pas casser l'invariant « toute valeur vient d'une DonneeSourcee » ;
l'écriture d'ajustement devient elle-même une source traçable.

---

#### M2 — Seuils complémentaires · **P0 · difficulté 1 · charge S**

**Ce que fait Caseware :** formulaires ISA 320/450 complets : seuil de signification, seuil(s) de
planification, **seuil des anomalies manifestement insignifiantes** (clearly trivial, usuellement
1 à 5 % du seuil), seuils spécifiques par poste ou par catégorie d'opérations.

**Écart Probare :** seuil global + seuil de planification (75 %) uniquement.

**Travaux :**
1. Ajouter le **seuil des anomalies manifestement insignifiantes** (défaut 3 % du seuil, réglable) ;
   en dessous, une exception peut être tranchée « insignifiante » sans entrer au cumul ISA 450 —
   mais reste journalisée et listée au dossier.
2. Permettre des **seuils spécifiques par cycle ou par compte** (ex. : provisions, parties liées),
   utilisés par les contrôles du cycle concerné à la place du seuil global.
3. Documenter la justification de chaque seuil dans la note de planification (rédaction IA, comme déjà fait).

**Quick win** : le meilleur ratio valeur/effort de tout le plan.

---

#### M3 — Couverture des ISA de périphérie de mission · **P0 · difficulté 2 · charge L**

**Ce que fait Caseware :** la mission couvre TOUT le cycle de vie : acceptation et maintien,
indépendance, fraude, parties liées, continuité d'exploitation, événements postérieurs,
déclarations écrites, communication avec la gouvernance — sous forme de questionnaires,
checklists et modèles de lettres.

**Écart Probare :** Probare couvre 230/300/315/320/330/450/500/505/520/530 — le « cœur »
substantif — mais un dossier réel exige aussi la périphérie.

**Travaux** (le patron QCI existant — questionnaire + score calculé + synthèse IA — se réplique) :
1. **ISA 210/220 — Acceptation et maintien** : questionnaire au cadrage (indépendance, compétence,
   intégrité du client, honoraires) ; blocage doux si conclusion défavorable non justifiée.
2. **ISA 240 — Fraude** : questionnaire triangle de la fraude + entretiens obligatoires tracés +
   lien vers les contrôles data (D1, montants ronds, cut-off déjà en place) ; synthèse IA des
   facteurs de risque de fraude injectée dans la cartographie des risques existante.
3. **ISA 550 — Parties liées** : registre des parties liées (dossier permanent), contrôle
   déterministe signalant les mouvements avec ces tiers, questionnaire de diligences.
4. **ISA 560 — Événements postérieurs** : checklist datée entre clôture et signature + revue des
   écritures post-clôture si le grand livre N+1 partiel est importé.
5. **ISA 570 — Continuité d'exploitation** : contrôles déterministes (capitaux propres < moitié du
   capital — déjà partiellement couvert par CP-SOLDE-ANORMAL —, fonds de roulement négatif, ratios
   de structure), questionnaire, conclusion documentée obligatoire avant l'étape `generation`.
6. **ISA 580 — Déclarations écrites** : génération IA de la lettre d'affirmation à partir du
   contenu réel du dossier (exceptions tranchées, ajustements refusés) ; statut envoyée/signée.
7. **ISA 260/265 — Communications à la gouvernance** : génération IA de la lettre de faiblesses
   du contrôle interne à partir du QCI et des exceptions ; journal des communications.

**Découpage conseillé :** livrer par norme, dans l'ordre 240 → 570 → 580 → 560 → 210/220 → 550 → 260/265.

---

#### M4 — Cartographie contrôles ↔ assertions (ISA 315 révisée) · **P0 · difficulté 2 · charge M**

**Ce que fait Caseware :** chaque procédure est reliée aux **assertions** (existence, exhaustivité,
exactitude, séparation des exercices, classement, droits et obligations, valorisation) ; la
couverture des risques par assertion est visible et pilote le programme de travail.

**Écart Probare :** les risques et le programme existent, mais les 52 contrôles ne déclarent pas
les assertions qu'ils couvrent ; impossible de démontrer qu'un risque « exhaustivité des ventes »
est couvert.

**Travaux :**
1. Ajouter `assertions: list[str]` à `ControleDefinition` dans `controls/registry.py` et renseigner
   les 52 contrôles (travail métier, pas technique).
2. Étendre la cartographie des risques : chaque risque validé porte cycle × assertion(s).
3. **Matrice de couverture** risque → assertion → contrôles/sondages/circularisations dans l'UI
   Planification et dans la note de planification ; l'IA signale les assertions à risque non couvertes
   et propose des procédures complémentaires au programme de travail.

---

#### M5 — Feuilles maîtresses (leadsheets) par cycle · **P1 · difficulté 3 · charge M**

**Ce que fait Caseware :** pour chaque cycle, une feuille maîtresse agrège les comptes,
affiche N / ajustements / N ajusté / N-1 / variation %, sert de pivot de navigation vers les travaux.

**Écart Probare :** les données existent (balance, variations, contrôles par cycle) mais il n'y a
pas de vue « feuille maîtresse » ; le dossier Word est généré sans ce pivot standard.

**Travaux :**
1. Vue UI par cycle : tableau des comptes du cycle (préfixes déjà définis par cycle), colonnes
   N brut / ajustements (M1) / N ajusté / N-1 / variation, total du cycle.
2. Rattacher visuellement à chaque ligne : exceptions ouvertes, contrôles exécutés, sondages,
   circularisations du compte.
3. Export de chaque feuille maîtresse dans le dossier Word (une section par cycle, avant la
   feuille de travail rédigée par l'IA).

---

#### M6 — Roll-forward de mission N → N+1 · **P1 · difficulté 2 · charge M**

**Ce que fait Caseware :** création de la mission N+1 en un clic : structure, mapping, paramètres,
soldes N devenant les comparatifs N-1.

**Écart Probare :** chaque mission repart de zéro ; seuls les dossiers permanents portent le pluriannuel.

**Travaux :**
1. Action « Créer la mission N+1 » depuis une mission archivée : reprend client, cycles, fiche
   entité, registre des parties liées, paramètres de seuil (à revalider), QCI pré-rempli avec
   les réponses N (marquées « à confirmer »).
2. La balance N validée devient automatiquement la balance comparative N-1 de la nouvelle mission
   (avec provenance pointant vers la mission d'origine).
3. Report des points d'attention : exceptions non corrigées N, faiblesses de CI, risques —
   l'IA rédige une note « points ouverts de l'exercice précédent ».

---

### Axe D — Analyse de données (rapprocher IDEA / AnalyticsAI)

---

#### D1 — Tests des écritures de journal (Journal Entry Testing, ISA 240) · **P0 · difficulté 3 · charge M**

**Ce que fait Caseware (IDEA/AnalyticsAI) :** batterie standard sur le grand livre complet :
écritures de week-end / jours fériés / nuit, écritures manuelles vs automatiques, utilisateurs
inhabituels, contreparties inhabituelles (ex. : vente ↔ trésorerie sans client), écritures juste
sous le seuil, top-side entries, écritures de clôture tardives, scoring de risque par écriture.

**Écart Probare :** montants ronds et cut-off existent par cycle, mais il n'y a pas de module JET
transversal sur l'ensemble du grand livre — exigence ISA 240 sur **toute** mission.

**Travaux :**
1. Nouveau groupe de contrôles transversal `journal_entry_testing` (hors cycles) dans le registre :
   - écritures datées week-end / hors heures (si l'horodatage existe dans le fichier) ;
   - écritures dans les N derniers jours avec contrepartie inhabituelle (table de correspondances
     attendues entre classes de comptes) ;
   - écritures d'un montant juste sous le seuil (90–100 % du seuil) ;
   - déséquilibres par pièce (débits ≠ crédits au sein d'un même numéro de pièce) ;
   - libellés vides, génériques (« divers », « od ») ou dupliqués ;
   - écritures sans numéro de pièce.
2. **Score de risque par écriture** (somme pondérée déterministe des signaux — pas de LLM) ;
   les X écritures les mieux scorées partent en sélection ciblée, pointables comme un sondage (module ISA 530 existant réutilisé).
3. Interprétation IA de la population signalée (patron exceptions existant).

---

#### D2 — Loi de Benford · **P1 · difficulté 2 · charge S**

**Ce que fait Caseware (IDEA) :** analyse des premier / deux premiers chiffres sur toute
population, écart au modèle de Benford, χ² ou MAD, zoom sur les classes déviantes.

**Travaux :**
1. Contrôle `BENFORD` exécutable sur grand livre complet ou par cycle (population ≥ 300 écritures
   pour être significatif — en dessous, contrôle « non exécuté » avec motif, mécanisme déjà en place).
2. Calcul déterministe (distribution observée vs théorique, MAD avec bornes de Nigrini), graphique
   dans l'UI, liste des écritures des classes déviantes.
3. Exception levée si déviation forte ; interprétation IA standard.

---

#### D3 — Échantillonnage statistique complet · **P1 · difficulté 3 · charge M**

**Ce que fait Caseware (IDEA) :** MUS (probabilité proportionnelle à la taille) avec évaluation
des erreurs (facteurs de confiance, basic precision, projection), stratification,
échantillonnage par attributs, aléatoire et systématique.

**Écart Probare :** tirage aléatoire simple reproductible + extrapolation monétaire. Correct,
mais non stratifié et non MUS — la limite est même documentée dans le guide utilisateur.

**Travaux :**
1. **MUS** : tirage par unités monétaires (intervalle = population / taille), les éléments ≥
   intervalle deviennent une strate « éléments clés » examinés à 100 % ; évaluation par facteurs
   de confiance Poisson (projection + basic precision + incremental allowance).
2. **Stratification** : découpage en strates par montant (bornes automatiques ou manuelles),
   allocation de l'échantillon par strate, projection par strate.
3. **Attributs** : taille pour test de conformité du CI (niveau de confiance, taux d'écart
   tolérable/attendu) — ce module permettrait ensuite d'alléger les travaux substantifs quand le
   CI est testé efficace, levée propre de la restriction actuelle (le QCI déclaratif ne le permet pas, conformément à ISA 330).
4. Conserver : graine enregistrée, reproductibilité, conclusion IA.

---

#### D4 — Balance âgée automatique · **P1 · difficulté 2 · charge S**

**Ce que fait Caseware (IDEA) :** aging clients/fournisseurs par tranches (0-30, 31-60, 61-90, 90+),
base des tests de dépréciation.

**Écart Probare :** le contrôle VENTE-CREANCES-ECHUES détecte les créances > 90 jours, mais il
n'y a pas de balance âgée complète ni d'équivalent fournisseurs.

**Travaux :**
1. Construction de la balance âgée par tiers (41x et 40x) par lettrage approché
   (rapprochement facture/règlement par montant et chronologie — heuristique documentée).
2. Tranches paramétrables, totaux par tranche, export au dossier.
3. Lien avec la provision : l'IA propose une estimation de dépréciation à partir de la balance
   âgée (calcul déterministe des assiettes, taux proposés à valider par l'auditeur).

---

#### D5 — Import élargi et auto-détection renforcée · **P1 · difficulté 2 · charge M**

**Ce que fait Caseware :** connecteurs vers la plupart des logiciels comptables + import
générique très robuste.

**Travaux (adaptés à la cible Djibouti / zone franc / France) :**
1. **Parseur FEC natif** (format normalisé français — répandu aussi chez les filiales) : mapping
   automatique complet sans IA, y compris JournalCode/EcritureDate/PieceRef — alimente directement D1.
2. Profils d'import mémorisés par client (le mapping validé en N est proposé en N+1 — synergie M6).
3. Tolérance accrue : encodages, séparateurs, formats de montants (1.234,56 / 1 234,56), balances
   sur plusieurs blocs.

---

#### D6 — Rapprochements génériques de fichiers · **P2 · difficulté 3 · charge M**

**Ce que fait Caseware (IDEA) :** jointures entre fichiers quelconques (facturier ↔ GL,
paie ↔ registre RH, stock physique ↔ stock comptable), avec correspondances exactes ou approchées.

**Travaux :**
1. Module « Rapprochement » : deux sources importées, choix des clés (exactes ou approchées :
   montant ± tolérance, date ± n jours), résultat en trois listes — appariés / présents seulement
   à gauche / seulement à droite.
2. Chaque non-apparié significatif devient une exception standard (interprétation IA).
3. L'IA propose les clés de jointure probables (classification de colonnes, patron Haiku existant) ;
   le calcul du rapprochement reste 100 % déterministe.

---

#### D7 — Passage aux gros volumes · **P2 · difficulté 3 · charge M**

**Ce que fait Caseware (IDEA) :** millions de lignes sans broncher.

**Écart Probare :** SQLite + pandas conviennent aux PME ; un grand livre de plusieurs millions de
lignes dégradera l'expérience et JET (D1) est justement le module le plus volumineux.

**Travaux :**
1. Benchmarks sur GL synthétiques (1 M, 5 M, 20 M lignes) pour objectiver le besoin réel.
2. Introduire **DuckDB** (ou Polars) comme moteur de calcul des contrôles sur les tables
   volumineuses, en gardant SQLite comme stockage du dossier (métadonnées, exceptions, journal).
3. Pagination/virtualisation des tableaux côté UI.

**Note :** à ne lancer qu'après D1/D2/D6 — optimiser avant d'avoir les usages serait prématuré.

---

### Axe C — Dossier de travail et revue

---

#### C1 — Verrouillage du dossier conforme ISA 230 · **P1 · difficulté 2 · charge S**

**Ce que fait Caseware :** gel du dossier à l'issue du délai d'assemblage (60 jours après le
rapport), toute modification ultérieure documentée, protection d'intégrité.

**Écart Probare :** l'archivage lecture seule existe, mais sans notion de date de rapport, de
délai d'assemblage, ni de preuve d'intégrité.

**Travaux :**
1. Champ **date de signature du rapport** sur la mission ; compte à rebours des 60 jours affiché ;
   rappel à l'approche de l'échéance.
2. Au verrouillage : **empreinte SHA-256 de la base et des fichiers importés**, enregistrée dans le
   journal et dans l'export ZIP — preuve d'intégrité vérifiable à la restauration.
3. Déverrouillage exceptionnel : motif obligatoire, journalisé, mention au dossier (exigence ISA 230).

---

#### C2 — Dossier de travail interactif · **P2 · difficulté 4 · charge L**

**Ce que fait Caseware :** le dossier est un espace navigable : index normalisé des feuilles
(A = acceptation, B = planification…), références croisées cliquables, tickmarks, statut par feuille.

**Écart Probare :** la navigation actuelle est le pipeline par étapes ; le « dossier » n'existe
qu'au moment de l'export Word.

**Travaux :**
1. **Index de dossier** : arborescence normalisée regroupant tout ce qui existe déjà (note de
   planification, QCI, feuilles maîtresses, contrôles, exceptions, sondages, circularisations,
   lettres) avec cotation automatique (A-1, C-2.3…).
2. Références croisées : toute valeur affichée pointe vers sa `DonneeSourcee` (la provenance
   existe déjà — il s'agit de la rendre navigable) et les documents se citent par cote.
3. Tickmarks et annotations de l'auditeur sur chaque document (persistés, exportés).
4. L'export Word devient une **projection de l'index** (ordre et cotes identiques à l'écran).

**Point d'attention :** c'est le chantier UI le plus lourd ; le découper (index → cotes →
annotations → références croisées).

---

#### C3 — Workflow de revue et sign-off · **P2 · difficulté 3 · charge M**

**Ce que fait Caseware :** notes de revue adressées, réponses, statuts de préparation/revue par
feuille, signatures à plusieurs niveaux, tableau de bord d'avancement.

**Écart Probare :** mono-utilisateur, signature déclarative unique.

**Travaux (version mono-poste d'abord — sans attendre C4) :**
1. **Rôles nominatifs** sur la mission (préparateur, réviseur, signataire) — toujours déclaratifs
   (pas de comptes), mais chaque action porte son rôle et la piste d'audit les distingue.
2. **Notes de revue** : sur toute pièce du dossier, une note « à traiter » adressée, avec réponse
   et clôture ; l'étape `generation` exige zéro note ouverte.
3. **Sign-off à deux niveaux** sur les éléments sensibles (seuil, cartographie des risques,
   exceptions critiques, dossier final) : préparé par X / revu par Y, horodaté.
4. Tableau de bord d'avancement par cycle et par étape.

---

#### C4 — Multi-utilisateurs et synchronisation · **P3 · difficulté 5 · charge XL**

**Ce que fait Caseware :** travail simultané, SmartSync (hors ligne + fusion), droits fins.

**Pourquoi P3 :** contredit l'hypothèse fondatrice actuelle (SQLite local mono-poste) et la cible
MVP (petit cabinet). À instruire seulement si la cible commerciale évolue vers des équipes.

**Options à étudier le moment venu :** (a) serveur central léger (PostgreSQL + API existante
déployée) ; (b) partage de dossier à tour de rôle avec verrou d'édition (checkout/checkin sur un
partage de fichiers) — l'option (b) est très inférieure mais atteignable, l'option (a) est la vraie
réponse mais reclasse Probare en client-serveur (authentification, droits, migration).

---

### Axe P — Production et écosystème

---

#### P1 — Circularisation : envoi et suivi intégrés · **P2 · difficulté 3 · charge M**

**Ce que fait Caseware (Validate) :** envoi électronique réel des demandes de confirmation,
réponses collectées sur plateforme, traçabilité complète.

**Écart Probare :** génération des lettres + suivi manuel (envoyé/relancé/reçu saisi à la main).

**Travaux (sans plateforme tierce — irréaliste à l'échelle de Probare) :**
1. **Envoi email intégré** (SMTP du cabinet paramétré dans la fiche Cabinet) : lettre PDF jointe,
   copie archivée au dossier, date d'envoi automatique — supprime la saisie manuelle « envoyé ».
2. Relances programmées (proposées à J+15, envoyées après confirmation de l'auditeur).
3. Adresse de réponse dédiée par mission en objet normalisé pour rattacher les réponses ; à
   réception (import manuel du PDF/email), extraction IA du solde confirmé via le module Dossier
   brut existant, écart calculé comme aujourd'hui.

---

#### P2 — États financiers liés à la balance · **P3 · difficulté 4 · charge XL**

**Ce que fait Caseware (CaseView/Financials) :** états financiers complets et annexes générés
depuis la balance mappée, recalculés à chaque ajustement.

**Pourquoi P3 :** Probare audite des comptes établis par ailleurs ; produire les états financiers
est le métier de l'expert-comptable, pas de l'auditeur. La valeur pour la mission d'audit est
la **comparaison** états présentés / balance auditée, pas la production.

**Alternative recommandée (difficulté 2, charge M — à faire en P1 si M1 est livré) :**
un contrôle « cadrage états financiers » : l'auditeur importe le bilan/compte de résultat présentés
(ou les saisit par rubrique), Probare mappe la balance ajustée sur les rubriques et signale tout
écart — c'est la diligence d'audit réelle, à 10 % du coût de CaseView.

---

#### P3 — Consolidation et multi-devises · **P3 · difficulté 5 · charge XL**

**Ce que fait Caseware :** consolidation multi-entités, conversion multi-devises.

**Pourquoi P3 :** hors cible PME mono-entité actuelle. N'instruire qu'en cas de demande client
avérée (groupes locaux). Prérequis : P2, M1, et une refonte du modèle « une mission = une entité ».

---

#### P4 — Portail client PBC · **P3 · difficulté 4 · charge L**

**Ce que fait Caseware (Cloud) :** liste de demandes au client, dépôt de fichiers, relances,
suivi d'avancement.

**Écart Probare :** checklist interne des documents attendus, sans interaction client.

**Version intermédiaire raisonnable (difficulté 2, charge S) :** générer depuis la checklist un
**email de demande de pièces** (IA) avec relances tracées — sans portail. Le portail web
complet suppose un composant hébergé et change le modèle de déploiement : à coupler avec C4 si un
jour la plateforme devient client-serveur.

---

## 4. Feuille de route proposée

**Phase 1 — « Dossier normativement complet » (≈ 1 trimestre)**
M2 (quick win) → M1 → M4 → D1 → M3 (livré par norme : 240, 570, 580 d'abord).
*Sortie de phase : un dossier Probare tient face à un contrôle qualité sur les exigences ISA
centrales, y compris fraude, continuité et déclarations écrites.*

**Phase 2 — « Parité data & travail annuel » (≈ 1 trimestre)**
D2 → D4 → D3 → D5 → M6 → C1 → M5 → fin de M3 (210/220, 550, 560, 260/265) → alternative P2
(cadrage états financiers).
*Sortie de phase : l'essentiel de ce qu'un utilisateur IDEA attend au quotidien, plus le
roll-forward et le verrouillage conformes.*

**Phase 3 — « Productivité de revue » (≈ 1 trimestre)**
C3 → C2 → D6 → P1 → D7 → version intermédiaire P4.
*Sortie de phase : le dossier se navigue, se revoit et se signe comme dans Working Papers.*

**Phase 4 — « Parité plateforme » (non planifiée — décision produit préalable)**
C4, P2 complet, P3, P4 complet. À n'ouvrir que si la cible commerciale dépasse le cabinet mono-poste.

### Quick wins (à glisser dès que possible, < 1 semaine chacun)

| Réf | Quick win | Difficulté |
|---|---|---|
| M2 | Seuil des anomalies manifestement insignifiantes | 1 |
| D2 | Loi de Benford | 2 |
| D4 | Balance âgée | 2 |
| C1 | Hash d'intégrité + délai d'assemblage 60 jours | 2 |
| P4bis | Email de demande de pièces généré depuis la checklist | 2 |

---

## 5. Ce qu'il ne faut PAS copier de Caseware

1. **Le modèle « formulaires à remplir ».** La force de Probare est l'inversion : le moteur
   exécute, l'IA instruit, l'humain signe. Chaque chantier ci-dessus doit être livré dans ce
   modèle (ex. : M3 = questionnaires *dépouillés par l'IA*, pas des formulaires morts).
2. **La production des états financiers (CaseView complet).** Métier d'expert-comptable, coût XL,
   valeur d'audit faible — préférer le contrôle de cadrage (alternative P2).
3. **La plateforme cloud obligatoire.** La confidentialité locale (SQLite + pseudonymisation +
   consentement) est un argument commercial face à Caseware — ne l'abandonner que sur preuve de
   demande (C4/P4).
4. **L'IA « assistant sur demande » (AiDA).** Probare est déjà au-delà : interprétation
   automatique, garde-fous durs, provenance obligatoire. C'est le différenciateur à protéger dans
   chaque nouveau module : *aucun chantier de ce plan ne doit introduire un chiffre qui ne soit pas
   une `DonneeSourcee`, ni un texte IA non signé par l'auditeur.*

---

*Document de travail interne — à réviser après chaque phase. Les charges sont indicatives pour un
développeur connaissant la base de code ; les priorités P0 reflètent les exigences des ISA pour un
dossier complet, pas une urgence commerciale.*

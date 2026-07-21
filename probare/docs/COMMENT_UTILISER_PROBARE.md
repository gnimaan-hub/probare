# Comment utiliser Probare

**Guide de première utilisation — assistant d'audit IA-first (référentiel ISA — NEP en option)**

---

## 1. Ce qu'est Probare (et ce qu'il n'est pas)

Probare vous accompagne sur toute une mission d'audit contractuel, du cadrage à la génération du dossier de travail. Il repose sur trois règles d'or :

1. **Le logiciel calcule.** Tous les chiffres (équilibres, écarts, ratios, seuils, cumuls) sont produits par du code déterministe. Chaque valeur est traçable jusqu'à sa cellule d'origine dans vos fichiers importés.
2. **L'IA interprète et rédige.** Dès qu'une exception est levée, l'IA l'explique, propose des hypothèses, des diligences et un **projet** de décision. Elle ne produit jamais un montant qui ne vient pas du moteur de calcul.
3. **Vous supervisez et signez.** Aucune décision n'entre au dossier sans votre validation nominative. **Probare ne formule jamais l'opinion d'audit** : elle reste de votre responsabilité exclusive.

Chaque action (import, contrôle, appel IA, décision, changement d'étape) est inscrite dans l'**Historique**, la piste d'audit de la mission (ISA 230).

---

## 2. Avant la première utilisation

### 2.1 Clé API Claude (fonctions IA)

Les fonctions IA nécessitent une clé API Anthropic :

1. Copiez le fichier `.env.example` en `.env` à la racine de Probare.
2. Renseignez `ANTHROPIC_API_KEY=sk-ant-...` (votre clé).
3. Redémarrez l'application.

Sans clé, Probare fonctionne en **mode dégradé** : tous les calculs et contrôles restent disponibles, mais sans interprétation ni rédaction automatique.

### 2.2 Consentement du client (obligatoire pour l'IA)

Aucune donnée n'est envoyée à l'IA sans que la case **« Consentement client »** soit cochée dans le cadrage de la mission. Obtenez l'accord écrit de votre client avant de l'activer. Le nom du client et son NIF sont pseudonymisés avant tout envoi ; la table de correspondance ne quitte jamais votre machine.

### 2.3 Fiche du cabinet

Ouvrez **Cabinet** (bas de la barre latérale) et renseignez le nom du cabinet, l'adresse, le numéro d'agrément et le responsable signataire. Ces informations figurent sur les documents générés.

### 2.4 Dossiers permanents (recommandé)

Depuis le **Tableau de bord → Dossiers permanents**, créez une fiche par client (nom, NIF, secteur, dirigeants) et rattachez-y les documents pluriannuels : statuts, PV d'AG, contrats, rapports antérieurs. Vous pourrez lier chaque mission à un client existant.

### 2.5 Référentiel de normes : ISA (défaut) ou NEP

Probare référence chaque contrôle, exception et livrable à une norme d'audit.
Le référentiel par défaut est **ISA** (normes internationales de l'IAASB, applicables
à Djibouti). Les cabinets travaillant sous référentiel français peuvent basculer en
**NEP** dans **Cabinet → Référentiel de normes d'audit**. Les NEP étant la transposition
des ISA avec la même numérotation, ce choix ne change rien au processus d'audit —
uniquement les références affichées et imprimées.

> ⚠️ **Le changement de référentiel nécessite un redémarrage de l'application** pour
> s'appliquer partout de façon cohérente. La session en cours conserve le référentiel
> chargé au démarrage ; ce guide utilise les références ISA.

---

## 3. Créer une mission

Sur le **Tableau de bord**, cliquez **Nouvelle mission** et renseignez :

- **Nom de la mission** et **exercice** audité (ex. « 2025 ») ;
- **Client** et **NIF** (ou liez un client des dossiers permanents) ;
- **Cycles couverts** : trésorerie, achats-fournisseurs, ventes-clients, immobilisations, stocks, paie, impôts, capitaux propres. Ne cochez que ce qui entre dans votre périmètre — la liste des documents attendus et les contrôles en découlent ;
- **Consentement client** pour l'IA (voir § 2.2).

La barre latérale affiche alors les étapes de la mission et votre progression. Les étapes se déverrouillent au fur et à mesure ; vous pouvez toujours **revenir à une étape antérieure** (le retour est journalisé).

---

## 4. Le déroulé d'une mission, étape par étape

### Étape 1 — Cadrage

Vérifiez les paramètres de la mission (client, exercice, cycles, nature de la mission). Le seuil de signification peut être saisi ici, mais il est préférable de le **calculer** à l'étape Planification (§ Étape 4). Passez ensuite à l'étape suivante.

### Étape 2 — Contrôle interne (ISA 315)

Pour chaque cycle, répondez au **Questionnaire de Contrôle Interne** (oui / non / N.A., commentaires libres). À partir de 3 réponses, lancez l'**évaluation** : le score est calculé par le logiciel, l'IA rédige la synthèse (forces, faiblesses, recommandations).

> **Incidence sur les travaux :** un contrôle interne jugé **à risque élevé** durcit automatiquement les seuils de détection des contrôles (vous verrez plus d'exceptions). Un bon score ne les allège jamais : le questionnaire étant déclaratif, Probare n'autorise pas de réduction des travaux substantifs sans test d'efficacité du contrôle interne (ISA 330).

### Étape 3 — Ingestion des données

Importez les fichiers comptables de l'exercice :

| Document | Format | Nécessaire pour |
|---|---|---|
| **Balance générale N** | Excel / CSV | Quasi tous les contrôles, calcul du seuil |
| **Grand livre N** | Excel / CSV | Contrôles de mouvements (séquences, doublons, cut-off…) |
| **Relevé bancaire** | Excel / CSV | Rapprochement bancaire |
| **Balance N-1** | Excel / CSV | Variations et procédures analytiques |

Points pratiques :

- La **checklist des documents attendus** (selon vos cycles) vous indique ce qui manque.
- Le mapping des colonnes (compte, libellé, débit, crédit, solde, date, n° pièce) est **détecté automatiquement** ; l'IA identifie la nature de chaque document importé.
- Pour un classeur Excel multi-onglets, Probare analyse chaque onglet et vous propose d'importer ceux qui sont pertinents, chacun comme document distinct.
- Un fichier strictement identique déjà importé est **refusé** (anti-doublon) — supprimez l'ancien import pour réimporter.
- Les PDF, scans et documents Word passent par le module **Dossier brut** : l'IA les catalogue, en extrait les données comptables, les **vérifie ligne à ligne**, puis vous les importez comme source de données à part entière.

### Étape 4 — Planification (ISA 300)

C'est l'étape la plus structurante. Dans l'ordre :

1. **Fiche entité** : forme juridique, activités, marchés, dirigeants, système d'information, facteurs de risque.
2. **Variations N/N-1** : choisissez le fichier N et le fichier N-1 ; le logiciel calcule toutes les variations par compte et signale les significatives. L'IA peut ensuite les interpréter (zones de risque).
3. **Seuils (ISA 320 / 450)** : choisissez l'agrégat de référence — total bilan (1 %), chiffre d'affaires (1,5 %), résultat net (5 %) — et validez. Trois seuils sont calculés et appliqués à toute la mission : le seuil de signification, le seuil de planification (75 %) et le **seuil des anomalies manifestement insignifiantes** (3 % du seuil par défaut, réglable jusqu'à 5 %) — en dessous de ce dernier, une exception non critique peut être écartée du cumul ISA 450 tout en restant listée au dossier. Vous pouvez aussi définir des **seuils spécifiques par cycle** (toujours inférieurs au seuil global, justification obligatoire) pour durcir la détection sur une zone sensible. *Le total bilan est calculé sur les seuls comptes de bilan (classes 1 à 5).*
4. **Cartographie des risques (ISA 315)** : l'IA propose des risques à partir de la fiche entité et des variations ; ajoutez les vôtres, puis **validez** ceux que vous retenez — seuls les risques validés comptent.
5. **Programme de travail** : généré par l'IA à partir des risques validés et du registre des contrôles ; ajustez les priorités et le périmètre.
6. **Couverture des risques par assertion (ISA 315 révisée)** : la matrice croise chaque risque validé (cycle × assertion) avec les procédures qui le couvrent — contrôles déterministes, sondages, circularisations. Une assertion à risque **sans aucune procédure** apparaît en rouge : c'est un trou à combler. Vous pouvez demander à l'IA de **proposer une procédure complémentaire** pour chaque trou — elle est ajoutée à votre programme de travail. La matrice figure dans la note de planification.
7. **Note de planification** : générez la synthèse et téléchargez la note au format Word pour le dossier.

> ⚠️ **Le passage aux travaux substantifs est bloqué tant que le seuil de signification n'est pas défini.**

### Étape 5 — Travaux substantifs (ISA 330 / 500 / 505 / 530)

**a) Contrôles déterministes.** Lancez les contrôles cycle par cycle. Pour chaque cycle, Probare exécute sa batterie (équilibre de balance, cohérence grand livre/balance, séquences de pièces, soldes anormaux, doublons de factures, concentration, avoirs, montants ronds, cut-off, variations, amortissements, TVA, paie…). Chaque résultat est soit **OK**, soit une **exception** ; les contrôles qui n'ont pas pu s'exécuter (document manquant, seuil absent) sont **documentés avec leur motif** et figureront au dossier. Les contrôles ne peuvent pas être lancés avant la fin de la planification (le moteur le refuse).

**b) Circularisation (ISA 505).** Probare propose les tiers à circulariser (plus gros soldes clients/fournisseurs). Pour chaque tiers :
1. Générez la lettre de confirmation (IA) — *générer n'est pas envoyer* ;
2. Après envoi réel, marquez le dossier **« envoyé »** avec la date ;
3. Sans réponse, tracez la **relance** ; à réception, saisissez le solde confirmé — l'écart est calculé et comparé au seuil de planification de la mission ;
4. Un dossier resté **sans réponse** ne peut être clos qu'après documentation des **procédures alternatives** mises en œuvre.

**c) Sondages (ISA 530).** Créez un sondage par cycle : le logiciel calcule la taille d'échantillon (niveau de confiance, taux d'erreur toléré), tire l'échantillon de façon **reproductible** (graine enregistrée), et vous pointez chaque pièce (conforme / anomalie + montant). À la conclusion, l'erreur est **projetée sur la population** par extrapolation monétaire et l'IA rédige la conclusion du sondage.

### Les Diligences de périphérie (ISA 210/220, 240, 550, 560, 570, 580, 260/265)

L'écran **Diligences** (accessible à toute étape) couvre les diligences transversales de la mission : acceptation et maintien, fraude, parties liées, événements postérieurs, continuité d'exploitation, déclarations écrites et communication à la gouvernance. Pour chacune :

1. Répondez au questionnaire (oui / non / N.A., commentaires) — le score est calculé par le logiciel ;
2. Lancez l'**évaluation** (3 réponses minimum) : l'IA rédige la synthèse, les points d'attention, les diligences à mener et un projet de conclusion au conditionnel ;
3. Réalisez les diligences puis **signez la conclusion** de votre nom.

Points particuliers :

- **Fraude (ISA 240)** : les risques identifiés par l'IA sont versés à la cartographie des risques — validez-les à l'étape Planification.
- **Continuité (ISA 570)** : les indicateurs financiers (capitaux propres, résultat, fonds de roulement, trésorerie) sont calculés depuis la balance importée. **La conclusion signée est obligatoire avant la génération du dossier.**
- **Déclarations écrites (ISA 580)** et **gouvernance (ISA 260/265)** : l'IA rédige un projet de lettre à partir du contenu réel du dossier (anomalies tranchées, faiblesses du contrôle interne). *Générer n'est pas envoyer* — relisez et adaptez avant tout envoi.

L'état de chaque diligence (score, synthèse, conclusion signée) est versé au dossier de travail exporté.

### Étape 6 — Exceptions (ISA 450) : le cœur de votre travail

Chaque exception levée est **automatiquement interprétée par l'IA** (si activée) : explication, hypothèses de cause, diligences à mener, et un **projet de décision rédigé au conditionnel** — il ne prétend jamais que des vérifications ont été faites : c'est à vous de les faire.

Pour trancher une exception :

1. Réalisez les diligences proposées (ou les vôtres) ;
2. Cliquez **Valider** (décision IA telle quelle) ou **Modifier** (votre propre rédaction, 20 caractères minimum) ;
3. Choisissez la **nature de la résolution** — c'est essentiel :
   - **Corrigée par le client** : l'anomalie a été corrigée, aucune incidence résiduelle ;
   - **Sans incidence** : explication obtenue, aucune anomalie avérée ;
   - **Non corrigée** : l'anomalie demeure — saisissez son **montant d'incidence** ;
   - **Manifestement insignifiante** (si le seuil d'insignifiance est défini et que l'exception n'est pas critique) : montant dérisoire, écarté du cumul ISA 450 mais **listé au dossier** — saisissez son montant, qui doit rester sous le seuil d'insignifiance ;
4. Signez de votre nom. Les exceptions **critiques** exigent en plus la saisie du mot VALIDER.

> **Cumul ISA 450 :** Probare additionne les montants des anomalies **non corrigées** et les compare au seuil de signification. Si le cumul dépasse le seuil, le passage en génération est **bloqué** : soit vous enregistrez les corrections du client, soit vous confirmez explicitement le dépassement — en sachant qu'il devra se traduire dans l'opinion (réserve ou refus). Cette confirmation est journalisée.

### Les écritures d'ajustement (ISA 450)

Une anomalie chiffrée peut être **matérialisée en écriture comptable** à proposer au client, depuis l'écran **Ajustements** (ou directement depuis une exception tranchée « non corrigée » via le lien *Proposer l'écriture d'ajustement*).

1. **Créer l'écriture** : saisissez les lignes (compte, débit, crédit) — le logiciel refuse toute écriture déséquilibrée. Depuis une exception, l'**IA propose le schéma comptable** (comptes et sens) mais le **montant vient toujours du moteur** (incidence saisie ou écart calculé) et il est re-vérifié.
2. **Suivre son cycle de vie** : *proposée au client* → *acceptée* → **passée** (le client l'a comptabilisée) ou *refusée*. Une écriture passée est définitive : contenu gelé, suppression impossible.
3. **Lire les effets** : chaque écriture affiche son effet sur le **résultat** et sur les **capitaux propres**, calculés par le logiciel. L'état récapitulatif en haut de l'écran cumule les effets des écritures **non passées** — c'est le chiffrage comptable de vos anomalies subsistantes.
4. **Consulter la balance ajustée** : balance importée + écritures passées, compte par compte (brut / ajustement / ajusté), avec provenance conservée.

À la clôture d'une écriture **passée**, pensez à trancher l'exception liée comme « corrigée par le client » : le cumul ISA 450 diminuera d'autant. L'état récapitulatif des ajustements et la balance ajustée figurent dans le dossier de travail exporté.

### Étape 7 — Rapport et génération

Une fois toutes les exceptions tranchées :

1. Générez les **feuilles de travail** par cycle (rédaction IA structurée : objectif, procédures, résultats, anomalies, conclusion). Tout montant rédigé par l'IA est vérifié contre les valeurs calculées ; les montants non tracés sont signalés en « avertissements de traçabilité » ;
2. Exportez le **dossier de travail** (Word) : résultats des contrôles, exceptions et leur traitement, **synthèse des anomalies ISA 450**, contrôles non exécutés et motifs, feuilles de travail ;
3. Exportez le **tableau des exceptions** (Excel) si besoin.

L'export est **bloqué** s'il subsiste un chiffre sans provenance : c'est votre garantie qu'aucun montant inventé n'entre au dossier.

### Étape 8 — Opinion

L'opinion (certification sans réserve, avec réserve, refus) se formule **hors de Probare**, sur la base du dossier généré — en particulier de la synthèse ISA 450. Probare ne signe rien à votre place.

---

## 5. Sauvegarde, archivage, journal

- **Sauvegarder** (Tableau de bord, menu de la mission) : exporte la mission complète en ZIP (base + fichiers importés). Conservez ces archives hors de la machine.
- **Restaurer** : réimporte un ZIP Probare ; refusé si la mission existe déjà.
- **Archiver** : à la clôture, archivez la mission — elle passe en **lecture seule** (toute modification est refusée tant qu'elle n'est pas explicitement désarchivée).
- **Historique** : consultez à tout moment la piste d'audit — imports, contrôles, appels IA (modèle et volumes), décisions, transitions.

---

## 6. Bonnes pratiques et limites à connaître

1. **L'IA propose, vous disposez.** Ne validez jamais un projet de décision sans avoir réalisé les diligences : le texte est volontairement rédigé au conditionnel pour vous y obliger.
2. **Typez toujours vos tranchements.** Le cumul ISA 450 ne fonctionne que si chaque anomalie non corrigée porte son montant d'incidence.
3. **Rapprochement bancaire :** le solde du relevé est détecté par heuristique (plus grand montant) — vérifiez-le systématiquement contre le relevé papier.
4. **Anonymisation :** seuls le nom du client et le NIF sont pseudonymisés. Les libellés d'écritures (noms de fournisseurs, de salariés) partent tels quels à l'IA — tenez-en compte dans le consentement client.
5. **Sondages :** le tirage est aléatoire simple (non stratifié). Pour les populations très hétérogènes, complétez par une sélection ciblée des éléments majeurs.
6. **Mono-utilisateur :** Probare (MVP) n'a ni comptes ni signature électronique — le nom du décideur est déclaratif. Encadrez l'accès au poste de travail.
7. **Sauvegardez avant chaque étape importante** (fin d'ingestion, fin des travaux) : les données vivent en local sur votre machine.

---

## 7. Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| « Moteur non disponible » au démarrage | Le service de calcul n'a pas démarré | Cliquez **Réessayer** ; vérifiez l'installation Python si le problème persiste |
| « Clé API Claude non configurée » | `.env` absent ou incomplet | Voir § 2.1, puis redémarrez |
| « Consentement client requis » | Case non cochée au cadrage | Activez le consentement (avec l'accord du client) |
| « Ce fichier a déjà été importé » | Import strictement identique | Supprimez l'import existant avant de réimporter |
| « Seuil de signification non défini » | Passage aux travaux sans seuil | Calculez le seuil à l'étape Planification |
| « ISA 450 : le cumul… dépasse le seuil » | Anomalies non corrigées > seuil | Enregistrez les corrections du client ou confirmez le dépassement en connaissance de cause |
| « Dossier archivé — lecture seule » | Mission archivée | Désarchivez-la depuis le tableau de bord |
| « ISA 505 : … documentez les procédures alternatives » | Clôture d'une circularisation sans réponse | Renseignez les procédures alternatives avant de clore |

---

*Probare v0.1 (MVP) — Ce guide décrit le fonctionnement du logiciel ; il ne se substitue ni aux normes d'exercice professionnel ni à votre jugement. L'opinion d'audit demeure de la responsabilité exclusive de l'auditeur habilité signataire.*

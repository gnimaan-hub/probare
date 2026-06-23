<!-- converted from Probare_Cahier_des_charges.docx -->

PROBARE
Cahier des charges fonctionnel
Outil d’assistance à l’audit comptable
Périmètre fonctionnel exhaustif — V1 audit contractuel, V2 audit légal
Document de spécification — base du brief de développement

Sommaire

# 1. Contexte et objectifs
Objet. Probare est un outil d’assistance destiné aux auditeurs comptables. Il accompagne la mission d’audit de la prise de contact jusqu’à la remise du dossier complet, en automatisant les calculs, en assistant le raisonnement et en garantissant la traçabilité de chaque conclusion.
Principe directeur. Séparation stricte entre le calcul déterministe (toute l’arithmétique est traitée par le moteur Python, donc exacte et reproductible) et le raisonnement probabiliste (le modèle de langage se limite à l’extraction, l’interprétation et la rédaction). Toute valeur est rattachée à sa source par un modèle de provenance.
Posture de l’outil. Probare propose, l’auditeur décide. Aucune sortie issue d’un raisonnement n’est figée : tout est modifiable, justifié et révisable. L’outil ne se substitue jamais au jugement professionnel ni à la signature.
## 1.1 Stratégie de versions
Le périmètre est livré en deux temps, qui correspondent aux deux familles d’audit :
- V1 — Audit contractuel. Embranchement principal, développé en premier. Il implémente la méthode d’audit complète sur un périmètre librement négocié, sans les obligations légales propres au commissariat aux comptes.
- V2 — Audit légal. Couche additionnelle qui se greffe sur le tronc commun de la V1. Elle ajoute les obligations, rapports et procédures spécifiques au commissaire aux comptes, sans reconstruire la méthode.
Note de conception — Choix d’architecture fondateur : la méthode d’audit est commune aux deux familles. La V1 doit donc être conçue dès le départ comme un tronc extensible, où la « nature de mission » est une variable de premier plan activant ou masquant des modules. La V2 n’est pas un nouveau produit mais une extension.

# 2. Périmètre, acteurs et hypothèses
## 2.1 Dans le périmètre
- Gestion des dossiers et du cycle de vie de la mission.
- Import et préparation des données comptables.
- Planification, analyse des risques et seuils de signification.
- Contrôle des comptes par cycle, circularisation, échantillonnage.
- Registre des anomalies, travaux de fin de mission, opinion et rapports.
- Moteurs IA et déterministe, traçabilité, gestion documentaire, restitution.
## 2.2 Hors périmètre (à ce stade)
- Tenue de la comptabilité du client (Probare consomme des données, ne les produit pas).
- Télétransmission réglementaire et signature électronique qualifiée (à étudier ultérieurement).
- Gestion commerciale du cabinet (facturation, CRM).
## 2.3 Acteurs
Auditeur (préparateur). Réalise les travaux, saisit et valide les conclusions. Utilisateur principal.
Réviseur / associé signataire. Supervise, revoit, valide l’opinion. Peut être la même personne en exercice solo, mais le rôle existe.
Assistant IA. Acteur logiciel : extrait, interprète, rédige des propositions. N’a aucun pouvoir de décision ni de calcul.
## 2.4 Hypothèses à confirmer
Ces hypothèses structurent le cahier des charges ; elles peuvent être ajustées :
- Trois cycles pour le MVP : ventes-clients, achats-fournisseurs et trésorerie (les plus universels et couvrant les assertions clés). À confirmer.
- Application de bureau (Electron) avec backend local Python/FastAPI ; un dossier = une base locale chiffrée. Synchronisation cloud envisageable ultérieurement.
- Usage mono-utilisateur au départ, conception prévoyant le multi-utilisateur.
- Langue française en priorité, architecture d’internationalisation prévue.

# 3. Architecture cible
Le cahier des charges suppose la pile retenue pour Probare :
Frontend. Electron + React + TypeScript — application de bureau, interface organisée par cycle (gabarit réutilisable).
Backend. Python + FastAPI — moteur de calcul déterministe, orchestration des traitements, accès aux données.
Intelligence. API Claude — extraction, interprétation et rédaction uniquement, encadrées par des garde-fous.
Données. Stockage par dossier (base locale chiffrée), avec modèle de provenance transversal.
## 3.1 Les deux moteurs
L’architecture repose sur deux moteurs nettement séparés. Cette séparation est une exigence, pas une commodité :
Note de conception — La frontière entre les deux moteurs doit être matérialisée dans l’interface : l’utilisateur distingue toujours une valeur calculée (fiable) d’une proposition de l’IA (à valider). C’est un gage de confiance professionnelle et de conformité.

# 4. Lecture des exigences
Chaque exigence porte un identifiant unique (préfixe de module + numéro) pour la traçabilité et le suivi de développement. La priorité suit la logique MoSCoW :
- Must — indispensable à la V1 ; sans elle, l’outil n’est pas utilisable.
- Should — importante mais pouvant être livrée juste après le premier jalon.
- Could — utile, à intégrer si le temps le permet.
Les exigences de la partie V2 (audit légal) sont toutes postérieures à la V1 ; leur priorité indique l’ordre au sein de la V2.

# 5. V1 — Audit contractuel (périmètre fonctionnel complet)
Cette partie décrit l’intégralité des fonctionnalités de la V1. Elle constitue aussi le tronc commun réutilisé par la V2.
## GEN — Généralités et fondations
Exigences transverses qui sous-tendent tous les modules.
Note de conception — Les exigences GEN sont les fondations : elles doivent être posées avant les modules métier, car la provenance et le journal d’audit s’y greffent partout.

## DOS — Gestion des dossiers et des missions
Le dossier est l’objet central de l’outil.
Note de conception — DOS-02 est l’aiguillage qui rend la V2 possible sans refonte : prévoir dès la V1 le mécanisme d’activation conditionnelle de modules selon la nature de mission.

## ACC — Acceptation et cadrage de la mission
En contractuel, l’acceptation est allégée mais structurée ; le périmètre est négocié.

## IMP — Import et préparation des données comptables
Point d’entrée des chiffres ; tout y est déterministe et tracé.
Note de conception — L’import est le premier maillon de la chaîne de provenance : chaque montant manipulé plus loin doit pouvoir remonter jusqu’à sa ligne et son fichier d’origine.

## PLA — Planification et analyse des risques
Phase à plus forte valeur d’assistance.
Note de conception — Le seuil de signification est transversal : sa valeur doit alimenter dynamiquement l’étendue suggérée des contrôles (PLA-04 → CPT, ECH) et la confrontation finale des anomalies (ANO-04).

## CIN — Appréciation du contrôle interne
Optionnelle et allégée en contractuel selon le périmètre négocié ; obligatoire en V2.
Note de conception — CIN-04 matérialise l’embranchement « approche par les contrôles vs substantive » : la conclusion d’un cycle doit moduler l’effort de contrôle des comptes de ce même cycle.

## CPT — Contrôle des comptes (travaux substantifs)
Cœur opérationnel, structuré par cycle. Trois cycles en MVP.
Note de conception — Le gabarit par cycle (CPT-01) est un composant unique paramétré par cycle : concevoir un seul écran réutilisable plutôt que trois écrans distincts facilite l’ajout de cycles supplémentaires.

## CIR — Circularisation (confirmations externes)
Demandes de confirmation aux tiers et rapprochement des réponses.
Note de conception — L’envoi effectif des demandes reste une action de l’utilisateur : l’outil prépare, suit et rapproche, mais n’expédie pas sans validation explicite.

## ECH — Échantillonnage
Sélection des éléments à tester quand le contrôle exhaustif est impossible.
Note de conception — L’échantillonnage relève strictement du moteur déterministe : une même base et un même paramétrage doivent toujours produire le même échantillon, condition de reproductibilité du dossier.

## ANO — Registre des anomalies
Recensement central de toutes les anomalies de la mission.
Note de conception — Le registre alimente directement la synthèse de fin de mission (FIN-04) et la proposition d’opinion (OPI-01). Il doit être unique et centralisé, alimenté depuis tous les cycles.

## FIN — Travaux de fin de mission
Bouclage de la mission avant l’opinion.

## OPI — Opinion et rapports
Formation de l’opinion et production des rapports.
Note de conception — La matrice d’opinion (OPI-01) est commune aux deux versions ; la V2 y ajoutera seulement les libellés et le formalisme de la certification légale.

## IA — Moteur d’assistance (IA)
Encadre l’usage de l’API Claude.
Note de conception — IA-03 est une règle de sûreté : tout besoin de chiffre dans une tâche IA doit être satisfait par un appel au moteur déterministe, jamais par le modèle de langage.

## CAL — Moteur de calcul (déterministe)
Garantit l’exactitude et la reproductibilité des chiffres.

## TRA — Traçabilité et provenance
Exigence normative la plus structurante.
Note de conception — La traçabilité répond directement à l’exigence de justification du dossier de travail : c’est un différenciateur produit autant qu’une obligation.

## GED — Gestion documentaire
Pièces justificatives et documents générés.

## REV — Revue et supervision
Workflow de validation, utile même en exercice solo.

## DASH — Tableau de bord et pilotage
Vue d’ensemble de l’avancement de la mission.

## ADM — Administration et paramétrage
Configuration de l’outil et des référentiels.

## EXP — Export et restitution
Production du dossier de travail et des livrables.


# 6. Exigences non fonctionnelles
Communes aux deux versions, elles conditionnent l’adoption de l’outil par des professionnels soumis au secret et à des normes.
## SEC — Sécurité et confidentialité
Les données comptables sont sensibles et couvertes par le secret professionnel.
Note de conception — SEC-04 mérite une attention particulière : définir explicitement quelles données quittent le poste vers l’API, et offrir un contrôle à l’auditeur, est à la fois une exigence déontologique et un argument commercial.

## PERF — Performance
Les dossiers comptables peuvent être volumineux.

## FIA — Fiabilité et conformité
La crédibilité de l’outil repose sur l’exactitude et la traçabilité.

## EXP-NF — Exploitation et ergonomie
Conditions d’usage au quotidien.


# 7. V2 — Audit légal (couche additionnelle)
La V2 réutilise l’intégralité du tronc commun de la V1. Elle n’ajoute que les éléments propres au commissariat aux comptes, activés par la « nature de mission = légale » (DOS-02). Aucun module de la V1 n’est reconstruit ; certains sont renforcés.
## 7.1 Ce que la V2 réutilise tel quel
Toute la méthode : gestion de dossier, import, planification et risques, contrôle des comptes par cycle, circularisation, échantillonnage, registre des anomalies, fin de mission, moteurs IA et déterministe, traçabilité, gestion documentaire, restitution. Le commissaire aux comptes travaille selon la même démarche que l’auditeur contractuel.
## 7.2 Ce que la V2 ajoute ou renforce
## LEG-ACC — Acceptation renforcée du mandat
L’acceptation légale est plus exigeante que la contractuelle.
Note de conception — S’appuie sur ACC (V1) en durcissant le questionnaire et en ajoutant les contrôles légaux. C’est une extension du module ACC, pas un nouveau module.

## LEG-MAN — Gestion du mandat pluriannuel
Le mandat légal couvre plusieurs exercices (six ans dans la tradition francophone).

## LEG-OUV — Contrôle des soldes d’ouverture
Spécifique à la première année de mandat.
Note de conception — Se branche sur le module IMP / CPT : un drapeau « première année de mandat » déclenche un programme de travail additionnel sur les soldes d’ouverture.

## LEG-CIN — Contrôle interne obligatoire
Ce qui est optionnel en contractuel devient requis en légal.
Note de conception — Active et rend obligatoires les exigences CIN (V1) ; ajoute l’obligation de communication.

## LEG-CONV — Conventions réglementées
Engagements entre la société et ses dirigeants ou associés.

## LEG-RAP — Rapports légaux
Livrables spécifiques au commissaire aux comptes.
Note de conception — Réutilise le moteur de génération documentaire (GED) et la matrice d’opinion (OPI) ; n’ajoute que des modèles et le formalisme légal.

## LEG-CERT — Formalisme de certification
Habillage légal de l’opinion.

## LEG-OBL — Obligations légales spécifiques
Procédures sans équivalent contractuel.
Note de conception — Ces procédures se déclenchent sur des constats précis (FIN-02 pour la continuité, ANO pour les faits relevés). Les modéliser comme des workflows tracés rattachés à leur fait déclencheur.


# 8. Modèle de données (entités principales)
Traduction directe du dossier de travail en entités, base de la persistance par dossier.
Note de conception — Le couple « dossier permanent / dossier annuel » et l’entité « provenance » sont le socle. Les entités spécifiques à la V2 (mandat, convention réglementée, alerte, révélation) s’ajoutent par simple extension, rattachées au Dossier de nature légale.

# 9. Lotissement et trajectoire
## 9.1 V1 — Audit contractuel
Découpage indicatif en lots livrables, du socle vers la valeur :
- Lot 1 — Socle. GEN, DOS, IMP, CAL, TRA. Créer un dossier, importer des données fiables et tracées.
- Lot 2 — Planification. ACC, PLA. Cadrer la mission, calculer les seuils, cartographier les risques.
- Lot 3 — Travaux. CPT (3 cycles), ECH, CIR, ANO. Le cœur opérationnel.
- Lot 4 — Conclusion. FIN, OPI, GED, EXP. Boucler, conclure, produire le dossier.
- Lot 5 — Confort. CIN, REV, DASH, ADM et les exigences Should/Could.
## 9.2 V2 — Audit légal
Une fois la V1 stabilisée, activation de la couche légale : LEG-ACC et LEG-MAN, puis LEG-CIN, LEG-CONV et LEG-RAP, enfin LEG-CERT et LEG-OBL. Aucun lot V2 ne précède l’achèvement du tronc commun, dont il dépend entièrement.
Note de conception — Critère de réussite de l’architecture : le passage de la V1 à la V2 ne doit demander que l’ajout de modules et d’entités, jamais la réécriture d’un module existant. Si une fonctionnalité V2 oblige à refondre un module V1, c’est le signe que la « nature de mission » n’a pas été suffisamment isolée dès le départ.
| ID | Exigence | Priorité |
| --- | --- | --- |
| Déterministe | Imports, normalisation, totalisations, rapprochements, recalculs, seuils, échantillonnage, cumul des anomalies. Exact et reproductible. | Must |
| Probabiliste | Extraction de données depuis des pièces, interprétation des variations, qualification proposée d’anomalies, rédaction de mémos et de rapports. Propositions tracées. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| GEN-01 | Application de bureau multiplateforme (Windows, macOS). | Must |
| GEN-02 | Backend de calcul local Python/FastAPI orchestrant les traitements. | Must |
| GEN-03 | Intégration de l’API Claude pour les tâches de raisonnement. | Must |
| GEN-04 | Séparation stricte calcul déterministe / raisonnement probabiliste, imposée par l’architecture. | Must |
| GEN-05 | Modèle de provenance : toute valeur reliée à sa source (fichier, ligne, pièce). | Must |
| GEN-06 | Stockage par dossier dans une base locale chiffrée. | Must |
| GEN-07 | Fonctionnement hors-ligne des opérations ne requérant pas l’IA. | Should |
| GEN-08 | Interface en français, architecture d’internationalisation prévue. | Must |
| GEN-09 | Journal d’audit applicatif : toutes les actions horodatées et attribuées. | Must |
| GEN-10 | Sauvegarde et restauration d’un dossier. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| DOS-01 | Créer, ouvrir, dupliquer et archiver un dossier de mission. | Must |
| DOS-02 | Attribut « nature de mission » (contractuelle / légale) pilotant l’activation des modules. | Must |
| DOS-03 | Fiche de l’entité auditée (identité, secteur, dirigeants, systèmes d’information). | Must |
| DOS-04 | Paramétrage de l’exercice et du référentiel comptable applicable. | Must |
| DOS-05 | Séparation dossier permanent / dossier annuel. | Must |
| DOS-06 | Report des éléments permanents d’un exercice à l’autre. | Should |
| DOS-07 | Cycle de vie et statuts de la mission (acceptation → planification → travaux → fin → clôture). | Must |
| DOS-08 | Gestion de plusieurs exercices pour une même entité. | Should |
| DOS-09 | Recherche et filtrage des dossiers. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| ACC-01 | Questionnaire d’acceptation (compétence, ressources, risque client). | Must |
| ACC-02 | Évaluation de l’indépendance (version allégée). | Should |
| ACC-03 | Décision d’acceptation tracée et horodatée, avec sortie « refus » possible. | Must |
| ACC-04 | Définition du périmètre négocié (objectifs, comptes et cycles visés). | Must |
| ACC-05 | Génération de la lettre de mission depuis un modèle. | Must |
| ACC-06 | Saisie informative du calendrier et des honoraires. | Could |
| ID | Exigence | Priorité |
| --- | --- | --- |
| IMP-01 | Import de la balance (CSV, Excel). | Must |
| IMP-02 | Import du grand-livre et des journaux. | Must |
| IMP-03 | Support du fichier des écritures comptables (FEC) ou équivalent local. | Should |
| IMP-04 | Mapping des comptes au référentiel et aux cycles. | Must |
| IMP-05 | Contrôles d’intégrité (équilibre débit/crédit, cohérence balance/grand-livre). | Must |
| IMP-06 | Détection des écarts d’import et journal des rejets. | Must |
| IMP-07 | Conservation de la provenance de chaque ligne importée. | Must |
| IMP-08 | Réimport et versionnement des jeux de données. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| PLA-01 | Fiche de prise de connaissance de l’entité et de son environnement. | Must |
| PLA-02 | Procédures analytiques préliminaires (variations N/N-1, ratios) — calcul déterministe. | Must |
| PLA-03 | Interprétation assistée des variations (proposition IA à valider). | Should |
| PLA-04 | Détermination des seuils : global, de travail, de remontée — calcul + proposition. | Must |
| PLA-05 | Choix paramétrable de l’agrégat de référence du seuil. | Should |
| PLA-06 | Cartographie des risques par cycle et par assertion. | Must |
| PLA-07 | Proposition IA de risques, systématiquement validée par l’auditeur. | Should |
| PLA-08 | Génération du plan de mission et du programme de travail. | Must |
| PLA-09 | Bibliothèque de programmes-types par cycle. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| CIN-01 | Description des cycles et de leurs procédures. | Should |
| CIN-02 | Questionnaires de contrôle interne par cycle. | Should |
| CIN-03 | Tests de procédures et conclusion sur la fiabilité. | Should |
| CIN-04 | Lien entre conclusion de contrôle interne et étendue substantive du cycle. | Should |
| CIN-05 | Génération d’une note de recommandations sur les faiblesses. | Could |
| ID | Exigence | Priorité |
| --- | --- | --- |
| CPT-01 | Espace de travail par cycle, sur le gabarit « comprendre → apprécier → contrôler → conclure ». | Must |
| CPT-02 | Feuilles de travail structurées (objectif, étendue, éléments examinés, conclusion). | Must |
| CPT-03 | Rattachement de chaque contrôle aux assertions couvertes. | Must |
| CPT-04 | Recalculs automatiques (amortissements, provisions, dépréciations) — déterministe. | Must |
| CPT-05 | Tests de séparation des exercices (cut-off). | Must |
| CPT-06 | Rapprochements (balance auxiliaire / grand-livre, bancaires) — déterministe. | Must |
| CPT-07 | Procédures analytiques de substance. | Should |
| CPT-08 | Détection assistée d’incohérences (proposition IA). | Should |
| CPT-09 | Lien feuille de travail ↔ pièces ↔ valeurs (provenance complète). | Must |
| CPT-10 | Statut d’avancement et de revue par feuille de travail. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| CIR-01 | Génération des demandes (clients, fournisseurs, banques, avocats). | Must |
| CIR-02 | Sélection des tiers à circulariser (liée à l’échantillonnage). | Must |
| CIR-03 | Suivi des envois et des relances. | Must |
| CIR-04 | Saisie et rapprochement des réponses reçues. | Must |
| CIR-05 | Traitement et documentation des écarts confirmés. | Should |
| CIR-06 | Modèles de lettres multilingues. | Could |
| ID | Exigence | Priorité |
| --- | --- | --- |
| ECH-01 | Méthodes statistiques et par jugement. | Must |
| ECH-02 | Sélection déterministe, reproductible et tracée. | Must |
| ECH-03 | Paramétrage par seuil et par niveau de risque. | Must |
| ECH-04 | Documentation de la base d’échantillonnage et de l’extrapolation. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| ANO-01 | Saisie ou détection d’une anomalie (montant, assertion, cycle). | Must |
| ANO-02 | Statut corrigée / non corrigée et lien vers la pièce d’origine. | Must |
| ANO-03 | Agrégation et cumul des anomalies — déterministe. | Must |
| ANO-04 | Confrontation du cumul au seuil de signification. | Must |
| ANO-05 | Vue consolidée des anomalies du dossier. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| FIN-01 | Note des événements postérieurs à la clôture. | Must |
| FIN-02 | Mémo de continuité d’exploitation. | Must |
| FIN-03 | Génération de la lettre d’affirmation. | Must |
| FIN-04 | Synthèse des anomalies, agrégée automatiquement depuis le registre. | Must |
| FIN-05 | Liste de contrôle (checklist) de fin de mission. | Should |
| FIN-06 | Note de revue finale. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| OPI-01 | Matrice de sélection d’opinion (gravité × étendue × nature du problème). | Must |
| OPI-02 | Proposition du sens de l’opinion (IA), validée par l’auditeur. | Should |
| OPI-03 | Génération du rapport contractuel (opinion ou constats). | Must |
| OPI-04 | Modèles de rapport paramétrables. | Must |
| OPI-05 | Verrouillage et horodatage du rapport final. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| IA-01 | Intégration de l’API Claude avec clé stockée de façon sécurisée. | Must |
| IA-02 | Tâches autorisées limitées à l’extraction, l’interprétation et la rédaction. | Must |
| IA-03 | Interdiction de tout calcul arithmétique par l’IA. | Must |
| IA-04 | Chaque sortie IA est une proposition modifiable, tracée à ses sources. | Must |
| IA-05 | Bibliothèque de prompts / compétences par tâche. | Should |
| IA-06 | Gestion du coût (jetons) et journalisation des appels. | Should |
| IA-07 | Mode dégradé lorsque l’IA est indisponible (travail manuel possible). | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| CAL-01 | Toute l’arithmétique de la mission traitée en Python. | Must |
| CAL-02 | Recalculs, totalisations, rapprochements et cumuls. | Must |
| CAL-03 | Calcul des seuils et de l’échantillonnage. | Must |
| CAL-04 | Reproductibilité garantie : mêmes entrées, mêmes sorties. | Must |
| CAL-05 | Tests automatisés sur les calculs critiques. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| TRA-01 | Modèle de provenance reliant chaque valeur à sa source. | Must |
| TRA-02 | Journal d’audit applicatif horodaté (qui, quoi, quand). | Must |
| TRA-03 | Versionnement des feuilles de travail. | Should |
| TRA-04 | Piste d’audit reconstituable pour chaque conclusion. | Must |
| TRA-05 | Distinction visuelle entre valeur calculée et proposition de l’IA. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| GED-01 | Stockage des pièces justificatives par dossier. | Must |
| GED-02 | Liens pièces ↔ feuilles de travail ↔ valeurs. | Must |
| GED-03 | Génération de documents Word et PDF depuis modèles. | Must |
| GED-04 | Bibliothèque de modèles paramétrables. | Must |
| GED-05 | Indexation et recherche des pièces. | Should |
| GED-06 | Classification assistée des pièces (IA). | Could |
| ID | Exigence | Priorité |
| --- | --- | --- |
| REV-01 | Statuts de revue par feuille de travail. | Must |
| REV-02 | Workflow préparateur → réviseur. | Should |
| REV-03 | Notes de revue et points en suspens. | Should |
| REV-04 | Verrouillage des feuilles après revue. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| DASH-01 | Avancement global et par cycle. | Must |
| DASH-02 | Alertes (anomalies au-dessus du seuil, travaux non revus, réponses de circularisation manquantes). | Should |
| DASH-03 | Vue d’ensemble synthétique de la mission. | Must |
| DASH-04 | Indicateurs de couverture des assertions. | Could |
| ID | Exigence | Priorité |
| --- | --- | --- |
| ADM-01 | Gestion des référentiels comptables. | Must |
| ADM-02 | Gestion des modèles de documents et de programmes de travail. | Must |
| ADM-03 | Paramétrage des seuils par défaut. | Should |
| ADM-04 | Gestion des utilisateurs (mono au départ, multi prévu). | Should |
| ADM-05 | Configuration sécurisée de la clé d’API. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| EXP-01 | Export du dossier de travail complet. | Must |
| EXP-02 | Génération du dossier final structuré (permanent + annuel). | Must |
| EXP-03 | Export PDF des rapports et des feuilles de travail. | Must |
| EXP-04 | Archivage du dossier clôturé en lecture seule. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| SEC-01 | Chiffrement des données au repos. | Must |
| SEC-02 | Stockage sécurisé de la clé d’API, jamais en clair. | Must |
| SEC-03 | Contrôle d’accès au dossier (authentification). | Must |
| SEC-04 | Maîtrise des données transmises à l’IA (minimisation, consentement). | Must |
| SEC-05 | Respect des obligations de confidentialité et de protection des données. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| PERF-01 | Traitement de jeux de données de plusieurs centaines de milliers de lignes. | Must |
| PERF-02 | Réactivité de l’interface pendant les calculs (traitements en arrière-plan). | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| FIA-01 | Déterminisme et exactitude vérifiables des calculs. | Must |
| FIA-02 | Conformité de la documentation aux attentes normatives (NEP/ISA). | Must |
| FIA-03 | Auditabilité de l’outil lui-même (journal, versions). | Should |
| FIA-04 | Intégrité et cohérence des données du dossier. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| ERG-01 | Ergonomie de bureau cohérente, gabarit identique par cycle. | Must |
| ERG-02 | Sauvegarde et restauration fiables. | Must |
| ERG-03 | Maintenabilité et modularité du code (ajout de cycles, de modules). | Must |
| ERG-04 | Internationalisation (français d’abord, extensible). | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-ACC-01 | Vérification approfondie de l’indépendance et des incompatibilités légales. | Must |
| LEG-ACC-02 | Contrôle des conditions de nomination et de la régularité du mandat. | Must |
| LEG-ACC-03 | Prise de contact formalisée avec le commissaire prédécesseur. | Should |
| LEG-ACC-04 | Distinction première année de mandat / années suivantes. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-MAN-01 | Suivi du mandat sur sa durée et des exercices qu’il couvre. | Must |
| LEG-MAN-02 | Continuité du dossier permanent sur toute la durée du mandat. | Should |
| LEG-MAN-03 | Échéancier des obligations récurrentes du mandat. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-OUV-01 | Travaux renforcés sur les soldes d’ouverture en première année. | Must |
| LEG-OUV-02 | Documentation de la reprise des soldes et de leur justification. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-CIN-01 | Appréciation du contrôle interne rendue obligatoire et formalisée. | Must |
| LEG-CIN-02 | Communication des faiblesses significatives à la gouvernance. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-CONV-01 | Recensement et suivi des conventions réglementées. | Must |
| LEG-CONV-02 | Qualification assistée des conventions (proposition IA). | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-RAP-01 | Génération du rapport général sur les comptes annuels (certification). | Must |
| LEG-RAP-02 | Génération du rapport spécial sur les conventions réglementées. | Must |
| LEG-RAP-03 | Production des autres rapports spécifiques selon les opérations de l’exercice. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-CERT-01 | Libellés de certification (sans réserve, avec réserve, refus, impossibilité de certifier). | Must |
| LEG-CERT-02 | Justification structurée du type de certification retenu. | Must |
| ID | Exigence | Priorité |
| --- | --- | --- |
| LEG-OBL-01 | Procédure d’alerte lorsque la continuité est compromise (workflow et traçabilité). | Must |
| LEG-OBL-02 | Registre de révélation des faits délictueux. | Must |
| LEG-OBL-03 | Communications légales à la gouvernance. | Should |
| LEG-OBL-04 | Calendrier de suivi des échéances et obligations légales. | Should |
| ID | Exigence | Priorité |
| --- | --- | --- |
| Dossier | Mission : nature, exercice(s), référentiel, seuils, statut, lien vers l’entité. | Must |
| Entité auditée | Identité, secteur, dirigeants, systèmes d’information. | Must |
| Dossier permanent | Pièces stables réutilisées d’un exercice à l’autre. | Must |
| Cycle | Rattache risques, contrôles internes, programme et feuilles de travail. | Must |
| Risque | Niveau, assertion(s) visée(s), réponse d’audit associée. | Must |
| Feuille de travail | Objectif, étendue, éléments examinés, conclusion, statut de revue. | Must |
| Anomalie | Montant, assertion, statut (corrigée/non), pièce d’origine, cycle. | Must |
| Seuils | Global, de travail, de remontée. | Must |
| Pièce / preuve | Document source, avec liens de provenance vers les valeurs qui s’en servent. | Must |
| Donnée comptable | Ligne de balance / écriture, avec source d’import. | Must |
| Trace / provenance | Qui, quoi, quand, à partir de quelle source — transversale à tout. | Must |
| Document généré | Livrable produit depuis un modèle (lettre, rapport, synthèse). | Must |
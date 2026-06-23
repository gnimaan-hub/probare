<!-- converted from Probare_Reference_Audit.docx -->

PROBARE
Document de référence métier
L’audit comptable de bout en bout
Du premier contact client à la remise du dossier d’audit complet
Cadre, étapes, embranchements et points de conception logicielle
Référence interne — conception de l’outil d’assistance à l’audit

Sommaire

# 0. Comment lire ce document
Ce document décrit le déroulement d’un audit comptable tel qu’il est pratiqué par un cabinet de commissariat aux comptes ou un auditeur contractuel. Il est conçu comme une référence pour concevoir un logiciel d’assistance : chaque phase métier est décrite puis traduite en implications concrètes pour l’outil.
Trois types d’encadrés rythment le texte :
- Pour le logiciel — ce que l’étape implique en termes de fonctionnalités, de données ou d’ergonomie.
- Embranchement — les bifurcations où le déroulement change selon une décision ou un constat.
- Livrable(s) — le ou les documents produits à la fin de la phase.
Le vocabulaire est celui de la tradition francophone (commissaire aux comptes, certification, réserve…), qui correspond au marché visé. La méthodologie sous-jacente est commune aux Normes d’Exercice Professionnel (NEP) et aux normes internationales d’audit (ISA), largement convergentes.

# 1. Vue d’ensemble et cadre
## 1.1 Les deux grandes familles d’audit
Avant toute chose, il faut distinguer deux contextes qui partagent la même méthode mais pas le même cadre juridique.
Audit légal (commissariat aux comptes). Obligatoire pour certaines entités selon des seuils (chiffre d’affaires, total de bilan, effectif) ou selon la forme juridique. Le commissaire aux comptes (CAC) est nommé par l’assemblée générale, pour un mandat pluriannuel (six ans dans la tradition française et OHADA). Il a des obligations légales envers les tiers et sa mission aboutit à une certification des comptes.
Audit contractuel. Demandé volontairement (banque, investisseur, acquéreur, dirigeant). Le périmètre est librement négocié ; il n’y a pas de certification au sens légal, mais un rapport d’opinion ou de constats.
Embranchement — Tout l’outil doit savoir, dès l’ouverture d’un dossier, à quelle famille il appartient : le type d’audit conditionne les obligations, les livrables et certaines procédures spécifiques (alerte, révélation, conventions réglementées) qui n’existent qu’en légal.
Pour le logiciel — Prévoir un attribut « nature de mission » (légale / contractuelle) au niveau du projet, qui active ou masque des modules entiers. C’est une variable structurante, pas un simple champ descriptif.
## 1.2 Le cadre normatif
L’audit n’est pas libre : il suit un référentiel de normes (NEP en contexte francophone, ISA à l’international). Ces normes imposent une démarche par les risques, un seuil de signification, une documentation traçable et une supervision. Localement, l’exercice s’appuie aussi sur le référentiel comptable applicable (plan comptable national ou OHADA selon le cas) et sur l’autorité de tutelle de la profession.
Pour le logiciel — Le référentiel applicable (normes d’audit, plan comptable) gagne à être paramétrable par dossier. Les libellés de comptes, les seuils par défaut et les modèles de rapport en dépendent.
## 1.3 Le fil rouge : risque, preuve, opinion
Toute la mission obéit à une logique simple en trois temps, qu’il est utile de garder en tête pour structurer l’outil :
- Identifier le risque — où les comptes pourraient-ils être faux ?
- Réunir la preuve — collecter des éléments suffisants et appropriés pour réduire ce risque.
- Former l’opinion — conclure et le justifier par le dossier de travail.

# 2. Phase 0 — Acceptation ou maintien de la mission
Objectif. Décider si l’auditeur prend ou conserve le client, et fixer le contrat de la mission.
## 2.1 Déroulement
- Prise de contact et premières informations sur l’entité (activité, taille, dirigeants, contexte).
- Évaluation de l’indépendance : aucun lien financier, familial ou d’intérêt avec le client ; respect des incompatibilités légales en audit légal.
- Évaluation de la compétence et des ressources : maîtrise du secteur, disponibilité des équipes, calendrier réaliste.
- Évaluation du risque client : intégrité des dirigeants, santé financière, secteur sensible, antécédents, motifs de la demande.
- En cas de succession à un confrère : prise de contact avec le prédécesseur. En première année : examen renforcé des soldes d’ouverture.
- Rédaction et signature de la lettre de mission.
Embranchement — Si le risque est jugé inacceptable, la mission est refusée ou le mandat non renouvelé — c’est une sortie possible du processus, qu’il faut pouvoir tracer.
Embranchement — Première mission vs mission récurrente : en première mission, la prise de connaissance et le contrôle des soldes d’ouverture sont plus lourds ; en récurrent, on met à jour l’existant.
Livrable(s) : Lettre de mission (périmètre, responsabilités respectives, calendrier, honoraires) ; fiche d’acceptation/maintien documentant l’analyse d’indépendance et de risque.
Pour le logiciel — C’est l’étape de création d’un dossier dans l’outil. Prévoir un questionnaire d’acceptation structuré (indépendance, risque, ressources) avec décision tracée et horodatée, et la génération de la lettre de mission depuis un modèle. La distinction première année / récurrent doit être un attribut du dossier.

# 3. Phase 1 — Planification (orientation et stratégie)
Objectif. Comprendre l’entité, cartographier les risques et bâtir la stratégie d’audit avant tout contrôle de comptes. C’est la phase intellectuelle la plus déterminante.
## 3.1 Prise de connaissance de l’entité et de son environnement
Secteur d’activité et réglementation, modèle économique, méthodes comptables retenues, systèmes d’information, organisation et gouvernance. En mission récurrente, il s’agit d’une mise à jour ; en première année, d’un travail de fond.
## 3.2 Évaluation du risque d’anomalies significatives
L’auditeur identifie où les comptes pourraient être matériellement faux, à deux niveaux : au niveau des états financiers (risque de fraude du dirigeant, doute sur la continuité, environnement de contrôle faible) et au niveau des assertions, compte par compte et cycle par cycle. La prise en compte du risque de fraude est obligatoire.
## 3.3 Détermination du seuil de signification (matérialité)
C’est le montant au-delà duquel une anomalie est jugée significative — souvent un pourcentage d’un agrégat de référence (résultat, chiffre d’affaires, capitaux propres, total de bilan). On définit en pratique trois niveaux : le seuil de signification global, un seuil de travail plus bas (pour calibrer l’étendue des contrôles) et un seuil de remontée des anomalies non corrigées.
## 3.4 Procédures analytiques préliminaires
Analyse des variations, ratios et tendances sur les comptes pour repérer les zones anormales qui orienteront l’effort d’audit.
## 3.5 Stratégie et plan de mission
La synthèse de ce qui précède donne la stratégie d’audit (vision d’ensemble : nature, calendrier, étendue) et le programme de travail (liste détaillée des contrôles par cycle).
Embranchement — Le niveau de risque évalué oriente directement l’étendue des travaux : un cycle à risque élevé appellera plus de contrôles qu’un cycle à risque faible.
Livrable(s) : Plan de mission ; programme de travail ; note de seuil de signification ; cartographie des risques.
Pour le logiciel — C’est ici que l’assistance apporte le plus de valeur. L’outil peut : calculer des propositions de seuil à partir des agrégats, automatiser la revue analytique (variations, ratios) et signaler les écarts, proposer une cartographie des risques par cycle/assertion à valider par l’auditeur. Toute proposition issue d’un raisonnement doit rester modifiable et justifiée — l’auditeur décide, l’outil suggère.

# 4. Phase 2 — Appréciation du contrôle interne
Objectif. Comprendre et tester les procédures internes de l’entreprise, pour décider du degré de confiance qu’on peut leur accorder.
## 4.1 Démarche par cycle
Le contrôle interne s’examine cycle par cycle. Les cycles usuels sont :
- Ventes – clients (facturation, encaissements, créances)
- Achats – fournisseurs (commandes, réception, dettes, décaissements)
- Paie – personnel
- Stocks et en-cours
- Immobilisations
- Trésorerie et financement
- Capitaux propres et provisions
- Impôts et taxes
Pour chaque cycle, l’auditeur décrit le système (qui fait quoi, quels contrôles existent, séparation des tâches), puis réalise des tests de procédures pour vérifier que ces contrôles fonctionnent réellement dans le temps.
## 4.2 L’embranchement central de la mission
Embranchement — Si le contrôle interne est jugé fiable, l’auditeur peut s’appuyer dessus et réduire les contrôles directs sur les comptes : c’est l’« approche par les contrôles ». S’il est défaillant, l’auditeur ne peut s’y fier et doit renforcer les contrôles substantifs sur les chiffres : c’est l’« approche substantive » étendue. Ce choix conditionne toute la phase 3.
Livrable(s) : Descriptifs de cycles ; feuilles de tests de procédures ; conclusion sur la fiabilité du contrôle interne ; le cas échéant, lettre de recommandations sur les faiblesses constatées.
Pour le logiciel — Modéliser les cycles comme objets de premier plan, chacun rattachant ses contrôles, ses tests et sa conclusion. Le résultat de l’évaluation (fiable / non fiable) doit piloter dynamiquement l’étendue suggérée des travaux substantifs du cycle correspondant. Prévoir un module de recommandations généré à partir des faiblesses relevées.

# 5. Phase 3 — Contrôle des comptes (travaux substantifs)
Objectif. Vérifier directement que les soldes et opérations des comptes sont corrects, au regard des assertions d’audit.
## 5.1 Les assertions d’audit
Chaque contrôle vise à valider une ou plusieurs assertions. Elles constituent l’ossature mentale de tout auditeur :
## 5.2 Les techniques de contrôle
- Confirmations externes (circularisation). On écrit directement aux tiers — banques, clients, fournisseurs, avocats — pour faire confirmer les soldes et engagements.
- Observation physique. Assistance à l’inventaire des stocks, vérification de l’existence des immobilisations.
- Inspection de pièces. Examen des factures, contrats, relevés, pièces justificatives.
- Recalcul et ré-exécution. Refaire un calcul (amortissements, provisions) ou rejouer un contrôle.
- Procédures analytiques de substance. Expliquer des soldes par des relations attendues entre données.
- Sondages (échantillonnage). Quand le volume interdit le contrôle exhaustif, on teste un échantillon — statistique ou par jugement — et on extrapole.
## 5.3 Organisation des travaux
Les travaux se déroulent cycle par cycle. Chaque contrôle produit une feuille de travail documentée : objectif, étendue, éléments examinés, anomalies relevées, conclusion.
Embranchement — L’étendue des sondages et la nature des tests dépendent de l’évaluation du contrôle interne (phase 2) et du risque (phase 1). Un même cycle peut être traité légèrement ou en profondeur selon ces deux variables.
Livrable(s) : Feuilles de travail par cycle ; demandes et réponses de circularisation ; feuilles d’inventaire ; tableaux de recalcul ; relevé des anomalies détectées.
Pour le logiciel — Cœur opérationnel de l’outil. À prévoir : génération et suivi des circularisations (envois, relances, rapprochement des réponses), outils d’échantillonnage (sélection déterministe et traçable), recalculs automatiques, et détection assistée d’incohérences. Chaque anomalie détectée alimente un registre central des anomalies, relié à sa pièce d’origine.

# 6. Phase 4 — Travaux de fin de mission
Objectif. Boucler la mission, s’assurer qu’aucun élément tardif ne remet en cause les comptes, et synthétiser les constats.
- Événements postérieurs à la clôture. Un litige, une défaillance client ou un sinistre survenu après la date de clôture mais avant le rapport peut devoir être pris en compte.
- Continuité d’exploitation. L’entreprise peut-elle poursuivre son activité dans un avenir prévisible ? Point critique, avec des obligations renforcées en audit légal.
- Lettre d’affirmation. La direction confirme par écrit qu’elle a communiqué l’ensemble des informations.
- Synthèse des anomalies. On liste les anomalies corrigées et non corrigées, et on compare leur cumul au seuil de signification. C’est ce cumul qui détermine l’opinion.
- Revue analytique finale et revue du dossier. Cohérence d’ensemble des comptes ; supervision par un associé (revue qualité).
Embranchement — Le cumul des anomalies non corrigées par rapport au seuil est l’embranchement qui, en pratique, oriente le type d’opinion en phase 5.
Livrable(s) : Note d’événements postérieurs ; mémo de continuité d’exploitation ; lettre d’affirmation signée ; synthèse des anomalies (corrigées / non corrigées) ; note de revue.
Pour le logiciel — Prévoir un tableau de synthèse des anomalies qui agrège automatiquement le registre des anomalies de la phase 3, calcule le cumul et le confronte au seuil, puis propose le sens de l’opinion. La lettre d’affirmation et les notes de fin de mission peuvent être générées depuis des modèles.

# 7. Phase 5 — Opinion et rapports
Objectif. Former l’opinion d’audit et émettre les rapports, livrables finaux de la mission.
## 7.1 Les quatre types d’opinion
La conclusion se range dans l’une de quatre catégories, selon la gravité et l’étendue des constats :
## 7.2 Les rapports
En audit légal, les livrables finaux comprennent notamment :
- Le rapport général sur les comptes annuels — il porte l’opinion.
- Le rapport spécial sur les conventions réglementées (engagements entre la société et ses dirigeants ou associés).
- D’autres rapports spécifiques selon les opérations de l’exercice et les obligations légales applicables.
## 7.3 Obligations propres au commissaire aux comptes
Trois obligations n’existent qu’en audit légal et n’ont pas d’équivalent contractuel :
- Révélation des faits délictueux au procureur lorsqu’ils sont découverts.
- Procédure d’alerte lorsque la continuité d’exploitation est compromise.
- Communication à la gouvernance des constats significatifs.
Embranchement — Le choix entre les quatre opinions découle directement de deux axes : gravité (anomalie / désaccord) et étendue (circonscrit / généralisé), croisés avec la nature du problème (désaccord vs limitation des travaux). C’est une matrice de décision modélisable.
Livrable(s) : Rapport général portant l’opinion ; rapport spécial ; rapports spécifiques ; communications légales le cas échéant.
Pour le logiciel — Modéliser la sélection d’opinion comme une matrice (gravité × étendue × nature) qui propose le type d’opinion et le squelette de rapport correspondant. Générer les rapports depuis des modèles paramétrés par la nature de mission. L’outil propose ; l’auditeur tranche et signe.

# 8. Le dossier de travail — votre véritable livrable et votre modèle de données
Tout au long de la mission, l’auditeur alimente un dossier de travail qui matérialise et justifie son opinion. C’est l’objet central autour duquel l’outil doit s’organiser.
## 8.1 Les deux compartiments
Dossier permanent. Informations stables et pluriannuelles : statuts, organigramme, contrats importants, descriptions de cycles, historique des mandats. On le met à jour d’une année sur l’autre.
Dossier annuel (ou courant). Tous les travaux de l’exercice : plan de mission, programme, feuilles de travail, justificatifs, synthèses, rapports.
## 8.2 Le principe d’or : traçabilité et supervision
Chaque conclusion doit être justifiée par une preuve, et chaque travail revu hiérarchiquement. C’est l’exigence normative la plus structurante pour un logiciel : rien ne doit exister sans origine ni justification.
## 8.3 Modèle de données suggéré
Une traduction directe en entités pour la base par projet :
- Dossier (projet) — nature de mission, exercice, référentiel, seuils, statut.
- Dossier permanent — pièces stables, réutilisées d’un exercice à l’autre.
- Cycle — rattache risques, contrôles internes, programme et feuilles de travail.
- Risque — niveau, assertion(s) visée(s), réponse d’audit associée.
- Feuille de travail — objectif, étendue, éléments examinés, conclusion, statut de revue.
- Anomalie — montant, assertion, statut (corrigée / non corrigée), pièce d’origine.
- Seuils — global, de travail, de remontée.
- Pièce / preuve — document source, avec lien de provenance vers les éléments qui s’en servent.
- Trace / provenance — qui, quoi, quand, à partir de quelle source : transversale à tout.
Pour le logiciel — Le couple « dossier permanent / dossier annuel » est le bon point de départ du schéma de données. La traçabilité que vous avez placée au cœur de l’architecture de Probare répond précisément à l’exigence normative de justification du dossier : c’est un atout différenciant, pas un détail technique.

# 9. Synthèse des embranchements décisionnels
Les bifurcations à modéliser dans l’outil, regroupées :
- Accepter ou refuser la mission (phase 0) — selon indépendance, risque, ressources.
- Légale ou contractuelle — active ou non les procédures et rapports spécifiques.
- Première mission ou récurrente — intensité de la prise de connaissance et contrôle des soldes d’ouverture.
- Approche par les contrôles ou substantive (phase 2) — selon la fiabilité du contrôle interne ; pilote l’étendue de la phase 3.
- Cumul des anomalies ≷ seuil (phase 4) — oriente le sens de l’opinion.
- Type d’opinion (phase 5) — matrice gravité × étendue × nature du problème.
- Procédures spéciales du CAC — alerte, révélation, conventions réglementées, déclenchées par des constats spécifiques.

# 10. Implications consolidées pour le logiciel d’assistance
Les points essentiels, rassemblés pour servir de cahier d’orientation fonctionnelle :
- Architecture par cycles et assertions. C’est le squelette mental des auditeurs ; l’interface doit l’épouser.
- Dossier permanent / dossier annuel. Modèle de données de base, avec report d’un exercice à l’autre.
- Seuil de signification transversal. Paramètre central qui module dynamiquement l’étendue suggérée des contrôles et déclenche la confrontation finale des anomalies.
- Registre central des anomalies. Alimenté en continu, agrégé en fin de mission, relié à l’opinion.
- Traçabilité / provenance native. Chaque sortie reliée à sa source — exigence normative et différenciateur.
- Génération documentaire depuis modèles. Lettre de mission, lettre d’affirmation, rapports — paramétrés par la nature de mission.
- Modules activables selon la nature de mission. Les procédures propres au CAC ne s’affichent qu’en audit légal.
- Le logiciel propose, l’auditeur décide. Toute suggestion issue d’un raisonnement reste modifiable, justifiée et révisable.

# 11. Cartographie IA / déterministe
La ligne de partage que vous avez posée dans l’architecture de Probare — calcul déterministe d’un côté, raisonnement probabiliste de l’autre, avec provenance complète — se projette naturellement sur les phases d’audit.

Règle transversale : toute sortie de la colonne de droite est une proposition tracée, rattachée à ses sources, modifiable et révisable par l’auditeur. Le déterministe fournit les chiffres ; l’IA aide à les interpréter ; l’humain conclut et signe.

# 12. Glossaire
Assertion — Affirmation implicite contenue dans les comptes (existence, exhaustivité…) que l’auditeur cherche à valider.
Certification — Opinion du commissaire aux comptes attestant de la régularité, sincérité et image fidèle des comptes.
Circularisation — Confirmation directe d’un solde ou d’un engagement auprès d’un tiers (banque, client, fournisseur, avocat).
Commissaire aux comptes (CAC) — Auditeur légal nommé par l’assemblée générale, soumis à des obligations envers les tiers.
Continuité d’exploitation — Hypothèse selon laquelle l’entité poursuivra son activité dans un avenir prévisible.
Conventions réglementées — Engagements entre la société et ses dirigeants/associés, soumis à un rapport spécial.
Cut-off (séparation des exercices) — Rattachement d’une opération au bon exercice comptable.
Dossier permanent / annuel — Compartiments du dossier de travail : informations stables vs travaux de l’exercice.
NEP / ISA — Normes d’Exercice Professionnel (francophone) / International Standards on Auditing — référentiels d’audit convergents.
Procédure d’alerte — Démarche du CAC lorsque la continuité d’exploitation est menacée.
Procédures analytiques — Analyse des relations entre données (ratios, variations) pour repérer l’anormal.
Seuil de signification — Montant au-delà duquel une anomalie est jugée significative.
Sondage / échantillonnage — Test d’un sous-ensemble d’opérations, avec extrapolation au total.
Tests de procédures — Contrôles destinés à vérifier l’efficacité réelle du contrôle interne.

# Annexe — Le cycle ventes-clients traité de bout en bout
Un exemple concret pour servir de gabarit à l’interface : comment un seul cycle se déroule à travers les phases.
## A.1 Comprendre le cycle (planification)
Flux : commande → livraison → facturation → enregistrement → encaissement. Risques typiques : ventes fictives (existence), ventes non enregistrées (exhaustivité), erreurs de facturation (exactitude), rattachement au mauvais exercice (cut-off), créances irrécouvrables non dépréciées (évaluation).
## A.2 Apprécier le contrôle interne
Vérifier la séparation des tâches (qui facture, qui encaisse, qui comptabilise), l’existence de contrôles sur les prix et les avoirs, le suivi des créances. Tester quelques opérations pour confirmer que ces contrôles fonctionnent.
## A.3 Contrôler les comptes
- Circularisation clients — confirmer les soldes auprès d’un échantillon de clients (existence, droits).
- Tests de cut-off — examiner les dernières factures de l’exercice et les premières du suivant.
- Rapprochement balance auxiliaire / grand-livre — cohérence des créances.
- Revue des créances anciennes — suffisance des dépréciations (évaluation).
## A.4 Conclure
Synthèse du cycle : assertions couvertes, anomalies relevées et leur montant, conclusion sur le caractère raisonnable du poste clients. Les anomalies remontent au registre central pour la synthèse finale.
Pour le logiciel — Ce gabarit « comprendre → apprécier le contrôle interne → contrôler → conclure » se répète pour chaque cycle. C’est un patron d’écran réutilisable : un même composant, paramétré par cycle, avec ses risques, ses contrôles et ses feuilles de travail.
| Niveau | Rôle | Usage dans la mission |
| --- | --- | --- |
| Seuil global | Définit la matérialité d’ensemble | Comparé au cumul final des anomalies pour décider de l’opinion |
| Seuil de travail | Marge de sécurité sous le global | Calibre la profondeur et la taille des sondages |
| Seuil de remontée | Plancher de signalement | En deçà, les anomalies ne sont pas remontées |
| Assertion | Question posée |
| --- | --- |
| Existence / réalité | L’élément enregistré existe-t-il réellement ? |
| Exhaustivité | Tout ce qui devait être enregistré l’a-t-il été ? |
| Droits et obligations | L’entité possède-t-elle bien l’actif / doit-elle bien la dette ? |
| Évaluation et exactitude | Le montant est-il correctement évalué et calculé ? |
| Séparation des exercices (cut-off) | L’opération est-elle rattachée au bon exercice ? |
| Présentation et informations | Est-ce correctement classé et mentionné en annexe ? |
| Opinion | Situation | Déclencheur |
| --- | --- | --- |
| Sans réserve | Comptes réguliers, sincères, fidèles | Aucune anomalie significative non corrigée ; pas de limitation |
| Avec réserve | Anomalie ou limitation circonscrite | Désaccord ou limitation significatif mais non généralisé |
| Défavorable / refus | Comptes trompeurs | Anomalies significatives ET généralisées |
| Impossibilité de certifier | Éléments insuffisants | Limitation des travaux significative ET généralisée |
| Traitement déterministe (calcul, vérifiable) | Assistance probabiliste (IA, à valider) |
| --- | --- |
| Imports et normalisation de la balance | Cartographie des risques par cycle/assertion |
| Totalisations, rapprochements, recalculs | Revue analytique : interprétation des variations |
| Calcul des seuils à partir des agrégats | Détection d’incohérences et d’anomalies |
| Sélection d’échantillons (traçable, reproductible) | Qualification proposée des anomalies |
| Cumul des anomalies vs seuil | Rédaction de mémos et de synthèses |
| Génération de documents depuis modèles | Proposition de type d’opinion (jamais décision) |
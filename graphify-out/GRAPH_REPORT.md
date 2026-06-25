# Graph Report - .  (2026-06-25)

## Corpus Check
- 35 files · ~128,096 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 970 nodes · 2194 edges · 64 communities (52 shown, 12 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_API Routes Core|API Routes Core]]
- [[_COMMUNITY_Dossier Audit DALOL|Dossier Audit DALOL]]
- [[_COMMUNITY_LLM Claude Client|LLM Claude Client]]
- [[_COMMUNITY_API Routes Calculs|API Routes Calculs]]
- [[_COMMUNITY_API Routes Documents|API Routes Documents]]
- [[_COMMUNITY_API Routes Preconditions|API Routes Preconditions]]
- [[_COMMUNITY_Assertions & Cadrage|Assertions & Cadrage]]
- [[_COMMUNITY_Circularisation|Circularisation]]
- [[_COMMUNITY_Controles Engine|Controles Engine]]
- [[_COMMUNITY_Storage Database|Storage Database]]
- [[_COMMUNITY_Tests Controls|Tests Controls]]
- [[_COMMUNITY_UI Sidebar Layout|UI Sidebar Layout]]
- [[_COMMUNITY_Sondages Controls|Sondages Controls]]
- [[_COMMUNITY_UI Planification|UI Planification]]
- [[_COMMUNITY_Tests Coherence|Tests Coherence]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]

## God Nodes (most connected - your core abstractions)
1. `API Routes` - 175 edges
2. `_make_row()` - 117 edges
3. `_rows()` - 115 edges
4. `_get_db()` - 84 edges
5. `ProjectDB` - 80 edges
6. `ClaudeClient` - 50 edges
7. `get_projet()` - 34 edges
8. `controle_soldes_anormaux()` - 32 edges
9. `_result_ok()` - 25 edges
10. `_result_exception()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Routes FastAPI — toutes les routes de l'application.` --rationale_for--> `API Routes`  [EXTRACTED]
  probare/apps/engine/probare_engine/api/routes.py → CLAUDE.md
- `Planification Page` ----> `Planification`  [EXTRACTED]
  index.html → CLAUDE.md
- `Controles Page` ----> `Controles`  [EXTRACTED]
  index.html → CLAUDE.md
- `Electron App` ----> `FastAPI Sidecar`  [EXTRACTED]
  index.html → CLAUDE.md
- `test_get_donnees_segmentees_avec_releve()` --calls--> `_get_donnees_segmentees()`  [INFERRED]
  probare/apps/engine/tests/test_new_features.py → probare/apps/engine/probare_engine/api/routes.py

## Import Cycles
- 1-file cycle: `probare/apps/engine/probare_engine/controls/engine.py -> probare/apps/engine/probare_engine/controls/engine.py`

## Hyperedges (group relationships)
- **Trois anomalies MARSA (A1+A2+A3) dépassent le seuil et dictent l'opinion d'audit** — converted_marsa_distribution_dossier_audit_complet_f3c1b207_anomalie_a1_cutoff_ventes, converted_marsa_distribution_dossier_audit_complet_f3c1b207_anomalie_a2_facture_non_parvenue, converted_marsa_distribution_dossier_audit_complet_f3c1b207_anomalie_a3_depreciation_insuffisante, converted_marsa_distribution_dossier_audit_complet_f3c1b207_seuil_signification, converted_marsa_distribution_dossier_audit_complet_f3c1b207_phase5_opinion_rapport [EXTRACTED 1.00]
- **Probare génère les notes de planification IYYIU, NNNN et TEST selon NEP 300** — converted_marsa_distribution_dossier_audit_complet_f3c1b207_probare, converted_note_planification_iyyiu_2026_7ab3b867_note_planification, converted_note_planification_nnnn_2026_53cda848_note_planification, converted_note_planification_test_2026_c58b3693_note_planification [EXTRACTED 1.00]
- **Comptabilité DALOL et liasse justificatifs forment le dossier complet audit DALOL 2025** — converted_dalol_trading_comptabilite_et_pieces_2025_c8de31d6_dalol_trading_sarl, converted_dalol_trading_pieces_justificatives_2025_d4502a35_liasse_pieces, converted_sans_nom_2_43735581_balance_generale_dalol [INFERRED 0.85]

## Communities (64 total, 12 thin omitted)

### Community 0 - "API Routes Core"
Cohesion: 0.06
Nodes (73): _aggreger_soldes_nets(), _auto_interpreter(), _get_donnees_segmentees(), list_exceptions(), _parse_valeur(), Lance les 9 contrôles déterministes du cycle achats-fournisseurs., Lance les 10 contrôles déterministes du cycle ventes-clients., Lance l'interprétation IA automatique de toutes les exceptions. (+65 more)

### Community 1 - "Dossier Audit DALOL"
Cohesion: 0.05
Nodes (48): Balance âgée clients DALOL au 31/12/2025, Balance auxiliaire fournisseurs DALOL au 31/12/2025, Balance générale DALOL au 31/12/2025, Bilan et compte de résultat DALOL 2025, DALOL Trading SARL, Factures fournisseurs reçues janvier 2026 DALOL (cut-off), Tableau des immobilisations et amortissements DALOL 2025, Inventaire physique des stocks DALOL au 31/12/2025 (+40 more)

### Community 2 - "LLM Claude Client"
Cohesion: 0.06
Nodes (23): _now(), Implémentation Claude de LLMClient — SDK anthropic., Analyse la réponse du tiers et explique l'écart (le cas échéant).          Les, Haiku identifie la nature d'un document déposé pour l'audit., Rédige la conclusion du sondage (NEP 530).          Tous les chiffres provienn, Rédige une feuille de travail à partir de résultats déjà calculés., Haiku analyse chaque onglet d'un Excel et identifie sa nature., Haiku identifie les frontières de documents dans une liasse PDF/Word. (+15 more)

### Community 3 - "API Routes Calculs"
Cohesion: 0.08
Nodes (41): API Routes, calculer_variations(), CalculVariationsBody, CircularisationBody, create_circularisation(), create_client(), create_projet(), create_risque() (+33 more)

### Community 4 - "API Routes Documents"
Cohesion: 0.07
Nodes (39): analyser_annexe(), analyser_reponse_circularisation(), cataloguer_document_brut(), cataloguer_tous_documents_bruts(), conclure_sondage(), extraire_document_brut(), extraire_tous_documents_bruts(), generer_lettre_circularisation() (+31 more)

### Community 5 - "API Routes Preconditions"
Cohesion: 0.06
Nodes (31): _get_type_fichier(), _preconditions_check(), Retourne le type document prioritaire (type_document > type, compatibilité rétro, Vérifie que les fichiers requis pour ce contrôle sont présents., checklist_documents(), preconditions_ok(), Définition des types de documents et préconditions des contrôles., Retourne l'ensemble des types de documents présents dans la liste de fichiers. (+23 more)

### Community 6 - "Assertions & Cadrage"
Cohesion: 0.06
Nodes (39): Assertions audit, Cadrage, Cartographie des risques, Claude Haiku, Claude Sonnet, Controles, Controls Module, Cycle Achats-Fournisseurs (+31 more)

### Community 7 - "Circularisation"
Cohesion: 0.10
Nodes (15): calculer_ecart(), _get_amount(), _get_str(), proposer_tiers(), Circularisation — NEP 505 : Confirmation externe.  Toute l'arithmétique est ic, Sélectionne les N tiers avec le solde absolu le plus élevé.      Retourne une, Calcule l'écart entre le solde comptable et le solde confirmé par le tiers., RowDict (+7 more)

### Community 8 - "Controles Engine"
Cohesion: 0.13
Nodes (11): controle_equilibre_balance(), controle_rapprochement_bancaire(), controle_sequence_pieces(), TRESOR-BAL-EQUIL : Σ débits = Σ crédits., Détection de trous et doublons dans les numéros de pièces., TRESOR-RAPPROCH : solde comptable vs solde relevé bancaire., DonneeSourcee, _ds_piece() (+3 more)

### Community 10 - "Tests Controls"
Cohesion: 0.11
Nodes (8): _rows(), TestCutOff, TestSoldesAnomauxDettes, TestSoldesAnomauxImmobilisations, TestSoldesAnomauxTva, TestStocksRound, TestStocksSoldesAnormaux, TestTaxeCutOff

### Community 11 - "UI Sidebar Layout"
Cohesion: 0.12
Nodes (19): NavItemDef, navItems, PipelineProgress(), projetNavItems, Sidebar(), cn(), ETAT_ALIAS, EtatPipeline (+11 more)

### Community 12 - "Sondages Controls"
Cohesion: 0.13
Nodes (12): calculer_taille_echantillon(), _get_amount(), _get_str(), projeter_erreur(), Sondages sur pièces — NEP 530 : Sondage en audit.  Toute l'arithmétique est ic, Projette les anomalies constatées dans l'échantillon à la population entière., Formule Neyman simplifiée (NEP 530).      n = (Z² × p × (1-p)) / e²   puis cor, Sélectionne n éléments au hasard parmi les lignes correspondant aux préfixes. (+4 more)

### Community 13 - "UI Planification"
Cohesion: 0.09
Nodes (14): AGREGATS, ASSERTIONS, CYCLES, Dirigeant, FichierSource, FORMES_JURIDIQUES, InterpretationVariations, NIVEAUX (+6 more)

### Community 14 - "Tests Coherence"
Cohesion: 0.14
Nodes (6): _make_row(), Crée une liste de DonneeSourcees simulant une ligne de GL ou balance., TestCoherenceCycle, TestGroupRows, TestSoldesAnormaux, TestStocksCutOff

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (21): decouper_liasse(), delete_circularisation(), delete_document_brut(), delete_fichier(), delete_programme_item(), delete_risque(), delete_sondage(), exporter_dossier() (+13 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (19): _get_documents_attendus(), get_documents_requis(), get_etat(), get_onglets_excel(), get_planification(), get_programme(), get_projet(), importer_onglet() (+11 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (3): Any, _now(), SQLite storage — un fichier par projet.

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (12): useToast, formatDate(), Cadrage(), CYCLES_DISPONIBLES, ResultatRow(), ExceptionCard(), Exceptions(), severiteLabel (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (16): enregistrer_reponse_circularisation(), importer_document_brut(), _now(), Upload d'un document brut (PDF, image, Excel, CSV, Word...)., Convertit l'extraction d'un document brut en DonneeSourcee importables., Exporte le dossier complet en ZIP (SQLite + fichiers). Archive téléchargeable., Restaure un dossier depuis un ZIP exporté. Refuse si le projet existe déjà., Enregistre le solde confirmé par le tiers et calcule l'écart (Python). (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.19
Nodes (15): DataFrame, _coerce_value(), _detect_column_mapping(), _detect_header_row(), lire_fichier(), _now(), Ingestion Excel/CSV → DonneeSourcee avec provenance complète., Scanne les premières lignes pour trouver la ligne d'en-tête réelle.     Retourne (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (15): Any, Path, generer_dossier_travail(), generer_note_planification(), _now(), ProvenanceError, Export dossier de travail (docx) et tableaux (xlsx) avec contrôle de provenance., Levée si un chiffre sans source est détecté dans un livrable. (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (5): controle_creances_echues(), VENTE-CREANCES-ECHUES : détecte les créances clients (41x) dont la date     d'é, Grand livre ventes avec créances anciennes et concentration client., TestCreancesEchues, TestScenarioVentesRisquees

### Community 23 - "Community 23"
Cohesion: 0.19
Nodes (5): controle_concentration_compte(), Détecte une concentration des flux sur un seul compte (fournisseur ou client)., Grand livre achats avec doublon, concentration et avoirs anormaux., TestConcentrationCompte, TestScenarioAchatsFrauduleux

### Community 24 - "Community 24"
Cohesion: 0.21
Nodes (5): controle_ratio_charges_sociales(), PAIE-RATIO-SOCIAL : ratio cotisations patronales (645x) / salaires bruts (641x)., Paie régulière sur 12 mois avec bonne structure., TestRatioChargesSociales, TestScenarioPayeComplete

### Community 25 - "Community 25"
Cohesion: 0.35
Nodes (9): DonneeSourcee, _ds(), _ds_compte(), _ds_credit(), _ds_date(), _ds_debit(), _ds_libelle(), _ds_solde() (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.23
Nodes (5): controle_amort_excedent(), IMO-AMORT-EXCEDENT : détecte si les amortissements cumulés (28xx) dépassent, Immobilisations avec sous-amortissement et excédent., TestAmortExcedent, TestScenarioImmobilisationsComplet

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (7): useApi, DocRequis, FichierCard(), FichierImporte, getFileIcon(), OngletAnalyse, statutBadge()

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (8): Circ, Cycle, CYCLE_PREFIXES, CYCLES, Sondage, SondageElement, STATUT_CIRC_CLASS, STATUT_CIRC_LABEL

### Community 29 - "Community 29"
Cohesion: 0.25
Nodes (5): controle_soldes_anormaux_tresorerie(), TRESOR-SOLDE-ANORMAL : comptes 5xx avec solde net créditeur., Trésorerie sans anomalie., TestScenarieTresorerieClean, TestSoldesAnomauxTresorerie

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (6): useSyncProjet, CYCLE_META, CycleQCI, EvaluationCI(), NIVEAU_CONFIG, Question

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (8): Layout, Controles(), CyclePanel(), Ingestion(), NotFound, Planification, App(), useProjetStore

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (6): 15x crédité mais 68x absent → exception., 15x crédité ET 68x débité en proportion suffisante., Charges 68x très inférieures aux dotations 15x → exception., Pas de provision → OK (contrôle non applicable)., Compte 15x présent mais sans crédit sur la période., TestMouvementProvisions

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (6): Seul le compte 120 est non nul → cohérent., Seul le compte 129 est non nul → cohérent., Les deux comptes non nuls simultanément → exception., Pas de compte 120/129 dans les données → OK., Comptes 120 et 129 à zéro → OK., TestCoherenceResultat

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (9): archiver_projet(), calculer_seuils(), CalculSeuilsBody, desarchiver_projet(), Archive un dossier clôturé — lecture seule, non modifiable., Réouvre un dossier archivé pour modification., Calcule les seuils depuis un agrégat et les applique au projet (PLA-04 + PLA-05), update_projet() (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.36
Nodes (3): controle_mensualite_paie(), PAIE-MENSUALITE : vérifie la régularité des paiements mensuels de salaires (641x, TestMensualitePaie

### Community 37 - "Community 37"
Cohesion: 0.36
Nodes (3): controle_ratio_avoirs(), Détecte un ratio avoirs/total anormal.     - Avoirs fournisseurs : mouvements d, TestRatioAvoirs

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (9): Alerte critique — Réserves 20 M FDJ en premier exercice NNNN, Entité NNNN — SA exercice 2026, Note de planification audit NNNN 2026 (NEP 300), Cartographie des risques NNNN 2026 (10 risques, 4 élevés), Seuil de signification NNNN 2026 (5 880 000 FDJ), Incohérence variation stocks compte 6037 vs compte 37 — entité TEST, Note de planification audit TEST 2026 (NEP 300), Cartographie des risques TEST 2026 (12 risques, 6 élevés) (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (7): evaluer_qci(), get_qci(), Retourne les questions QCI et les réponses existantes pour tous les cycles du pr, Déclenche l'évaluation IA du contrôle interne pour un cycle., calculer_niveau_risque(), Questionnaire de Contrôle Interne (QCI) par cycle — NEP 315., Calcule le niveau de risque CI à partir des réponses.     reponses : [{question

### Community 40 - "Community 40"
Cohesion: 0.39
Nodes (3): controle_amortissement_manquant(), IMO-AMORTISSEMENT : détecte des immobilisations amortissables (21x-25x) sans, TestAmortissementManquant

### Community 41 - "Community 41"
Cohesion: 0.39
Nodes (3): controle_tva_coherence(), TAXE-TVA-COHERENCE : vérifie que la TVA déductible (4456x) ne dépasse pas anorma, TestTvaCoherence

### Community 42 - "Community 42"
Cohesion: 0.32
Nodes (7): ProjectDB, peut_transitionner(), PipelineError, Machine à états du pipeline d'audit., Effectue une transition d'état, journalise, et renvoie le projet mis à jour., Retourne (peut, raison_si_non)., transition()

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (7): create_sondage(), _cycle_prefixes(), proposer_tiers_circularisation(), Propose les N tiers à circulariser pour un cycle donné., Retourne les préfixes de compte standard pour un cycle., Crée un sondage et calcule la taille d'échantillon recommandée (Python)., SondageCreateBody

### Community 44 - "Community 44"
Cohesion: 0.38
Nodes (4): findFreePort(), ping(), startSidecar(), waitForSidecar()

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (6): DocumentAnnexe, DocumentRequis, FichierSource, Projet, ProjetStore, ResultatControle

### Community 46 - "Community 46"
Cohesion: 0.60
Nodes (4): ControleDefinition, enregistrer(), get_controles_par_cycle(), Registre des contrôles déterministes — NEP en données, pas en dur.

### Community 49 - "Community 49"
Cohesion: 0.40
Nodes (3): Capital (101) créditeur → normal., Capital (101) débiteur → capitaux propres négatifs → exception., TestSoldesAnomauxCapitauxPropres

## Knowledge Gaps
- **103 isolated node(s):** `ElectronAPI`, `Layout`, `ToastContainer`, `ToastType`, `Toast` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `API Routes` connect `API Routes Calculs` to `API Routes Core`, `API Routes Documents`, `API Routes Preconditions`, `Assertions & Cadrage`, `Circularisation`, `Controles Engine`, `Storage Database`, `Sondages Controls`, `Community 15`, `Community 16`, `Community 17`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 26`, `Community 29`, `Community 35`, `Community 36`, `Community 37`, `Community 39`, `Community 40`, `Community 41`, `Community 42`, `Community 43`?**
  _High betweenness centrality (0.676) - this node is a cross-community bridge._
- **Why does `Exception` connect `Community 21` to `Community 18`, `Community 42`, `Community 45`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Why does `ProjectDB` connect `Storage Database` to `Community 32`, `API Routes Calculs`, `Community 42`, `Community 15`, `Community 47`, `Community 17`, `Community 48`, `Community 50`, `Community 51`, `Community 52`, `Community 54`, `Community 53`, `Community 55`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **What connects `ElectronAPI`, `Layout`, `ToastContainer` to the rest of the system?**
  _268 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Routes Core` be split into smaller, more focused modules?**
  _Cohesion score 0.06281920326864147 - nodes in this community are weakly interconnected._
- **Should `Dossier Audit DALOL` be split into smaller, more focused modules?**
  _Cohesion score 0.051418439716312055 - nodes in this community are weakly interconnected._
- **Should `LLM Claude Client` be split into smaller, more focused modules?**
  _Cohesion score 0.06262626262626263 - nodes in this community are weakly interconnected._
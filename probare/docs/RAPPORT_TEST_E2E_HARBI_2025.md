# Rapport de test de bout en bout — Probare MVP

**Mission simulée :** audit des comptes 2025 de HARBI MATÉRIAUX SARL (société fictive, Djibouti)
**Rôle joué :** auditeur junior suivant le guide `docs/COMMENT_UTILISER_PROBARE.md`
**Date :** 08/07/2026 — **Branche :** `claude/probare-audit-test-planning-bug-kvriwg`
**Journal détaillé pas à pas :** `docs/JOURNAL_TEST_E2E_HARBI_2025.md`

---

## 1. Objet et méthode

Deux objectifs :

1. **Corriger le bug signalé** : la note de planification affichait « 0 contrôle inclus sur 0 planifiés » (section 6) depuis le 23/06/2026, alors que des risques étaient bien détectés — et revenir à la qualité de la note IYYIU du 22/06 (synthèse complète).
2. **Tester tout le processus d'audit** du cadrage à l'opinion, sur un dossier neuf (les jeux Marsa/Dalol du dépôt n'ont pas été utilisés).

**Jeu de données.** Aucun dossier comptable réel complet (grand livre détaillé + balances N/N-1 + relevé bancaire) n'est disponible en libre accès sur internet — seuls des modèles et exercices existent. La société **HARBI MATÉRIAUX SARL** a donc été construite : grand livre 2025 en partie double (492 lignes, à-nouveaux inclus), balances 2025/2024 équilibrées et cohérentes par construction, relevé bancaire, dossier permanent. **7 anomalies ont été plantées volontairement** (oracle en § 5) — voir `test_data/Harbi_Materiaux/README.md`.

**Limite assumée : IA simulée.** L'environnement de test ne dispose d'aucune clé API Anthropic. Un **stub local** (`apps/engine/tests/stub_llm_server.py`) imite l'API `/v1/messages` et renvoie des réponses JSON plausibles au format exact attendu par `llm/claude.py`. Tout le déterministe (ingestion, calculs, contrôles, seuils, machine à états, exports) est **réel** ; seul le contenu rédactionnel de l'IA est simulé. Les comportements LLM réels (troncature, JSON invalide) sont couverts par les tests unitaires de `tests/test_note_planification_regression.py`. Le stub est committé : il permet désormais de tester Probare hors ligne.

---

## 2. Le bug de la note de planification : diagnostic et correction

### Diagnostic (analyse de l'historique git et des trois notes .docx du dépôt)

| Note | Date | Section 6 | Section 7 |
|---|---|---|---|
| IYYIU | 22/06 12:33 | 8 contrôles / 8, paragraphe IA | Synthèse complète (4 sections + conclusion) |
| NNNN | 23/06 13:54 | 8 / 8 mais sans paragraphe IA | **« Note de synthèse » seul** |
| TEST | 25/06 07:59 | **« 0 contrôle inclus sur 0 »** | **« Note de synthèse » seul** |

Deux mécanismes, **tous deux des échecs silencieux du parsing de la réponse LLM** :

- `generer_note_synthese` : en cas de JSON illisible, retour du fallback `{"titre": "Note de synthèse", "sections": []}` **sans erreur**. Comme les paragraphes IA des sections 2, 3, 4 et 6 de la note sont extraits de ces `sections`, toute la rédaction disparaît (visible dès NNNN).
- `generer_programme_travail` : `max_tokens=4000` ; or le 23/06 le registre est passé de 27 à **52 contrôles (8 cycles)**. La réponse JSON (un item par contrôle) dépasse la limite → JSON tronqué → `return []` **silencieux** → la route **effaçait le programme existant**, sauvait 0 items, et la note sortait « 0 sur 0 » (visible sur TEST, qui couvrait 4 cycles ; NNNN, mono-cycle, y avait échappé).

### Correctifs (`llm/claude.py`, `api/routes.py`)

- `max_tokens` relevés : programme 4000 → 16000, synthèse 4000 → 8000 ;
- détection de `stop_reason == "max_tokens"` → erreur explicite « réponse tronquée » (plus jamais de troncature muette) ;
- JSON illisible ou synthèse sans sections → erreur explicite au lieu du fallback vide ;
- la route `generer-programme` **ne supprime plus le programme existant** tant que la réponse IA n'est pas validée (réponse vide → 502, programme conservé) ;
- la route `generer-synthese` refuse de produire le .docx sans programme inclus ; erreurs journalisées dans la piste d'audit ;
- **8 tests de régression** (troncature, JSON invalide, sections vides, liste vide).

### Preuve sur mission neuve

La note générée pour HARBI (voir `test_data/Harbi_Materiaux/exports/Note_Planification_HARBI_2025.docx`) affiche : **« 52 contrôle(s) inclus dans le programme sur 52 planifiés »**, les 8 cycles en tableaux, les paragraphes IA dans les sections 2/3/4/6 et la **section 7 complète** (4 sections + conclusion + signature) — le format de la note IYYIU est retrouvé.

---

## 3. Déroulé du test (résumé — détail dans le journal)

| Phase | Contenu | Résultat |
|---|---|---|
| 0. Démarrage | moteur + stub, `/health`, `/config` (référentiel ISA) | OK |
| 1. Cadrage | création mission 8 cycles, consentement IA, checklist documents | OK |
| 2. Contrôle interne | QCI des 8 cycles (80 réponses), évaluation IA par cycle | OK (voir constat C13) |
| 3. Ingestion | 4 CSV + 1 annexe .docx ; mapping colonnes auto ; anti-doublon vérifié (409) | OK |
| 4. Planification | fiche entité, variations N/N-1 (17 significatives), seuil 1 385 891 FDJ (1 % total bilan), 9 risques validés, programme 52 contrôles, note .docx | OK après correctif C1 |
| 5. Substantifs | 84 résultats de contrôles sur 8 cycles | 55 exceptions → **25 après correctifs C2/C3** |
| 6. Exceptions ISA 450 | 25 interprétations IA + 25 tranchements signés (2 non corrigées) | OK |
| 7. ISA 505 / 530 | circularisation 411 (lettre, envoi, réponse, analyse d'écart), sondage ventes (tirage, pointage, conclusion) | OK (constats C7, C8, C12) |
| 8. Revue → opinion | garde ISA 450 **bloque** à 2 352 500 > seuil ; correction client → cumul 12 500 → passage ; feuilles de travail, dossier .docx, exceptions .xlsx ; état final `opinion` | OK |

Piste d'audit finale : **237 événements** (23 transitions, 52 actions humaines, 146 appels LLM, calculs).

---

## 4. Constats

### Bugs corrigés pendant le test (commits de la branche)

| # | Sévérité | Constat | Correctif |
|---|---|---|---|
| C1 | **Majeure** | Note de planification « 0 sur 0 » + synthèse vide (§ 2) | `llm/claude.py`, `api/routes.py` + 8 tests |
| C2 | **Majeure** | **Balance N-1 fusionnée dans les contrôles** : tous les fichiers de type « balance » (N et N-1) étaient sommés → faux écarts GL/Balance sur chaque compte, soldes N doublés dans les variations. 30 des 55 exceptions du premier passage étaient de faux positifs de ce seul fait | `_get_donnees_segmentees` exclut la balance N-1 référencée en planification |
| C3 | Élevée | `TRESOR-RAPPROCH` passait la donnée **numéro de compte** (512) comme solde comptable : « Écart=33 564 418, Comptable=512.00 ». Après correctif : écart = **850 000**, la valeur plantée exacte | la source du solde est désormais la donnée montant |
| C4 | Élevée | **Fiche entité perdue** : le premier `PATCH fiche-entite` (avant tout GET) renvoyait 200 sans rien persister (`UPDATE` sur ligne inexistante = no-op). L'UI masque le bug (elle fait un GET d'abord) mais la note sortait « Forme juridique : — » | `update_planification` crée la ligne si absente + test |

### Constats ouverts (non corrigés — à prioriser)

| # | Sévérité | Constat | Recommandation |
|---|---|---|---|
| C5 | Élevée | **Grand livre en partie double mal supporté par les contrôles de séquence** : chaque pièce figurant sur ses 2 lignes, `TRESOR/VENTE-SEQ` signalent « 236 doublons » (faux). `VENTE-SEQ-FACTURES` ne filtre même pas par cycle (toutes les pièces du GL). Le vrai doublon (pièce 5115) et le vrai trou (5087) sont bien détectés, mais noyés | dédupliquer les numéros de pièce par écriture avant l'analyse de séquence ; filtrer par cycle |
| C6 | Élevée | **`*-AVOIR` faux positifs massifs en partie double** : les crédits 411 (encaissements) / débits 401 (règlements) sont comptés comme « avoirs » → ratios 81-86 % dénués de sens | identifier les avoirs par libellé/pièce ou exiger un journal des ventes dédié |
| C7 | Élevée | **Circularisation : la proposition de tiers renvoie des comptes de produits (701)** avec des soldes agrégés incohérents (-551 M) ; sans balance auxiliaire, « le plus gros solde clients » n'est pas un tiers | restreindre aux comptes 40x/41x/5x et prévoir l'import d'une balance auxiliaire |
| C8 | Moyenne | Un statut de circularisation invalide (« envoyee ») produit une **500 brute** (IntegrityError SQLite) au lieu d'un 400 explicite | valider le statut dans le modèle Pydantic |
| C9 | Moyenne | `VENTE-CREANCES-ECHUES` cumule les **débits bruts sans lettrage** : 71 % de créances « anciennes » alors que la seule vraiment ancienne est la facture litigieuse de 2 447 350 (A6, détectée mais surévaluée ×65) | lettrer débits/crédits par montant ou par pièce avant le calcul d'ancienneté |
| C10 | Moyenne | `IMO-AMORTISSEMENT` vérifie l'existence d'amortissements 28x **en global** : le compte 218 (9,9 M brut, aucun 2818) passe inaperçu grâce au 2815 → **anomalie plantée A5 non détectée** | apparier brut/amortissement par sous-compte (215↔2815, 218↔2818) |
| C11 | Moyenne | `*-CONCENTRATION` mesure la concentration **par compte** : avec des comptes collectifs 401/411 uniques, il conclut mécaniquement « 100 % sur un tiers » | neutraliser le contrôle en l'absence de comptes auxiliaires |
| C12 | Moyenne | Sondages : `niveau_confiance` attendu **entier** (95) alors que le guide parle de niveau de confiance (0,95 rejeté en 422) ; échantillon calculé de taille 1 sans que population ni graine soient renvoyées dans la réponse | homogénéiser les unités et documenter ; renvoyer population/graine |
| C13 | Moyenne | QCI déclaratif indulgent : profil « comptable unique, pas de séparation des tâches » → risque CI « faible » sur les 8 cycles (score ≥ 0,70 = faible) ; les questions de séparation des tâches pèsent peu | pondérer les questions critiques ou plafonner le score si certaines réponses clés sont « non » |
| C14 | Moyenne | Le prompt `proposer_risques` limite les cycles valides à `tresorerie, achats, ventes, transversal` alors que 8 cycles existent : l'IA ne peut jamais proposer un risque ciblant stocks/immobilisations/paie/impôts/capitaux propres | mettre à jour le prompt avec les cycles couverts par la mission |
| C15 | Faible | Les contrôles s'exécutent quel que soit l'état du pipeline (exécutés avec succès à l'état `cadrage`) ; la chaîne réelle (`cadrage → evaluation_ci → ingestion → planification → travaux_substantifs → revue → generation → opinion`) diffère de celle de `CLAUDE.md` et n'est pas dans le guide | soit bloquer, soit journaliser un avertissement ; mettre à jour la documentation |
| C16 | Faible | Le solde du relevé bancaire est extrait comme « plus grand montant du fichier » : fragile (ici, il attrape le solde du 31/12 *avant* les frais → écart mesuré 850 000 au lieu du vrai 837 500) | prendre le solde de la dernière ligne datée, ou demander le solde de clôture à l'import |

---

## 5. Verdict sur l'oracle (anomalies plantées)

| # | Anomalie plantée | Détection | Verdict |
|---|---|---|---|
| A1 | Chèque 850 000 non débité + frais 12 500 non comptabilisés | `TRESOR-RAPPROCH` : écart 850 000 (après C3) | ✅ (les 12 500 restent à trouver au relevé — voulu) |
| A2 | Facture fournisseur saisie 2× (pièce 5115, 2 340 000) | `ACHAT-DOUBLON` : « Pièce 5115, Montant 2 340 000, 2 fois » | ✅ |
| A3 | Trou de séquence (pièce 5087) | `TRESOR/ACHAT/VENTE-SEQ` : « Trous : [5087] » | ✅ (mais noyé dans les faux doublons — C5) |
| A4 | Concentration de ventes fin décembre | `VENTE-CUT-OFF` : 13/52 lignes 70x = 25 % < seuil 30 % | ❌ non déclenché (dénominateur = toutes les lignes 70x, pas seulement les factures — et calibrage du jeu à durcir) |
| A5 | Immobilisation 218 sans amortissement | `IMO-AMORTISSEMENT` : OK à tort | ❌ non détecté (C10) |
| A6 | Créance ancienne 2 447 350 (litige) non dépréciée | `VENTE-CREANCES-ECHUES` : détecte mais annonce 71 % | ⚠️ détecté, très surévalué (C9) |
| A7 | Variations N/N-1 marquées (CA +30 %, stocks +38 %, marge ×2,4) | `*-VARIATION` : 11 exceptions chiffrées justes (après C2) | ✅ |

**Score brut : 4/7 pleinement détectées, 1 partielle, 2 manquées** — les deux manques ont des causes précises et corrigeables (C10, et dénominateur du cut-off).

## 6. Appréciation générale

Le processus **tient de bout en bout** : la machine à états guide correctement la mission, l'anti-doublon d'import, le blocage sans seuil de signification et surtout la **garde ISA 450** (blocage du passage en génération à 2 352 500 > 1 385 891, déblocage après enregistrement de la correction client) fonctionnent exactement comme le décrit le guide. La piste d'audit est riche et exploitable. Les livrables (note de planification, dossier de travail, tableau des exceptions) sont produits et structurés.

Le point faible dominant est la **robustesse des contrôles face à un vrai export comptable en partie double avec comptes collectifs** : environ la moitié des exceptions restantes sont des faux positifs de format (C5, C6, C9, C11). C'est le chantier prioritaire avant de mettre le produit devant un cabinet — un auditeur qui reçoit 20 fausses alertes pour 5 vraies cessera vite de les lire.

---

*Rapport rédigé automatiquement à l'issue du test. Reproduction : `python tests/stub_llm_server.py 8799` puis `ANTHROPIC_API_KEY=stub ANTHROPIC_BASE_URL=http://127.0.0.1:8799 uvicorn probare_engine.main:app --port 8767`, jeu de données `test_data/Harbi_Materiaux/` (générateur rejouable `generer_harbi.py`).*

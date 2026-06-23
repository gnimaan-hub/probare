# Graph Report - D:/projet/Audit_Comptable  (2026-06-22)

## Corpus Check
- 86 files · ~80,350 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 68 nodes · 42 edges · 35 communities (7 shown, 28 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Planification & Risques|Planification & Risques]]
- [[_COMMUNITY_Contrles & Cycles Audit|Contr?les & Cycles Audit]]
- [[_COMMUNITY_Infrastructure Backend|Infrastructure Backend]]
- [[_COMMUNITY_Frontend React Pages|Frontend React Pages]]
- [[_COMMUNITY_Pipeline tats|Pipeline ?tats]]
- [[_COMMUNITY_LLM & IA|LLM & IA]]
- [[_COMMUNITY_Donnes & Traabilit|Donn?es & Tra?abilit?]]
- [[_COMMUNITY_Hook API|Hook API]]
- [[_COMMUNITY_Hook Projet|Hook Projet]]
- [[_COMMUNITY_Hook Toast|Hook Toast]]
- [[_COMMUNITY_Module 10|Module 10]]
- [[_COMMUNITY_Module 11|Module 11]]
- [[_COMMUNITY_Module 12|Module 12]]
- [[_COMMUNITY_Module 13|Module 13]]
- [[_COMMUNITY_Module 14|Module 14]]
- [[_COMMUNITY_Module 15|Module 15]]
- [[_COMMUNITY_Module 16|Module 16]]
- [[_COMMUNITY_Module 17|Module 17]]
- [[_COMMUNITY_Module 18|Module 18]]
- [[_COMMUNITY_Module 19|Module 19]]
- [[_COMMUNITY_Module 20|Module 20]]
- [[_COMMUNITY_Module 21|Module 21]]
- [[_COMMUNITY_Module 22|Module 22]]
- [[_COMMUNITY_Module 23|Module 23]]
- [[_COMMUNITY_Module 24|Module 24]]
- [[_COMMUNITY_Module 25|Module 25]]
- [[_COMMUNITY_Module 26|Module 26]]
- [[_COMMUNITY_Module 27|Module 27]]
- [[_COMMUNITY_Module 28|Module 28]]
- [[_COMMUNITY_Module 29|Module 29]]
- [[_COMMUNITY_Module 30|Module 30]]
- [[_COMMUNITY_Module 31|Module 31]]
- [[_COMMUNITY_Module 32|Module 32]]
- [[_COMMUNITY_Module 33|Module 33]]
- [[_COMMUNITY_Module 34|Module 34]]

## God Nodes (most connected - your core abstractions)
1. `Planification` - 9 edges
2. `Controles` - 9 edges
3. `LLMClient` - 5 edges
4. `FastAPI Sidecar` - 5 edges
5. `React Frontend` - 5 edges
6. `Storage Module` - 4 edges
7. `Cadrage` - 2 edges
8. `Ingestion` - 2 edges
9. `Extraction` - 2 edges
10. `Revue` - 2 edges

## Surprising Connections (you probably didn't know these)
- `Planification Page` ----> `Planification`  [EXTRACTED]
  index.html → CLAUDE.md
- `Controles Page` ----> `Controles`  [EXTRACTED]
  index.html → CLAUDE.md
- `Electron App` ----> `FastAPI Sidecar`  [EXTRACTED]
  index.html → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **audit_pipeline_sequence** — cadrage, ingestion, extraction, planification, controles, revue, generation, opinion [EXTRACTED]
- **audit_cycles_covered** — cycle_tresorerie, cycle_achats, cycle_ventes [EXTRACTED]

## Communities (35 total, 28 thin omitted)

### Community 0 - "Planification & Risques"
Cohesion: 0.22
Nodes (9): Assertions audit, Cartographie des risques, NEP 300, NEP 315, NEP 320 / ISA 320, Planification, Programme de travail, Risque audit (+1 more)

### Community 1 - "Contr?les & Cycles Audit"
Cohesion: 0.25
Nodes (8): Controles, Cycle Achats-Fournisseurs, Cycle Tresorerie, Cycle Ventes-Clients, Generation, NEP 330, Opinion, Revue

### Community 2 - "Infrastructure Backend"
Cohesion: 0.33
Nodes (6): API Routes, Controls Module, Electron App, FastAPI Sidecar, Planning Module, controls/registry.py

### Community 3 - "Frontend React Pages"
Cohesion: 0.40
Nodes (5): Cadrage Page, Controles Page, Dashboard Page, Planification Page, React Frontend

### Community 4 - "Pipeline ?tats"
Cohesion: 0.50
Nodes (4): Cadrage, Extraction, Ingestion, StateMachine Module

### Community 5 - "LLM & IA"
Cohesion: 0.50
Nodes (4): Claude Haiku, Claude Sonnet, LLMClient, LLM Philosophy

### Community 6 - "Donn?es & Tra?abilit?"
Cohesion: 0.50
Nodes (4): DonneeSourcee, Journal audit, SQLite per-project DB, Storage Module

## Knowledge Gaps
- **49 isolated node(s):** `startSidecar`, `stopSidecar`, `getSidecarPort`, `waitForSidecar`, `ElectronAPI` (+44 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Planification` connect `Planification & Risques` to `Contr?les & Cycles Audit`, `Frontend React Pages`, `Pipeline ?tats`, `LLM & IA`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Why does `React Frontend` connect `Frontend React Pages` to `Infrastructure Backend`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `Controles` connect `Contr?les & Cycles Audit` to `Planification & Risques`, `Frontend React Pages`, `LLM & IA`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **What connects `startSidecar`, `stopSidecar`, `getSidecarPort` to the rest of the system?**
  _49 weakly-connected nodes found - possible documentation gaps or missing edges._
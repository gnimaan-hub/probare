# -*- coding: utf-8 -*-
"""Stub local de l'API Anthropic pour tester Probare SANS clé API ni réseau.

Usage :
    python tests/stub_llm_server.py [port]           # défaut : 8799
puis lancer le moteur avec :
    ANTHROPIC_API_KEY=stub ANTHROPIC_BASE_URL=http://127.0.0.1:8799 uvicorn probare_engine.main:app

Le stub reconnaît chaque type d'appel LLM de Probare par des marqueurs du
prompt et renvoie un JSON plausible, en français, au format exact attendu par
`llm/claude.py`. Tout le déterministe (calculs, contrôles) reste réel : seul
le contenu rédactionnel est simulé. NE PAS utiliser en production — outil de
test de plomberie uniquement.
"""
from __future__ import annotations
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# ─── Répondeurs par type d'appel ─────────────────────────────────────────────

def rep_mapper_colonnes(prompt: str) -> dict:
    m = re.search(r"fichier comptable :\n(\[.*?\])\n", prompt, re.S)
    colonnes = json.loads(m.group(1)) if m else []
    cibles = ["compte", "libelle", "debit", "credit", "date", "numero_piece", "solde", "exercice"]
    mapping = {}
    for col in colonnes:
        k = col.strip().lower().replace("é", "e").replace("è", "e").replace(" ", "_")
        mapping[col] = k if k in cibles else "autre"
    return {"mapping": mapping, "confiance": 0.95, "notes": "Correspondance directe des intitulés."}


def rep_analyse_document(prompt: str) -> dict:
    m = re.search(r"Nom du fichier : (.+)", prompt)
    nom = (m.group(1) if m else "").lower()
    nature = "autre"
    if "grand" in nom or "livre" in nom:
        nature = "grand_livre"
    elif "balance" in nom:
        nature = "balance"
    elif "releve" in nom or "relevé" in nom or "bancaire" in nom:
        nature = "releve_bancaire"
    elif "permanent" in nom or "dossier" in nom:
        nature = "rapport"
    comptable = nature if nature in ("grand_livre", "balance", "releve_bancaire") else None
    return {
        "nature": nature,
        "type_comptable": comptable,
        "description": f"Document identifié par son intitulé et sa structure : {nature.replace('_', ' ')}.",
        "objectif": "Support des contrôles d'audit du ou des cycles concernés.",
        "correspond_a": comptable,
        "confiance": 0.9,
    }


def rep_onglets_excel(prompt: str) -> list:
    onglets = re.findall(r"--- Onglet : (.+?) ---", prompt)
    out = []
    for nom in onglets:
        n = nom.lower()
        nature = ("grand_livre" if "livre" in n or "gl" in n
                  else "balance" if "balance" in n
                  else "releve_bancaire" if "releve" in n or "banc" in n
                  else "autre")
        comptable = nature if nature != "autre" else None
        out.append({"nom_onglet": nom, "nature": nature, "type_comptable": comptable,
                    "description": f"Onglet identifié comme {nature}.",
                    "correspond_a": comptable, "confiance": 0.85,
                    "recommande_import": nature != "autre"})
    return out


def rep_liasse(_p: str) -> dict:
    return {"est_liasse": False, "nb_documents": 1, "documents": [],
            "description_globale": "Document unique, pas une liasse."}


def rep_evaluation_ci(prompt: str) -> dict:
    m = re.search(r"cycle (\w+)", prompt, re.I)
    cycle = m.group(1) if m else "concerné"
    faiblesses = []
    if "facturation" in prompt.lower() or "séparation" in prompt.lower():
        faiblesses.append("Absence de séparation des tâches entre facturation, encaissement et comptabilisation.")
    return {
        "synthese": (f"L'évaluation du contrôle interne du cycle {cycle} repose sur les réponses "
                     "au questionnaire ci-dessus. Les points de faiblesse identifiés appellent un "
                     "renforcement des travaux substantifs sur ce cycle, en particulier sur les "
                     "assertions d'exhaustivité et d'existence."),
        "forces": ["Supervision périodique par un cabinet d'expertise comptable externe.",
                   "Compte bancaire unique facilitant le suivi de trésorerie."],
        "faiblesses": faiblesses + [
            "Effectif comptable réduit à une personne : risque d'erreur ou de fraude non détectée.",
            "Facturation sous Excel ressaisie manuellement : risque d'exhaustivité."],
        "recommandations": [
            "Étendre les sondages sur les factures de vente ressaisies manuellement.",
            "Vérifier systématiquement le rapprochement bancaire de clôture."],
    }


def rep_synthese_globale_ci(prompt: str) -> dict:
    m = re.search(r"Entité : (.+?) —", prompt)
    client = m.group(1).strip() if m else "l'entité"
    m = re.search(r"Exercice (\S+)", prompt)
    exercice = m.group(1).strip() if m else "N"
    return {
        "titre": f"Synthèse de l'évaluation du contrôle interne — {client} — Exercice {exercice}",
        "sections": [
            {"titre": "1. Niveau de risque global",
             "contenu": ("À l'issue de l'évaluation du contrôle interne sur l'ensemble des cycles "
                         "sélectionnés, nous retenons un niveau de risque global qui oriente la mission "
                         "vers une approche essentiellement substantive : le dispositif déclaré ne permet "
                         "pas, en l'état et sans test d'efficacité, de réduire l'étendue de nos travaux.")},
            {"titre": "2. Analyse par cycle",
             "contenu": ("La matrice des risques fait ressortir une concentration du risque sur les cycles "
                         "où la séparation des tâches est absente et où la saisie comptable est manuelle. "
                         "Les cycles les mieux notés reposent sur des dispositifs simples mais tracés.")},
            {"titre": "3. Constats déterminants",
             "contenu": ("Les réponses « non » les plus pénalisantes portent sur la séparation des tâches, "
                         "la double signature des paiements et l'absence d'interface entre facturation et "
                         "comptabilité — autant de points qui fragilisent les assertions d'exhaustivité et "
                         "d'existence.")},
            {"titre": "4. Implications pour la suite de l'audit",
             "contenu": ("Nous étendrons les tests substantifs sur les cycles à risque élevé (contrôles de "
                         "détail, sondages élargis, circularisation des tiers), et concentrerons notre "
                         "vigilance sur la coupure et la recouvrabilité. Le programme de travail sera "
                         "dimensionné en conséquence.")},
        ],
        "conclusion": ("En synthèse, l'environnement de contrôle interne appelle une approche prudente : "
                       "nous ne nous appuierons pas sur les contrôles pour réduire nos diligences et "
                       "renforcerons les travaux substantifs sur les cycles porteurs de risque."),
    }


def rep_interpretation_exception(prompt: str) -> dict:
    m = re.search(r"Contrôle : ([A-Z0-9\-]+)", prompt)
    ref = m.group(1) if m else "INCONNU"
    catalogues = {
        "RAPPROCH": ("L'écart entre le solde comptable 512 et le solde du relevé bancaire correspond "
                     "typiquement à des éléments en rapprochement de fin d'exercice : chèques émis non "
                     "débités, virements en transit ou frais bancaires non comptabilisés.",
                     ["Chèque(s) émis fin décembre non encore débités par la banque.",
                      "Frais bancaires du dernier trimestre non enregistrés en comptabilité.",
                      "Virement client en transit au 31/12."],
                     ["Obtenir l'état de rapprochement bancaire au 31/12 préparé par le client.",
                      "Pointer les chèques émis en décembre avec le relevé de janvier N+1.",
                      "Vérifier la comptabilisation des frais bancaires du T4."]),
        "DOUBLON": ("Le moteur a détecté des écritures partageant le même compte, le même montant et le "
                    "même numéro de pièce : il peut s'agir d'une double saisie de la même facture.",
                    ["Double saisie de la même facture fournisseur à deux dates différentes.",
                     "Facture réémise par le fournisseur et enregistrée une seconde fois."],
                    ["Obtenir la facture d'origine et vérifier son unicité.",
                     "Demander une confirmation de solde au fournisseur concerné.",
                     "Vérifier si un avoir ou une annulation a été enregistré."]),
        "SEQ": ("La séquence des numéros de pièces présente des trous et/ou des doublons. Un trou peut "
                "correspondre à une pièce annulée non documentée ; des numéros répétés peuvent refléter "
                "le format en partie double du grand livre.",
                ["Pièce annulée ou supprimée sans trace dans le journal.",
                 "Grand livre en partie double : chaque pièce apparaît sur plusieurs lignes."],
                ["Demander la pièce manquante ou la preuve de son annulation.",
                 "Vérifier la politique de numérotation du logiciel comptable."]),
        "CUT-OFF": ("Une proportion anormalement élevée d'écritures est concentrée sur les derniers jours "
                    "de l'exercice, ce qui fait peser un risque de séparation des exercices sur le cycle.",
                    ["Ventes de N+1 anticipées sur N pour améliorer le chiffre d'affaires.",
                     "Rattrapage administratif de facturation en fin d'année."],
                    ["Contrôler les bons de livraison des factures des 15 derniers jours.",
                     "Vérifier les annulations/avoirs de janvier N+1."]),
        "CREANCES": ("Une part significative des créances clients a plus de 90 jours, sans dépréciation "
                     "constatée, ce qui interroge l'évaluation du poste clients.",
                     ["Litige commercial non provisionné.",
                      "Défaillance d'un client important.",
                      "Le contrôle lit les débits bruts sans lettrage : une partie peut être déjà réglée."],
                     ["Obtenir la balance âgée détaillée et le lettrage des comptes clients.",
                      "Analyser le litige mentionné au dossier permanent.",
                      "Apprécier la nécessité d'une dépréciation."]),
        "VARIATION": ("La variation N/N-1 du compte excède le seuil de signification : elle doit être "
                      "corroborée par des explications de la direction et des pièces probantes.",
                      ["Croissance réelle de l'activité.", "Changement de méthode ou reclassement.",
                       "Erreur de saisie ou de rattachement."],
                      ["Obtenir l'explication de la direction et les pièces sur les principaux mouvements.",
                       "Comparer avec les tendances sectorielles."]),
        "AMORT": ("Des immobilisations brutes ne portent aucun amortissement cumulé, ce qui n'est pas "
                  "conforme au rattachement des charges pour des biens en service.",
                  ["Omission de la dotation sur les acquisitions ou le compte concerné.",
                   "Biens comptabilisés mais non encore mis en service."],
                  ["Obtenir le tableau des immobilisations et vérifier les dates de mise en service.",
                   "Recalculer la dotation attendue sur le compte non amorti."]),
    }
    for cle, (exp, hyp, dil) in catalogues.items():
        if cle in ref:
            expl, hypotheses, diligences = exp, hyp, dil
            break
    else:
        expl = ("L'exception signalée par le moteur déterministe doit être corroborée par des pièces "
                "justificatives avant tout tranchement.")
        hypotheses = ["Erreur de saisie.", "Opération non documentée.", "Particularité du format des données."]
        diligences = ["Obtenir les pièces justificatives concernées.", "Interroger le comptable de l'entité."]
    return {
        "explication": expl,
        "hypotheses": hypotheses,
        "diligences": diligences,
        "decision_proposee": ("Sous réserve de l'obtention des pièces listées ci-dessus, il conviendra de "
                              "déterminer si cette exception peut être tranchée comme « sans incidence » "
                              "(explication probante obtenue), « corrigée » (écriture rectifiée par le "
                              "client) ou « non corrigée » avec chiffrage de l'incidence au regard du "
                              "seuil de signification."),
        "urgence": "elevee" if "RAPPROCH" in ref or "DOUBLON" in ref else "moyenne",
    }


def rep_annexe(_p: str) -> dict:
    return {
        "resume": ("Extrait du dossier permanent : présentation de la société, de son environnement "
                   "comptable (comptable unique, facturation Excel ressaisie), de son financement "
                   "(emprunt BCIMR) et des faits marquants 2025 dont un litige client non réglé."),
        "points_cles": ["Comptable unique, pas de séparation des tâches formalisée.",
                        "Facturation Excel ressaisie manuellement en comptabilité.",
                        "Litige client SOMACO TP (2 447 350 FDJ) non réglé à la clôture.",
                        "Croissance du CA d'environ +30 % sur l'exercice."],
        "alertes": ["Le litige client de février non réglé doit être rapproché des créances anciennes."],
    }


def rep_cataloguer(_p: str) -> dict:
    return {"type_detecte": "rapport", "description": "Document de présentation de la société (dossier permanent).",
            "parties": ["HARBI MATÉRIAUX SARL"], "dates": ["2025-12-31"], "montants_cles": [],
            "pertinence_audit": "moyenne"}


def rep_variations(prompt: str) -> dict:
    return {
        "synthese": ("L'analyse comparative N/N-1 confirme une croissance marquée de l'activité : le "
                     "chiffre d'affaires progresse d'environ un tiers, avec une progression parallèle "
                     "des achats. Les créances clients et les stocks augmentent plus vite que le chiffre "
                     "d'affaires, ce qui allonge le besoin en fonds de roulement et appelle des travaux "
                     "sur la recouvrabilité des créances et la réalité des stocks. La trésorerie "
                     "progresse fortement et le résultat net fait plus que tripler, améliorant la marge "
                     "nette de façon atypique pour un négoce de matériaux : la marge devra être "
                     "corroborée (exhaustivité des charges, séparation des exercices)."),
        "zones_risque": [
            {"cycle": "ventes", "libelle": "Créances clients en forte hausse (+41 %) et litige client",
             "niveau": "eleve", "explication": "Croissance des créances supérieure à celle du CA ; risque d'évaluation et de recouvrabilité."},
            {"cycle": "ventes", "libelle": "Concentration de facturation en fin d'exercice",
             "niveau": "eleve", "explication": "Risque de séparation des exercices (cut-off) sur les ventes de décembre."},
            {"cycle": "tresorerie", "libelle": "Solde bancaire en forte progression à rapprocher du relevé",
             "niveau": "moyen", "explication": "Le solde 512 doit être confirmé par le rapprochement bancaire et la confirmation banque."},
            {"cycle": "achats", "libelle": "Progression des achats et dettes fournisseurs",
             "niveau": "moyen", "explication": "Risque d'exhaustivité des charges et de doublons dans un contexte de ressaisie manuelle."},
            {"cycle": "transversal", "libelle": "Amélioration atypique de la marge nette",
             "niveau": "moyen", "explication": "La marge nette passe d'environ 5 % à plus de 11 % : cohérence à corroborer."},
        ],
        "facteurs_contextuels": ("Le secteur du négoce de matériaux à Djibouti bénéficie de chantiers "
                                 "publics : une croissance de l'activité est plausible, mais elle "
                                 "n'explique pas à elle seule l'amélioration de la marge nette."),
        "alertes": ["Stocks +38 % : inventaire physique à corroborer.",
                    "Créances anciennes non dépréciées à analyser (litige client au dossier permanent)."],
    }


def rep_risques(_p: str) -> dict:
    return {"risques": [
        {"libelle": "Séparation des exercices sur les ventes de décembre",
         "description": "Concentration de factures sur les 15 derniers jours de l'exercice ; des ventes de N+1 pourraient être rattachées à N.",
         "cycle": "ventes", "niveau": "eleve", "assertions": ["cut_off", "existence"], "source": "analytique"},
        {"libelle": "Recouvrabilité des créances clients anciennes",
         "description": "Créances de plus de 90 jours dont un litige connu, sans dépréciation comptabilisée.",
         "cycle": "ventes", "niveau": "eleve", "assertions": ["evaluation"], "source": "analytique"},
        {"libelle": "Éléments en rapprochement bancaire à la clôture",
         "description": "Le solde bancaire comptable doit être rapproché du relevé ; des éléments en transit peuvent masquer des erreurs.",
         "cycle": "tresorerie", "niveau": "eleve", "assertions": ["existence", "exhaustivite"], "source": "analytique"},
        {"libelle": "Double comptabilisation de factures fournisseurs",
         "description": "La ressaisie manuelle des factures augmente le risque de doublons de charges et de dettes.",
         "cycle": "achats", "niveau": "moyen", "assertions": ["existence", "exhaustivite"], "source": "entite"},
        {"libelle": "Exhaustivité des charges dans un contexte de marge atypique",
         "description": "L'amélioration marquée de la marge nette peut résulter de charges non comptabilisées.",
         "cycle": "transversal", "niveau": "moyen", "assertions": ["exhaustivite", "cut_off"], "source": "analytique"},
        {"libelle": "Réalité et valorisation du stock de clôture",
         "description": "Stocks en hausse de 38 % : l'inventaire physique et la valorisation doivent être corroborés.",
         "cycle": "transversal", "niveau": "moyen", "assertions": ["existence", "evaluation"], "source": "analytique"},
        {"libelle": "Manipulation des encaissements en espèces",
         "description": "Ventes au comptant en caisse remises en banque avec décalage : risque de détournement ou d'omission.",
         "cycle": "tresorerie", "niveau": "moyen", "assertions": ["exhaustivite"], "source": "entite"},
        {"libelle": "Fiabilité de la ressaisie de la facturation Excel",
         "description": "Absence d'interface entre facturation et comptabilité : risque d'erreurs d'exhaustivité et d'exactitude.",
         "cycle": "ventes", "niveau": "moyen", "assertions": ["exhaustivite"], "source": "entite"},
    ]}


def rep_reformuler(prompt: str) -> dict:
    m = re.search(r"- Libellé : (.+)", prompt)
    lib = (m.group(1).strip() if m else "Risque d'audit")[:78]
    return {"libelle": lib, "description": f"{lib} — risque reformulé pour homogénéité avec la cartographie.",
            "assertions": ["existence", "exhaustivite"]}


def rep_programme(prompt: str) -> dict:
    m = re.search(r"norme\) :\n(\[.*?\])\n\nPour chaque contrôle", prompt, re.S)
    registry = json.loads(m.group(1)) if m else []
    m2 = re.search(r"Risques validés par l'auditeur :\n(\[.*?\])\n\nCycles couverts", prompt, re.S)
    risques = json.loads(m2.group(1)) if m2 else []
    cycles_eleves = {r.get("cycle") for r in risques if r.get("niveau") == "eleve"}
    risque_par_cycle = {}
    for r in risques:
        risque_par_cycle.setdefault(r.get("cycle"), r.get("libelle"))
    items = []
    for c in registry:
        cyc = c.get("cycle")
        items.append({
            "controle_ref": c.get("ref"),
            "libelle": c.get("libelle"),
            "cycle": cyc,
            "risque_libelle": risque_par_cycle.get(cyc) or risque_par_cycle.get("transversal"),
            "priorite": "haute" if cyc in cycles_eleves else "normale",
            "statut": "inclus",
            "notes": "Contrôle retenu en réponse aux risques du cycle." if cyc in cycles_eleves else None,
        })
    return {"items": items}


def rep_synthese(prompt: str) -> dict:
    m = re.search(r"Client : (.+)", prompt)
    client = m.group(1).strip() if m else "l'entité"
    m = re.search(r"Exercice audité : (.+)", prompt)
    exercice = m.group(1).strip() if m else "N"
    return {
        "titre": f"Note de synthèse de planification — {client} — Exercice {exercice}",
        "sections": [
            {"titre": "1. Connaissance de l'entité",
             "contenu": (f"{client} est une société de négoce de matériaux de construction opérant sur le "
                         "marché local, avec un effectif restreint et une fonction comptable assurée par une "
                         "seule personne supervisée par un cabinet externe. La facturation est réalisée sous "
                         "Excel puis ressaisie en comptabilité, sans séparation des tâches formalisée : cet "
                         "environnement de contrôle interne limité oriente la mission vers une approche "
                         "essentiellement substantive.")},
            {"titre": "2. Résultats des procédures analytiques",
             "contenu": ("Les procédures analytiques préliminaires font ressortir une croissance marquée de "
                         "l'activité, une progression des créances clients et des stocks supérieure à celle "
                         "du chiffre d'affaires, et une amélioration atypique de la marge nette. Ces "
                         "évolutions concentrent l'attention sur la séparation des exercices, la "
                         "recouvrabilité des créances et l'exhaustivité des charges.")},
            {"titre": "3. Cartographie des risques et seuil de signification",
             "contenu": ("Les risques validés par l'auditeur couvrent principalement les cycles ventes "
                         "(cut-off, créances anciennes), trésorerie (rapprochement bancaire, espèces) et "
                         "achats (doublons de factures), avec des risques transversaux sur la marge et les "
                         "stocks. Le seuil de signification retenu, assis sur un agrégat représentatif de "
                         "l'activité, borne l'évaluation des anomalies relevées.")},
            {"titre": "4. Justification du programme de travail",
             "contenu": ("Le programme de travail inclut l'ensemble des contrôles des cycles couverts, avec "
                         "une priorité haute sur les cycles porteurs de risques élevés. Cette intensité "
                         "répond directement à la cartographie : chaque contrôle inclus est rattaché au "
                         "risque qu'il adresse, conformément à la démarche de réponse aux risques évalués.")},
        ],
        "conclusion": ("La mission est planifiée selon une approche substantive renforcée sur les cycles "
                       "ventes, trésorerie et achats. Le programme de travail et le seuil de signification "
                       "retenus permettent de couvrir les risques identifiés ; ils seront réévalués si des "
                       "éléments nouveaux apparaissent en cours de mission."),
    }


def rep_lettre_circu(prompt: str) -> dict:
    m = re.search(r'"destinataire_type": "(\w+)"', prompt)
    dest = m.group(1) if m else "client"
    return {"objet": "Demande de confirmation directe de solde au 31/12/2025",
            "corps": ("Madame, Monsieur,\n\nDans le cadre de l'audit des comptes de notre client, nous vous "
                      "prions de bien vouloir confirmer directement à notre cabinet le solde de votre compte "
                      "dans les livres de la société au 31/12/2025, tel qu'indiqué ci-joint, ou de nous "
                      "signaler tout écart avec vos propres livres, à la date du [DATE].\n\nCette demande "
                      "s'inscrit dans nos procédures normales d'audit et ne traduit aucune suspicion "
                      "particulière.\n\nVeuillez agréer, Madame, Monsieur, nos salutations distinguées."),
            "formule_confirmation": "Solde confirmé conforme / non conforme (rayer la mention inutile), le [DATE].",
            "destinataire_type": dest}


def rep_reponse_circu(_p: str) -> dict:
    return {"synthese": "La réponse du tiers est concordante avec le solde comptable, sous réserve des éléments en transit identifiés.",
            "causes_probables": ["Éléments en rapprochement de fin d'exercice."],
            "diligences": ["Pointer les éléments en transit avec les pièces de janvier N+1."],
            "conclusion": "sans_anomalie"}


def rep_sondage(_p: str) -> dict:
    return {"synthese": "Le sondage n'a pas révélé d'erreur au-delà du seuil toléré sur l'échantillon examiné.",
            "diligences": [], "conclusion": "acceptable",
            "impact_opinion": "Aucun impact sur l'opinion à ce stade."}


def rep_feuille(prompt: str) -> dict:
    m = re.search(r"cycle (\w+)", prompt)
    cycle = m.group(1) if m else "cycle"
    return {
        "titre": f"Feuille de travail — Cycle {cycle}",
        "contenu": ("Objectif : couvrir les assertions du cycle au regard des risques identifiés en "
                    "planification.\n\nProcédures effectuées : exécution des contrôles déterministes du "
                    "programme de travail (références en tête de chaque résultat), revue des exceptions "
                    "levées et de leur tranchement documenté.\n\nRésultats : les résultats chiffrés "
                    "proviennent exclusivement du moteur de calcul (voir références des contrôles). Les "
                    "exceptions levées ont été analysées et tranchées une à une ; les décisions et leurs "
                    "motifs figurent au dossier.\n\nAnomalies non corrigées : néant au-delà du seuil de "
                    "signification à la date de la présente feuille.\n\nConclusion : les travaux réalisés "
                    "sur le cycle permettent de conclure, sous réserve des points ouverts documentés."),
        "nep_refs": ["NEP 330", "NEP 500", "NEP 230"],
        "conclusion": "sans_reserve",
    }


DISPATCH = [
    ("mapping entre chaque nom de colonne", rep_mapper_colonnes),
    ("identifier la nature d'un document", rep_analyse_document),
    ("Analyse les onglets", rep_onglets_excel),
    ("liasse regroupant plusieurs documents", rep_liasse),
    ("synthèse globale de l'évaluation du contrôle interne", rep_synthese_globale_ci),
    ("évalues le contrôle interne", rep_evaluation_ci),
    ("moteur de contrôle déterministe a levé l'exception", rep_interpretation_exception),
    ("document annexe", rep_annexe),
    ("Analyse ce document et identifie-le", rep_cataloguer),
    ("variations N/N-1 significatives", rep_variations),
    ("Reformule-le", rep_reformuler),
    ("proposer une cartographie des risques", rep_risques),
    ("générer le programme de travail d'audit", rep_programme),
    ("note de synthèse de planification", rep_synthese),
    ("lettre de confirmation externe", rep_lettre_circu),
    ("réponse de circularisation", rep_reponse_circu),
    ("conclusion du sondage", rep_sondage),
    ("feuille de travail", rep_feuille),
]


def _texte_prompt(body: dict) -> str:
    msgs = body.get("messages", [])
    if not msgs:
        return ""
    content = msgs[-1].get("content", "")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not self.path.endswith("/v1/messages"):
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = _texte_prompt(body)

        payload = None
        fonction = "inconnue"
        for marqueur, fn in DISPATCH:
            if marqueur.lower() in prompt.lower():
                payload = fn(prompt)
                fonction = fn.__name__
                break
        if payload is None:
            payload = {"reponse": "Stub : aucun répondeur ne correspond à ce prompt."}

        texte = json.dumps(payload, ensure_ascii=False, indent=1)
        reponse = {
            "id": "msg_stub_000",
            "type": "message",
            "role": "assistant",
            "model": body.get("model", "claude-stub"),
            "content": [{"type": "text", "text": texte}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": max(1, len(prompt) // 4),
                      "output_tokens": max(1, len(texte) // 4)},
        }
        data = json.dumps(reponse, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        print(f"[stub] {fonction} ({len(prompt)} car. → {len(texte)} car.)", flush=True)

    def log_message(self, *args):  # silencieux (les prints suffisent)
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
    print(f"Stub LLM Anthropic sur http://127.0.0.1:{port} — Ctrl+C pour arrêter.", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

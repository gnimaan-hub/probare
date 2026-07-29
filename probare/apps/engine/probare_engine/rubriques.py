"""Plan de rubriques d'états financiers — normes/plans en DONNÉES, pas en dur (M5).

Une **feuille maîtresse** (leadsheet) regroupe les comptes de la balance sous la
rubrique d'états financiers à laquelle ils se rattachent (« Clients et comptes
rattachés », « Charges de personnel »…). C'est le pivot standard d'un dossier
d'audit : elle relie le poste publié aux comptes qui le composent, et de là aux
travaux réalisés.

Ce module ne contient QUE le référentiel (le plan de rubriques par référentiel
comptable). Le calcul est dans `reporting/leadsheets.py`.

Conventions — à lire avant de modifier le plan :

- Le **montant d'une rubrique est exprimé en solde net DÉBITEUR positif**, comme
  la balance ajustée (`ajustements.balance_ajustee`). Un poste de passif ou de
  produit porte donc un montant négatif dans cette convention interne.
- Le **signe de présentation** ne dépend que du `type` : actif et charges sont
  présentés tels quels ; passif et produits sont présentés en valeur absolue
  (montant × −1). Une rubrique de contre-valeur (amortissements, dépréciations)
  reste de type `bilan_actif` : son montant naturellement négatif s'affiche donc
  en déduction, ce qui est la présentation attendue.
- `sens` déclare le sens ATTENDU du solde. Il ne sert pas au calcul, seulement à
  signaler un solde anormal (un compte client globalement créditeur, par ex.).
- La résolution compte → rubrique se fait par **préfixe le plus long** : `409`
  (avances aux fournisseurs, à l'actif) l'emporte sur `40` (dettes fournisseurs,
  au passif). Tout ajout de préfixe doit préserver cette logique.
- Aucun compte n'est perdu : ce qui ne tombe dans aucun préfixe atterrit dans une
  rubrique « non affectée » de sa classe, ce qui garantit le bouclage
  Σ rubriques = Σ balance et rend l'anomalie visible plutôt que silencieuse.
"""
from __future__ import annotations
from dataclasses import dataclass, field


# Types de rubrique — déterminent le signe de présentation et le regroupement.
TYPE_BILAN_ACTIF = "bilan_actif"
TYPE_BILAN_PASSIF = "bilan_passif"
TYPE_BILAN_MIXTE = "bilan_mixte"          # comptes de tiers à double sens (44, 45, 46, 47…)
TYPE_RESULTAT_CHARGES = "resultat_charges"
TYPE_RESULTAT_PRODUITS = "resultat_produits"
TYPE_NON_AFFECTE = "non_affecte"

TYPES_RUBRIQUE: dict[str, str] = {
    TYPE_BILAN_ACTIF: "Bilan — Actif",
    TYPE_BILAN_PASSIF: "Bilan — Passif",
    TYPE_BILAN_MIXTE: "Bilan — Comptes à double sens",
    TYPE_RESULTAT_CHARGES: "Compte de résultat — Charges",
    TYPE_RESULTAT_PRODUITS: "Compte de résultat — Produits",
    TYPE_NON_AFFECTE: "Comptes non affectés",
}

# Types dont le montant se présente en valeur absolue (solde créditeur attendu).
_TYPES_INVERSES = (TYPE_BILAN_PASSIF, TYPE_RESULTAT_PRODUITS)

SENS = ("debiteur", "crediteur", "mixte")


@dataclass(frozen=True)
class Rubrique:
    """Une rubrique d'états financiers et les comptes qu'elle agrège."""
    ref: str
    libelle: str
    type: str
    groupe: str                        # grand poste, pour les sous-totaux
    prefixes: tuple[str, ...]
    sens: str = "mixte"                # sens de solde attendu (signalement only)
    cycles: tuple[str, ...] = ()       # cycles d'audit rattachés (travaux croisés)
    ordre: int = 0                     # position d'affichage (posée à la construction)

    @property
    def signe_presentation(self) -> int:
        return -1 if self.type in _TYPES_INVERSES else 1


def _numeroter(rubriques: list[Rubrique]) -> tuple[Rubrique, ...]:
    """Fige l'ordre d'affichage sur la position de déclaration.

    Les groupes sont ainsi contigus par construction : les sous-totaux par grand
    poste se calculent en un seul parcours, sans réordonnancement.
    """
    from dataclasses import replace
    return tuple(replace(r, ordre=i) for i, r in enumerate(rubriques))


# ═══════════════════════════════════════════════════════════════════════════════
# PCGD 2012 (Djibouti) — structure héritée du PCG français, classes 1 à 7
# ═══════════════════════════════════════════════════════════════════════════════

PLAN_PCGD: tuple[Rubrique, ...] = _numeroter([
    # ── Bilan — Actif ────────────────────────────────────────────────────────
    Rubrique("AC-IMMO-INCORP", "Immobilisations incorporelles", TYPE_BILAN_ACTIF,
             "Actif immobilisé", ("20",), "debiteur", ("immobilisations",)),
    Rubrique("AC-IMMO-CORP", "Immobilisations corporelles", TYPE_BILAN_ACTIF,
             "Actif immobilisé", ("21", "22", "23", "24", "25"), "debiteur", ("immobilisations",)),
    Rubrique("AC-IMMO-FIN", "Immobilisations financières", TYPE_BILAN_ACTIF,
             "Actif immobilisé", ("26", "27"), "debiteur", ("immobilisations",)),
    Rubrique("AC-IMMO-AMORT", "Amortissements et dépréciations des immobilisations",
             TYPE_BILAN_ACTIF, "Actif immobilisé", ("28", "29"), "crediteur", ("immobilisations",)),

    Rubrique("AC-STOCKS", "Stocks et en-cours", TYPE_BILAN_ACTIF, "Actif circulant",
             ("30", "31", "32", "33", "34", "35", "36", "37", "38"), "debiteur", ("stocks",)),
    Rubrique("AC-STOCKS-DEP", "Dépréciations des stocks", TYPE_BILAN_ACTIF,
             "Actif circulant", ("39",), "crediteur", ("stocks",)),
    Rubrique("AC-AVANCES-FOURN", "Avances et acomptes versés sur commandes",
             TYPE_BILAN_ACTIF, "Actif circulant", ("409",), "debiteur", ("achats",)),
    Rubrique("AC-CLIENTS", "Clients et comptes rattachés", TYPE_BILAN_ACTIF,
             "Actif circulant", ("41",), "debiteur", ("ventes",)),
    Rubrique("AC-PERSONNEL-DEB", "Avances et acomptes au personnel", TYPE_BILAN_ACTIF,
             "Actif circulant", ("425",), "debiteur", ("paie",)),
    Rubrique("AC-CCA", "Charges constatées d'avance", TYPE_BILAN_ACTIF,
             "Actif circulant", ("486",), "debiteur", ()),
    Rubrique("AC-DEP-TIERS", "Dépréciations des comptes de tiers", TYPE_BILAN_ACTIF,
             "Actif circulant", ("49",), "crediteur", ("ventes",)),

    Rubrique("AC-VMP", "Valeurs mobilières de placement", TYPE_BILAN_ACTIF,
             "Trésorerie active", ("50",), "debiteur", ("tresorerie",)),
    Rubrique("AC-DISPO", "Disponibilités", TYPE_BILAN_ACTIF, "Trésorerie active",
             ("51", "53", "54"), "debiteur", ("tresorerie",)),
    Rubrique("AC-DEP-FIN", "Dépréciations des comptes financiers", TYPE_BILAN_ACTIF,
             "Trésorerie active", ("59",), "crediteur", ("tresorerie",)),

    # ── Bilan — Passif ───────────────────────────────────────────────────────
    Rubrique("PA-CAPITAL", "Capital, primes et réserves", TYPE_BILAN_PASSIF,
             "Capitaux propres", ("10",), "crediteur", ("capitaux_propres",)),
    Rubrique("PA-REPORT", "Report à nouveau", TYPE_BILAN_PASSIF, "Capitaux propres",
             ("11",), "mixte", ("capitaux_propres",)),
    Rubrique("PA-RESULTAT", "Résultat de l'exercice", TYPE_BILAN_PASSIF,
             "Capitaux propres", ("12",), "mixte", ("capitaux_propres",)),
    Rubrique("PA-SUBVENTIONS", "Subventions d'investissement", TYPE_BILAN_PASSIF,
             "Capitaux propres", ("13",), "crediteur", ("capitaux_propres",)),
    Rubrique("PA-PROV-REGL", "Provisions réglementées", TYPE_BILAN_PASSIF,
             "Capitaux propres", ("14",), "crediteur", ("capitaux_propres",)),
    Rubrique("PA-PROVISIONS", "Provisions pour risques et charges", TYPE_BILAN_PASSIF,
             "Provisions", ("15",), "crediteur", ("capitaux_propres",)),
    Rubrique("PA-EMPRUNTS", "Emprunts et dettes financières", TYPE_BILAN_PASSIF,
             "Dettes financières", ("16", "17", "18"), "crediteur", ("tresorerie",)),

    Rubrique("PA-FOURNISSEURS", "Fournisseurs et comptes rattachés", TYPE_BILAN_PASSIF,
             "Dettes d'exploitation", ("40",), "crediteur", ("achats",)),
    Rubrique("PA-CLIENTS-CRED", "Clients créditeurs et avances reçues", TYPE_BILAN_PASSIF,
             "Dettes d'exploitation", ("419",), "crediteur", ("ventes",)),
    Rubrique("PA-PERSONNEL", "Personnel et comptes rattachés", TYPE_BILAN_PASSIF,
             "Dettes d'exploitation", ("42",), "crediteur", ("paie",)),
    Rubrique("PA-SOCIAL", "Organismes sociaux", TYPE_BILAN_PASSIF,
             "Dettes d'exploitation", ("43",), "crediteur", ("paie",)),
    Rubrique("PA-PCA", "Produits constatés d'avance", TYPE_BILAN_PASSIF,
             "Dettes d'exploitation", ("487",), "crediteur", ("ventes",)),

    # ── Comptes de tiers et financiers à double sens ─────────────────────────
    # Présentés selon le signe de leur solde : débiteur → actif, créditeur → passif.
    Rubrique("MX-ETAT", "État et autres collectivités publiques", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("44",), "mixte", ("impots",)),
    Rubrique("MX-GROUPE", "Groupe et associés", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("45",), "mixte", ("capitaux_propres",)),
    Rubrique("MX-DIVERS", "Débiteurs et créditeurs divers", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("46",), "mixte", ()),
    Rubrique("MX-TRANSITOIRE", "Comptes transitoires ou d'attente", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("47",), "mixte", ()),
    Rubrique("MX-REGUL", "Autres comptes de régularisation", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("48",), "mixte", ()),
    Rubrique("MX-TRESO-AUTRE", "Autres comptes financiers", TYPE_BILAN_MIXTE,
             "Comptes à double sens", ("52", "55", "56", "57", "58"), "mixte", ("tresorerie",)),

    # ── Compte de résultat — Charges ─────────────────────────────────────────
    Rubrique("RE-ACHATS", "Achats consommés", TYPE_RESULTAT_CHARGES,
             "Charges d'exploitation", ("60",), "debiteur", ("achats",)),
    Rubrique("RE-SERVICES", "Services extérieurs et autres services extérieurs",
             TYPE_RESULTAT_CHARGES, "Charges d'exploitation", ("61", "62"), "debiteur", ("achats",)),
    Rubrique("RE-IMPOTS-TAXES", "Impôts, taxes et versements assimilés",
             TYPE_RESULTAT_CHARGES, "Charges d'exploitation", ("63",), "debiteur", ("impots",)),
    Rubrique("RE-PERSONNEL", "Charges de personnel", TYPE_RESULTAT_CHARGES,
             "Charges d'exploitation", ("64",), "debiteur", ("paie",)),
    Rubrique("RE-AUTRES-CHARGES", "Autres charges de gestion courante",
             TYPE_RESULTAT_CHARGES, "Charges d'exploitation", ("65",), "debiteur", ()),
    Rubrique("RE-DOTATIONS", "Dotations aux amortissements et provisions",
             TYPE_RESULTAT_CHARGES, "Charges d'exploitation", ("68",), "debiteur",
             ("immobilisations",)),
    Rubrique("RE-CH-FIN", "Charges financières", TYPE_RESULTAT_CHARGES,
             "Charges financières et exceptionnelles", ("66",), "debiteur", ("tresorerie",)),
    Rubrique("RE-CH-EXC", "Charges exceptionnelles", TYPE_RESULTAT_CHARGES,
             "Charges financières et exceptionnelles", ("67",), "debiteur", ()),
    Rubrique("RE-IS", "Impôts sur les bénéfices", TYPE_RESULTAT_CHARGES,
             "Charges financières et exceptionnelles", ("69",), "debiteur", ("impots",)),

    # ── Compte de résultat — Produits ────────────────────────────────────────
    Rubrique("RE-VENTES", "Ventes et prestations de services", TYPE_RESULTAT_PRODUITS,
             "Produits d'exploitation", ("70",), "crediteur", ("ventes",)),
    Rubrique("RE-PROD-STOCKE", "Production stockée et immobilisée",
             TYPE_RESULTAT_PRODUITS, "Produits d'exploitation", ("71", "72", "73"),
             "mixte", ("stocks",)),
    Rubrique("RE-AUTRES-PROD-EXPL", "Subventions et autres produits d'exploitation",
             TYPE_RESULTAT_PRODUITS, "Produits d'exploitation", ("74", "75"), "crediteur", ()),
    Rubrique("RE-PROD-FIN", "Produits financiers", TYPE_RESULTAT_PRODUITS,
             "Produits financiers et exceptionnels", ("76",), "crediteur", ("tresorerie",)),
    Rubrique("RE-PROD-EXC", "Produits exceptionnels", TYPE_RESULTAT_PRODUITS,
             "Produits financiers et exceptionnels", ("77",), "crediteur", ()),
    Rubrique("RE-REPRISES", "Reprises sur amortissements et provisions",
             TYPE_RESULTAT_PRODUITS, "Produits financiers et exceptionnels",
             ("78", "79"), "crediteur", ()),

    # ── Filet de sécurité : aucun compte n'est perdu ─────────────────────────
    # Une rubrique par classe, pour que le bouclage Σ rubriques = Σ balance
    # tienne toujours et que l'anomalie de plan soit visible dans le dossier.
    *[Rubrique(f"NA-CLASSE-{n}", f"Comptes de classe {n} non affectés",
               TYPE_NON_AFFECTE, "Comptes non affectés", (str(n),), "mixte", ())
      for n in range(1, 10)],
])


# Plans par référentiel comptable. Le PCGD est la structure de référence ; les
# référentiels non encore dotés d'un plan propre s'y rattachent explicitement
# (SYSCOHADA et IFRS mériteront leur plan dédié — voir `plan_est_approxime`).
PLANS_RUBRIQUES: dict[str, tuple[Rubrique, ...]] = {
    "pcgd": PLAN_PCGD,
    "pcg_fr": PLAN_PCGD,
    "syscohada": PLAN_PCGD,
    "ifrs": PLAN_PCGD,
    "autre": PLAN_PCGD,
}

# Référentiels servis par un plan d'emprunt : le rendu doit le dire à l'auditeur.
_REFERENTIELS_APPROXIMES = ("syscohada", "ifrs", "autre")


def plan_rubriques(referentiel_comptable: str | None = None) -> tuple[Rubrique, ...]:
    """Plan de rubriques applicable au référentiel comptable de l'entité."""
    code = (referentiel_comptable or "pcgd").lower()
    return PLANS_RUBRIQUES.get(code, PLAN_PCGD)


def plan_est_approxime(referentiel_comptable: str | None = None) -> bool:
    """Vrai si le plan servi n'est pas celui du référentiel déclaré.

    L'auditeur doit alors relire l'affectation des comptes (elle est de toute
    façon modifiable compte par compte) plutôt que la tenir pour acquise.
    """
    return (referentiel_comptable or "pcgd").lower() in _REFERENTIELS_APPROXIMES


def rubrique_du_compte(compte: str,
                       plan: tuple[Rubrique, ...] | None = None) -> Rubrique | None:
    """Rubrique d'un compte — préfixe le PLUS LONG gagnant.

    `409` (avances fournisseurs, actif) l'emporte ainsi sur `40` (dettes
    fournisseurs, passif). Retourne None si le compte est vide ou ne commence
    pas par un chiffre (ligne de total, en-tête mal ingéré…).
    """
    plan = plan or PLAN_PCGD
    num = str(compte or "").strip()
    if not num or not num[0].isdigit():
        return None
    meilleure: Rubrique | None = None
    longueur = -1
    for r in plan:
        for p in r.prefixes:
            if num.startswith(p) and len(p) > longueur:
                meilleure, longueur = r, len(p)
    return meilleure


def index_par_ref(plan: tuple[Rubrique, ...] | None = None) -> dict[str, Rubrique]:
    plan = plan or PLAN_PCGD
    return {r.ref: r for r in plan}


def rubrique_as_dict(r: Rubrique) -> dict:
    return {
        "ref": r.ref,
        "libelle": r.libelle,
        "type": r.type,
        "type_libelle": TYPES_RUBRIQUE.get(r.type, r.type),
        "groupe": r.groupe,
        "prefixes": list(r.prefixes),
        "sens": r.sens,
        "cycles": list(r.cycles),
        "ordre": r.ordre,
        "signe_presentation": r.signe_presentation,
    }

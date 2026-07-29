"""Tests M5 — feuilles maîtresses par rubrique d'états financiers.

Trois propriétés doivent tenir en toutes circonstances :
  1. le BOUCLAGE — Σ des rubriques = Σ de la balance ajustée, aucun compte
     perdu ni compté deux fois ;
  2. la RÉAFFECTATION — le jugement de l'auditeur prime sur le plan par défaut,
     sans casser le bouclage ;
  3. la CONTINUITÉ N-1 — un compte soldé en N mais mouvementé en N-1 reste visible.
"""
from __future__ import annotations
import os

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_m5/projets")

from probare_engine.ajustements import balance_ajustee
from probare_engine.rubriques import (
    PLAN_PCGD, plan_rubriques, plan_est_approxime, rubrique_du_compte,
    index_par_ref, TYPE_BILAN_ACTIF, TYPE_BILAN_PASSIF, TYPE_NON_AFFECTE,
)
from probare_engine.reporting.leadsheets import (
    construire_feuilles_maitresses, rubriques_non_vides, TOLERANCE_BOUCLAGE,
)
from probare_engine.reporting.export import verifier_bouclage, BouclageError


# Balance d'essai : actif = passif, comptes de résultat équilibrés.
# Convention interne : solde net DÉBITEUR positif.
BALANCE_BRUTE = {
    "211000": (500_000.0, ["src-211"]),   # immobilisations corporelles
    "281100": (-120_000.0, ["src-281"]),  # amortissements (contre-valeur)
    "411000": (300_000.0, ["src-411"]),   # clients
    "512000": (80_000.0, ["src-512"]),    # banque
    "401000": (-260_000.0, ["src-401"]),  # fournisseurs
    "409000": (15_000.0, ["src-409"]),    # avances fournisseurs — préfixe plus long que 40
    "101000": (-400_000.0, ["src-101"]),  # capital
    "445700": (-45_000.0, ["src-445"]),   # TVA collectée (compte à double sens)
    "601000": (700_000.0, ["src-601"]),   # achats
    "701000": (-770_000.0, ["src-701"]),  # ventes
}


def _balance(soldes=None, ecritures=None):
    return balance_ajustee(soldes if soldes is not None else dict(BALANCE_BRUTE),
                           ecritures or [])


def _matrice(**kwargs):
    kwargs.setdefault("balance_ajustee", _balance())
    return construire_feuilles_maitresses(**kwargs)


# ─── Plan de rubriques ────────────────────────────────────────────────────────

class TestPlanRubriques:
    def test_prefixe_le_plus_long_gagne(self):
        """409 (avances, actif) doit l'emporter sur 40 (fournisseurs, passif)."""
        assert rubrique_du_compte("401000", PLAN_PCGD).ref == "PA-FOURNISSEURS"
        assert rubrique_du_compte("409000", PLAN_PCGD).ref == "AC-AVANCES-FOURN"
        assert rubrique_du_compte("411000", PLAN_PCGD).ref == "AC-CLIENTS"
        assert rubrique_du_compte("419000", PLAN_PCGD).ref == "PA-CLIENTS-CRED"
        assert rubrique_du_compte("425000", PLAN_PCGD).ref == "AC-PERSONNEL-DEB"
        assert rubrique_du_compte("421000", PLAN_PCGD).ref == "PA-PERSONNEL"
        assert rubrique_du_compte("486000", PLAN_PCGD).ref == "AC-CCA"
        assert rubrique_du_compte("487000", PLAN_PCGD).ref == "PA-PCA"
        assert rubrique_du_compte("481000", PLAN_PCGD).ref == "MX-REGUL"

    def test_compte_inconnu_tombe_dans_sa_classe(self):
        """Un compte hors plan atterrit dans la rubrique « non affectée » de sa classe."""
        r = rubrique_du_compte("991000", PLAN_PCGD)
        assert r is not None and r.ref == "NA-CLASSE-9"
        assert r.type == TYPE_NON_AFFECTE

    def test_compte_illisible_non_rattache(self):
        assert rubrique_du_compte("", PLAN_PCGD) is None
        assert rubrique_du_compte("TOTAL", PLAN_PCGD) is None
        assert rubrique_du_compte(None, PLAN_PCGD) is None

    def test_refs_uniques_et_ordre_strictement_croissant(self):
        refs = [r.ref for r in PLAN_PCGD]
        assert len(refs) == len(set(refs))
        assert [r.ordre for r in PLAN_PCGD] == sorted(r.ordre for r in PLAN_PCGD)

    def test_groupes_contigus(self):
        """Les sous-totaux par grand poste supposent des groupes contigus."""
        vus: set[str] = set()
        precedent = None
        for r in PLAN_PCGD:
            if r.groupe != precedent:
                assert r.groupe not in vus, f"groupe « {r.groupe} » scindé dans le plan"
                vus.add(r.groupe)
                precedent = r.groupe

    def test_signe_de_presentation(self):
        par_ref = index_par_ref(PLAN_PCGD)
        assert par_ref["AC-CLIENTS"].signe_presentation == 1
        assert par_ref["PA-FOURNISSEURS"].signe_presentation == -1
        assert par_ref["RE-ACHATS"].signe_presentation == 1
        assert par_ref["RE-VENTES"].signe_presentation == -1
        # Contre-valeur : reste à l'actif, son solde créditeur s'affiche en déduction.
        assert par_ref["AC-IMMO-AMORT"].type == TYPE_BILAN_ACTIF
        assert par_ref["AC-IMMO-AMORT"].signe_presentation == 1

    def test_referentiel_sans_plan_propre_est_signale(self):
        assert plan_rubriques("syscohada") is PLAN_PCGD
        assert plan_est_approxime("syscohada") is True
        assert plan_est_approxime("pcgd") is False


# ─── Bouclage ─────────────────────────────────────────────────────────────────

class TestBouclage:
    def test_somme_rubriques_egale_somme_balance(self):
        m = _matrice()
        b = m["bouclage"]
        assert b["boucle"] is True
        assert abs(b["ecart"]) <= TOLERANCE_BOUCLAGE
        assert b["total_rubriques"] == pytest.approx(b["total_balance"], abs=0.01)

    def test_aucun_compte_perdu(self):
        m = _matrice()
        repris = {c["compte"] for r in m["rubriques"] for c in r["comptes"]}
        assert repris == set(BALANCE_BRUTE)
        assert m["nb_comptes"] == len(BALANCE_BRUTE)

    def test_chaque_compte_dans_une_seule_rubrique(self):
        m = _matrice()
        vus: list[str] = [c["compte"] for r in m["rubriques"] for c in r["comptes"]]
        assert len(vus) == len(set(vus))

    def test_boucle_apres_ajustement_passe(self):
        """Une écriture passée modifie les soldes sans rompre le bouclage."""
        ecriture = {
            "statut": "passee",
            "lignes": [{"compte": "681100", "debit": 20_000, "credit": 0},
                       {"compte": "281100", "debit": 0, "credit": 20_000}],
        }
        m = _matrice(balance_ajustee=_balance(ecritures=[ecriture]))
        assert m["bouclage"]["boucle"] is True
        par_ref = {r["ref"]: r for r in m["rubriques"]}
        assert par_ref["RE-DOTATIONS"]["montant_ajustements"] == 20_000
        assert par_ref["AC-IMMO-AMORT"]["montant_ajustements"] == -20_000
        # Le compte 681100 n'existait pas dans la balance : il apparaît, solde brut nul.
        compte_681 = next(c for c in par_ref["RE-DOTATIONS"]["comptes"] if c["compte"] == "681100")
        assert compte_681["solde_brut"] == 0 and compte_681["solde_ajuste"] == 20_000

    def test_compte_illisible_conserve_le_bouclage(self):
        """Une ligne « TOTAL » mal ingérée ne doit pas disparaître silencieusement."""
        soldes = dict(BALANCE_BRUTE)
        soldes["TOTAL GENERAL"] = (0.0, ["src-total"])
        m = _matrice(balance_ajustee=_balance(soldes))
        assert m["comptes_non_affectes"] and \
            m["comptes_non_affectes"][0]["compte"] == "TOTAL GENERAL"
        assert m["bouclage"]["boucle"] is True

    def test_verifier_bouclage_bloque_le_livrable(self):
        m = _matrice()
        verifier_bouclage(m)  # ne lève pas
        m["bouclage"] = {"boucle": False, "ecart": 1_500.0,
                         "total_rubriques": 1.0, "total_balance": 2.0}
        with pytest.raises(BouclageError, match="non bouclées"):
            verifier_bouclage(m)


# ─── Agrégation et présentation ───────────────────────────────────────────────

class TestAgregation:
    def test_montants_par_rubrique(self):
        par_ref = {r["ref"]: r for r in _matrice()["rubriques"]}
        assert par_ref["AC-CLIENTS"]["montant_ajuste"] == 300_000
        assert par_ref["PA-FOURNISSEURS"]["montant_ajuste"] == -260_000
        # Le passif se présente en valeur positive.
        assert par_ref["PA-FOURNISSEURS"]["montant_presente"] == 260_000
        assert par_ref["RE-VENTES"]["montant_presente"] == 770_000
        # La contre-valeur d'amortissement reste négative à l'actif.
        assert par_ref["AC-IMMO-AMORT"]["montant_presente"] == -120_000

    def test_totaux_de_presentation(self):
        t = _matrice()["totaux"]
        # Actif : 500 000 − 120 000 + 300 000 + 80 000 + 15 000 = 775 000
        assert t["actif"] == 775_000
        # Passif : 260 000 + 400 000 + 45 000 (TVA collectée, à double sens) = 705 000
        assert t["passif"] == 705_000
        assert t["double_sens_passif"] == 45_000
        assert t["charges"] == 700_000
        assert t["produits"] == 770_000
        assert t["resultat"] == 70_000

    def test_sous_totaux_par_groupe(self):
        m = _matrice()
        groupes = {g["libelle"]: g for g in m["groupes"]}
        # Actif immobilisé = 500 000 − 120 000
        assert groupes["Actif immobilisé"]["montant_presente"] == 380_000

    def test_solde_de_sens_anormal_signale(self):
        """Un poste clients globalement créditeur est signalé, pas corrigé."""
        soldes = dict(BALANCE_BRUTE)
        soldes["411000"] = (-300_000.0, ["src-411"])
        soldes["101000"] = (-1_000_000.0, ["src-101"])  # rééquilibrage
        m = _matrice(balance_ajustee=_balance(soldes))
        par_ref = {r["ref"]: r for r in m["rubriques"]}
        assert par_ref["AC-CLIENTS"]["sens_anormal"] is True
        assert par_ref["PA-FOURNISSEURS"]["sens_anormal"] is False

    def test_rubriques_vides_exclues_du_rendu(self):
        m = _matrice()
        servies = rubriques_non_vides(m)
        assert all(r["nb_comptes"] > 0 for r in servies)
        assert len(servies) == m["nb_rubriques_servies"]
        assert len(servies) < len(m["rubriques"])

    def test_libelles_et_provenance_conserves(self):
        m = _matrice(libelles_comptes={"411000": "Clients France"})
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        compte = clients["comptes"][0]
        assert compte["libelle"] == "Clients France"
        assert "src-411" in compte["sources"]


# ─── Réaffectation par l'auditeur ─────────────────────────────────────────────

class TestReaffectation:
    def test_override_deplace_le_compte(self):
        m = _matrice(overrides={"445700": "PA-SOCIAL"})
        par_ref = {r["ref"]: r for r in m["rubriques"]}
        assert [c["compte"] for c in par_ref["PA-SOCIAL"]["comptes"]] == ["445700"]
        assert par_ref["PA-SOCIAL"]["montant_ajuste"] == -45_000
        assert par_ref["MX-ETAT"]["nb_comptes"] == 0
        assert par_ref["PA-SOCIAL"]["comptes"][0]["reaffecte"] is True

    def test_override_preserve_le_bouclage(self):
        assert _matrice(overrides={"445700": "PA-SOCIAL"})["bouclage"]["boucle"] is True

    def test_override_vers_rubrique_inconnue_ignore(self):
        """Une référence de rubrique invalide ne doit pas faire disparaître le compte."""
        m = _matrice(overrides={"445700": "RUBRIQUE-FANTOME"})
        par_ref = {r["ref"]: r for r in m["rubriques"]}
        assert par_ref["MX-ETAT"]["nb_comptes"] == 1
        assert m["bouclage"]["boucle"] is True


# ─── Comparatif N-1 ───────────────────────────────────────────────────────────

class TestComparatifN1:
    def test_variation_et_pourcentage(self):
        m = _matrice(soldes_n1={"411000": (250_000.0, ["n1-411"])})
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        assert clients["montant_n1"] == 250_000
        assert clients["variation_abs"] == 50_000
        assert clients["variation_pct"] == pytest.approx(0.2)
        assert m["avec_comparatif"] is True

    def test_pas_de_pourcentage_sans_base(self):
        """Une rubrique nouvelle n'a pas de variation relative : « +100 % » serait un artefact."""
        clients = next(r for r in _matrice()["rubriques"] if r["ref"] == "AC-CLIENTS")
        assert clients["montant_n1"] == 0
        assert clients["variation_pct"] is None

    def test_compte_present_en_n1_seulement_reste_visible(self):
        """Un compte soldé en N mais mouvementé en N-1 est une information d'audit."""
        m = _matrice(soldes_n1={"164000": (90_000.0, ["n1-164"])})
        emprunts = next(r for r in m["rubriques"] if r["ref"] == "PA-EMPRUNTS")
        assert emprunts["nb_comptes"] == 1
        compte = emprunts["comptes"][0]
        assert compte["compte"] == "164000"
        assert compte["absent_n"] is True
        assert compte["solde_ajuste"] == 0
        assert compte["variation_abs"] == -90_000
        assert m["bouclage"]["boucle"] is True

    def test_variation_notable_au_dela_du_seuil(self):
        m = _matrice(soldes_n1={"411000": (250_000.0, ["n1-411"])}, seuil_variation=10_000)
        assert _compte(m, "AC-CLIENTS", "411000")["variation_notable"] is True

    def test_variation_sous_le_seuil_non_signalee(self):
        """Une variation de 1 000 sous un seuil de 10 000 n'est pas signalée."""
        m = _matrice(soldes_n1={"411000": (299_000.0, ["n1-411"])}, seuil_variation=10_000)
        assert _compte(m, "AC-CLIENTS", "411000")["variation_notable"] is False


class TestEquilibreBilan:
    """Identité actif − passif = résultat : contrôle de SUBSTANCE des montants.

    Le bouclage (Σ rubriques = Σ balance) ne prouve que la cohérence de
    l'affectation : il tient même sur des soldes faux. Cette identité, elle,
    aurait détecté la confusion mouvements/soldes à l'ingestion.
    """

    def test_balance_saine_equilibree(self):
        eq = _matrice()["equilibre_bilan"]
        assert eq["equilibre"] is True
        assert eq["ecart"] == pytest.approx(0.0, abs=TOLERANCE_BOUCLAGE)

    def test_soldes_fausses_detectes_alors_que_le_bouclage_tient(self):
        """Le cas du bug réel : des soldes faux qui bouclent quand même."""
        soldes = dict(BALANCE_BRUTE)
        # On fausse un solde client ET sa contrepartie : la balance boucle
        # toujours (Σ = 0), mais l'actif ne correspond plus au passif + résultat.
        soldes["411000"] = (-300_000.0, ["src-411"])
        soldes["445700"] = (255_000.0, ["src-445"])
        m = _matrice(balance_ajustee=_balance(soldes))
        assert m["bouclage"]["boucle"] is True, "le bouclage doit rester vérifié"
        assert m["equilibre_bilan"]["equilibre"] is False, "l'identité doit, elle, alerter"

    def test_resultat_comptabilise_est_signale(self):
        """Un résultat déjà viré en compte 12 rompt l'identité — légitimement."""
        soldes = dict(BALANCE_BRUTE)
        soldes["120000"] = (-70_000.0, ["src-120"])
        soldes["101000"] = (-330_000.0, ["src-101"])
        eq = _matrice(balance_ajustee=_balance(soldes))["equilibre_bilan"]
        assert eq["resultat_deja_comptabilise"] is True

    def test_resultat_non_comptabilise_par_defaut(self):
        assert _matrice()["equilibre_bilan"]["resultat_deja_comptabilise"] is False

    def test_libelle_equilibre_selon_le_cas(self):
        from probare_engine.reporting.export import _libelle_equilibre_bilan
        assert _libelle_equilibre_bilan(_matrice()) == "Vérifiée"
        soldes = dict(BALANCE_BRUTE)
        soldes["411000"] = (-300_000.0, ["src-411"])
        soldes["445700"] = (255_000.0, ["src-445"])
        assert "à investiguer" in _libelle_equilibre_bilan(_matrice(balance_ajustee=_balance(soldes)))

    def test_identite_non_bloquante(self):
        """Contrairement au bouclage, elle ne doit pas empêcher la génération."""
        soldes = dict(BALANCE_BRUTE)
        soldes["411000"] = (-300_000.0, ["src-411"])
        soldes["445700"] = (255_000.0, ["src-445"])
        verifier_bouclage(_matrice(balance_ajustee=_balance(soldes)))  # ne lève pas


class TestRenduSansComparatif:
    """Sans balance N-1, les colonnes comparatives sont RETIRÉES des tableaux.

    Les laisser à zéro afficherait une variation égale au solde N — le lecteur y
    lirait « tout le poste a varié » alors qu'il n'y a rien à comparer.
    """

    def test_entetes_reduits_sans_comparatif(self):
        from probare_engine.reporting.export import _format_tableaux
        formats = _format_tableaux(_matrice())
        assert formats["synthese"][0] == ["Rubrique d'états financiers", "Solde importé",
                                          "Ajustements", "Solde audité"]
        assert formats["detail"][0] == ["Compte", "Libellé", "Solde importé",
                                        "Ajustements", "Solde audité"]

    def test_entetes_complets_avec_comparatif(self):
        from probare_engine.reporting.export import _format_tableaux
        formats = _format_tableaux(_matrice(soldes_n1={"411000": (250_000.0, ["n1"])}))
        assert "Exercice N-1" in formats["synthese"][0]
        assert "Variation" in formats["synthese"][0]

    def test_largeurs_coherentes_avec_les_entetes(self):
        """Autant de largeurs que de colonnes, et la somme tient dans la page."""
        from probare_engine.reporting.export import _format_tableaux
        for matrice in (_matrice(), _matrice(soldes_n1={"411000": (250_000.0, ["n1"])})):
            for entetes, largeurs in _format_tableaux(matrice).values():
                assert len(entetes) == len(largeurs)
                assert sum(largeurs) == pytest.approx(16.0, abs=0.01)

    def test_lignes_synthese_sans_comparatif(self):
        from probare_engine.reporting.export import (
            _lignes_synthese_feuilles, _format_tableaux)
        m = _matrice()
        lignes, _ = _lignes_synthese_feuilles(m)
        largeur_attendue = len(_format_tableaux(m)["synthese"][0])
        assert lignes and all(len(l) == largeur_attendue for l in lignes)

    def test_lignes_detail_sans_comparatif(self):
        from probare_engine.reporting.export import (
            _lignes_detail_rubrique, _format_tableaux)
        m = _matrice()
        rubrique = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        lignes, _ = _lignes_detail_rubrique(rubrique, avec_n1=False)
        assert all(len(l) == len(_format_tableaux(m)["detail"][0]) for l in lignes)

    def test_lignes_synthese_avec_comparatif_gardent_les_7_colonnes(self):
        from probare_engine.reporting.export import _lignes_synthese_feuilles
        lignes, _ = _lignes_synthese_feuilles(
            _matrice(soldes_n1={"411000": (250_000.0, ["n1"])}))
        assert lignes and all(len(l) == 7 for l in lignes)

    def test_sous_totaux_justes_sans_comparatif(self):
        """Le sous-total d'un grand poste reste la somme de ses rubriques."""
        from probare_engine.reporting.export import _lignes_synthese_feuilles
        lignes, styles = _lignes_synthese_feuilles(_matrice())
        i = next(i for i, s in enumerate(styles) if s == "sous_total")
        rubriques = [l for l, s in zip(lignes[:i], styles[:i]) if s != "sous_total"]

        def _nombre(txt):
            return 0.0 if txt.strip() == "—" else float(
                txt.replace(" ", "").replace(" ", "").replace(",", "."))

        attendu = sum(_nombre(l[3]) for l in rubriques)
        assert _nombre(lignes[i][3]) == pytest.approx(attendu, abs=0.01)


def _compte(matrice: dict, ref_rubrique: str, compte: str) -> dict:
    rubrique = next(r for r in matrice["rubriques"] if r["ref"] == ref_rubrique)
    return next(c for c in rubrique["comptes"] if c["compte"] == compte)


# ─── Rattachement des travaux d'audit ─────────────────────────────────────────

class TestRattachementTravaux:
    TRAVAUX = {
        "resultats": [{"controle_ref": "VENTE-CREANCES-ECHUES", "statut": "ok"}],
        "exceptions": [{"id": "e1", "controle_ref": "VENTE-CREANCES-ECHUES",
                        "statut": "ouverte", "severite": "significative",
                        "description": "Créances échues non provisionnées"}],
        "circularisations": [{"id": "c1", "compte": "411000", "libelle": "Client A",
                              "statut": "reponse_recue", "cycle": "ventes"}],
        "sondages": [{"id": "s1", "cycle": "achats", "prefixes": ["60"],
                      "libelle": "Factures d'achat", "taille_echantillon": 30}],
        "ajustements": [{"id": "a1", "libelle": "Provision clients", "statut": "passee",
                         "lignes": [{"compte": "411000"}, {"compte": "701000"}]}],
    }

    def test_circularisation_rattachee_par_compte(self):
        m = _matrice(travaux=self.TRAVAUX)
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        assert [c["id"] for c in clients["travaux"]["circularisations"]] == ["c1"]

    def test_sondage_rattache_par_prefixe(self):
        m = _matrice(travaux=self.TRAVAUX)
        achats = next(r for r in m["rubriques"] if r["ref"] == "RE-ACHATS")
        assert [s["id"] for s in achats["travaux"]["sondages"]] == ["s1"]
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        assert clients["travaux"]["sondages"] == []

    def test_exception_rattachee_par_cycle_du_controle(self):
        m = _matrice(travaux=self.TRAVAUX)
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        ventes = next(r for r in m["rubriques"] if r["ref"] == "RE-VENTES")
        assert [e["id"] for e in clients["travaux"]["exceptions_ouvertes"]] == ["e1"]
        # Le cycle ventes couvre aussi la rubrique de produits.
        assert [e["id"] for e in ventes["travaux"]["exceptions_ouvertes"]] == ["e1"]
        # Une rubrique d'un autre cycle n'hérite de rien.
        immo = next(r for r in m["rubriques"] if r["ref"] == "AC-IMMO-CORP")
        assert immo["travaux"]["exceptions_ouvertes"] == []

    def test_ajustement_rattache_a_chaque_compte_mouvemente(self):
        m = _matrice(travaux=self.TRAVAUX)
        for ref in ("AC-CLIENTS", "RE-VENTES"):
            r = next(x for x in m["rubriques"] if x["ref"] == ref)
            assert [a["id"] for a in r["travaux"]["ajustements"]] == ["a1"]

    def test_ajustement_compte_une_seule_fois_par_rubrique(self):
        """Une écriture touchant deux comptes de la MÊME rubrique n'y figure qu'une fois."""
        travaux = {"ajustements": [{"id": "a2", "libelle": "Reclassement", "statut": "passee",
                                    "lignes": [{"compte": "411000"}, {"compte": "411000"}]}]}
        m = _matrice(travaux=travaux)
        clients = next(r for r in m["rubriques"] if r["ref"] == "AC-CLIENTS")
        assert len(clients["travaux"]["ajustements"]) == 1

    def test_sans_travaux_les_listes_sont_vides(self):
        m = _matrice()
        assert all(r["nb_travaux"] == 0 for r in m["rubriques"])

"""Tests D1 — Journal Entry Testing (ISA 240).

Le score de risque de chaque écriture est une somme pondérée déterministe de
signaux. Ces tests figent le comportement de chaque signal et de l'agrégation.
"""
from __future__ import annotations
import os
import uuid
from types import SimpleNamespace

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_d1/projets")

from probare_engine.controls.journal_entries import (
    analyser_journal, SIGNAUX, SEUIL_SIGNALEMENT_DEFAUT, LIBELLES_GENERIQUES,
    JOURS_NON_OUVRES_DEFAUT, POPULATION_MIN_CALENDRIER,
    POPULATION_MIN_NEUTRALISATION, TAUX_SIGNAL_NON_DISCRIMINANT,
    _jours_non_ouvres, _grouper_en_ecritures,
)


# ── Fabrique de lignes de grand livre (RowDict = {champ: DonneeSourcee}) ──

_seq = iter(range(1, 10_000_000))


def _ds(valeur):
    return SimpleNamespace(id=f"d{next(_seq)}", valeur=valeur)


def _row(compte, debit=0, credit=0, piece="P1", date="2024-06-13", libelle="Achat"):
    r = {"compte": _ds(compte)}
    if piece is not None:
        r["numero_piece"] = _ds(piece)
    if date is not None:
        r["date"] = _ds(date)
    if libelle is not None:
        r["libelle"] = _ds(libelle)
    if debit:
        r["debit"] = _ds(debit)
    if credit:
        r["credit"] = _ds(credit)
    return r


def _piece_equilibree(piece, montant, **kw):
    """Deux lignes équilibrées portant le même numéro de pièce."""
    return [
        _row("601000", debit=montant, piece=piece, **kw),
        _row("401000", credit=montant, piece=piece, **kw),
    ]


def _signaux(analyse, numero_piece):
    for e in analyse["signalees"]:
        if e["numero_piece"] == numero_piece:
            return set(e["signaux"])
    return set()


class TestSignaux:
    def test_ecriture_normale_non_signalee(self):
        rows = _piece_equilibree("P1", 5000)
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024")
        assert a["nb_signalees"] == 0

    def test_desequilibre(self):
        rows = [
            _row("601000", debit=1000, piece="P9"),
            _row("401000", credit=700, piece="P9"),
        ]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "desequilibre" in _signaux(a, "P9")

    def test_sous_seuil(self):
        # Montant entre 90 % et 100 % du seuil → contournement possible
        rows = _piece_equilibree("P2", 95_000)
        a = analyser_journal(rows, seuil=100_000, exercice="2024", seuil_signalement=1)
        assert "sous_seuil" in _signaux(a, "P2")
        # Un montant nettement sous le seuil n'est pas concerné
        rows = _piece_equilibree("P3", 40_000)
        a = analyser_journal(rows, seuil=100_000, exercice="2024", seuil_signalement=1)
        assert "sous_seuil" not in _signaux(a, "P3")

    def test_contrepartie_inhabituelle(self):
        # Produit (7) directement soldé par la trésorerie (5), sans client (4)
        rows = [
            _row("512000", debit=8000, piece="P4"),
            _row("701000", credit=8000, piece="P4"),
        ]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "contrepartie" in _signaux(a, "P4")
        # Le même produit encaissé via un client (4) est un schéma normal
        rows_normal = [
            _row("512000", debit=8000, piece="P5"),
            _row("411000", credit=8000, piece="P5"),
        ]
        a = analyser_journal(rows_normal, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "contrepartie" not in _signaux(a, "P5")

    def test_weekend(self):
        rows = _piece_equilibree("P6", 5000, date="2024-06-16")  # dimanche
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "weekend" in _signaux(a, "P6")

    def test_cutoff_tardif(self):
        rows = _piece_equilibree("P7", 5000, date="2024-12-31")
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "cutoff_tardif" in _signaux(a, "P7")

    def test_libelle_suspect(self):
        rows = _piece_equilibree("P8", 5000, libelle="Divers")
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "libelle_suspect" in _signaux(a, "P8")

    def test_montant_rond(self):
        rows = _piece_equilibree("PR", 3_000_000)
        a = analyser_journal(rows, seuil=1_000_000_000, exercice="2024", seuil_signalement=1)
        assert "montant_rond" in _signaux(a, "PR")


class TestScoreEtAgregation:
    def test_score_cumule_les_signaux(self):
        # Pièce déséquilibrée (3) + libellé suspect (1) + week-end (2) = 6
        rows = [
            _row("601000", debit=1000, piece="PX", date="2024-06-16", libelle="OD"),
            _row("401000", credit=700, piece="PX", date="2024-06-16", libelle="OD"),
        ]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        e = next(x for x in a["signalees"] if x["numero_piece"] == "PX")
        attendu = SIGNAUX["desequilibre"]["poids"] + SIGNAUX["libelle_suspect"]["poids"] + SIGNAUX["weekend"]["poids"]
        assert e["score"] == attendu

    def test_seuil_de_signalement(self):
        # Un seul signal faible (libellé, poids 1) < seuil par défaut (3) → non signalé
        rows = _piece_equilibree("PF", 5000, libelle="Divers")
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024")
        assert a["seuil_signalement"] == SEUIL_SIGNALEMENT_DEFAUT
        assert _signaux(a, "PF") == set()  # pas dans les signalées

    def test_tri_par_score_decroissant(self):
        rows = []
        rows += [_row("601000", debit=1000, piece="FAIBLE", libelle="Divers"),
                 _row("401000", credit=1000, piece="FAIBLE", libelle="Divers")]
        rows += [_row("601000", debit=700, piece="FORT", date="2024-12-31", libelle="OD"),
                 _row("401000", credit=1000, piece="FORT", date="2024-12-31", libelle="OD")]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        scores = [e["score"] for e in a["signalees"]]
        assert scores == sorted(scores, reverse=True)

    def test_sans_piece_desactive_si_aucune_piece(self):
        # Grand livre sans aucun numéro de pièce : signal sans_piece désactivé
        rows = [_row("601000", debit=1000, piece=None), _row("401000", credit=1000, piece=None)]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["sans_piece_desactive"] is True
        assert a["par_signal"].get("sans_piece", 0) == 0

    def test_sans_piece_signale_si_isole(self):
        # La plupart des écritures ont une pièce, une seule n'en a pas → signalée
        rows = _piece_equilibree("P1", 5000) + _piece_equilibree("P2", 5000)
        rows += [_row("601000", debit=1000, piece=None), _row("401000", credit=1000, piece=None)]
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["sans_piece_desactive"] is False
        assert a["par_signal"].get("sans_piece", 0) >= 1


class TestIdentiteEcriture:
    """L'écriture est identifiée par (numéro de pièce, date), non par le seul numéro.

    Les numéros de pièce sont couramment réattribués d'un journal à l'autre : les
    à-nouveaux d'ouverture sont renumérotés à partir de 1 et collisionnent avec
    les écritures de l'exercice. Regrouper sur le seul numéro agglomérait des
    écritures étrangères et fabriquait un faux déséquilibre de masse (82 % de la
    population sur le grand livre ARULOS 2024).
    """

    def test_meme_numero_deux_dates_ne_fait_pas_un_desequilibre(self):
        rows = (_piece_equilibree("1", 1000, date="2024-01-01")
                + _piece_equilibree("1", 7000, date="2024-06-13"))
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["nb_ecritures"] == 2
        assert a["par_signal"].get("desequilibre", 0) == 0

    def test_desequilibre_reste_detecte_dans_une_meme_date(self):
        rows = [
            _row("601000", debit=1000, piece="1", date="2024-06-13"),
            _row("401000", credit=700, piece="1", date="2024-06-13"),
        ]
        rows += _piece_equilibree("1", 5000, date="2024-01-01")
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["par_signal"].get("desequilibre", 0) == 1

    def test_numeros_reutilises_documentes(self):
        rows = (_piece_equilibree("1", 1000, date="2024-01-01")
                + _piece_equilibree("1", 7000, date="2024-06-13")
                + _piece_equilibree("2", 500, date="2024-03-05"))
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024")
        assert a["numeros_piece_reutilises"] == 1

    def test_groupage_identique_si_numerotation_fiable(self):
        """Sur un grand livre bien numéroté, la clé (pièce, date) ne change rien."""
        rows = (_piece_equilibree("A", 100, date="2024-02-05")
                + _piece_equilibree("B", 200, date="2024-02-06"))
        ecritures, reutilises = _grouper_en_ecritures(rows)
        assert len(ecritures) == 2 and reutilises == 0
        assert all(len(e["lignes"]) == 2 for e in ecritures)


class TestCalendrierNonOuvre:
    """Les jours non ouvrés sont déduits du grand livre, non codés en dur.

    La semaine ouvrée court du dimanche au jeudi à Djibouti et du lundi au
    vendredi en France : signaler « samedi et dimanche » désignait 17 % du grand
    livre ARULOS (tous les dimanches, jours pleinement ouvrés) et laissait passer
    les vendredis.
    """

    @staticmethod
    def _dates(par_jour: dict[int, int]) -> list:
        """Fabrique des dates de 2024 selon un nombre d'occurrences par jour."""
        from datetime import datetime, timedelta
        lundi = datetime(2024, 1, 1)  # 1er janvier 2024 = lundi
        out = []
        for jour, n in par_jour.items():
            for k in range(n):
                out.append(lundi + timedelta(days=jour + 7 * k))
        return out

    def test_semaine_djiboutienne(self):
        # Activité du dimanche au jeudi, vendredi et samedi quasi vides
        jours, deduits = _jours_non_ouvres(self._dates(
            {0: 30, 1: 30, 2: 30, 3: 30, 4: 1, 5: 1, 6: 30}))
        assert deduits is True
        assert jours == frozenset({4, 5})  # vendredi, samedi

    def test_semaine_francaise(self):
        jours, deduits = _jours_non_ouvres(self._dates(
            {0: 30, 1: 30, 2: 30, 3: 30, 4: 30, 5: 1, 6: 1}))
        assert deduits is True
        assert jours == frozenset({5, 6})  # samedi, dimanche

    def test_entite_travaillant_tous_les_jours(self):
        jours, deduits = _jours_non_ouvres(self._dates({j: 20 for j in range(7)}))
        assert deduits is True
        assert jours == frozenset()  # le signal ne se déclenche jamais

    def test_population_insuffisante_repli_sur_la_convention(self):
        jours, deduits = _jours_non_ouvres(self._dates({0: 2, 6: 2}))
        assert deduits is False
        assert jours == JOURS_NON_OUVRES_DEFAUT

    def test_datation_trop_concentree_repli_sur_la_convention(self):
        # Tout est daté un lundi : la notion de jour non ouvré n'a plus de sens
        jours, deduits = _jours_non_ouvres(self._dates({0: POPULATION_MIN_CALENDRIER + 5}))
        assert deduits is False
        assert jours == JOURS_NON_OUVRES_DEFAUT

    def test_signal_suit_le_calendrier_deduit(self):
        """Sur un grand livre djiboutien, le dimanche n'est pas signalé, le vendredi l'est."""
        from datetime import datetime, timedelta
        lundi = datetime(2024, 1, 1)
        rows = []
        # 30 écritures par jour ouvré (dimanche→jeudi), aucune vendredi/samedi
        for jour in (0, 1, 2, 3, 6):
            for k in range(30):
                d = (lundi + timedelta(days=jour + 7 * k)).strftime("%Y-%m-%d")
                rows += _piece_equilibree(f"J{jour}-{k}", 1000, date=d)
        dimanche = (lundi + timedelta(days=6)).strftime("%Y-%m-%d")
        vendredi = (lundi + timedelta(days=4)).strftime("%Y-%m-%d")
        rows += _piece_equilibree("DIM", 1000, date=dimanche)
        rows += _piece_equilibree("VEN", 1000, date=vendredi)

        a = analyser_journal(rows, seuil=1_000_000_000, exercice="2024", seuil_signalement=1)
        assert a["jours_non_ouvres_deduits"] is True
        assert a["jours_non_ouvres_libelles"] == ["vendredi", "samedi"]
        assert "weekend" not in _signaux(a, "DIM")
        assert "weekend" in _signaux(a, "VEN")


class TestSignalNonDiscriminant:
    """Un signal déclenché sur une part trop large de la population est neutralisé.

    Généralisation du garde-fou « sans pièce » : un signal quasi universel décrit
    le fichier (format d'export, calendrier, identification des écritures) et non
    un risque de fraude. Il est retiré du score mais versé au dossier.
    """

    @staticmethod
    def _ledger_desequilibre(n: int) -> list:
        rows = []
        for i in range(n):
            rows += [_row("601000", debit=1000, piece=f"D{i}"),
                     _row("401000", credit=700, piece=f"D{i}")]
        return rows

    def test_neutralise_au_dela_du_taux(self):
        a = analyser_journal(self._ledger_desequilibre(POPULATION_MIN_NEUTRALISATION),
                            seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert "desequilibre" in a["signaux_neutralises"]
        assert a["signaux_neutralises"]["desequilibre"] == 1.0
        assert a["par_signal"].get("desequilibre", 0) == 0
        # Le score est recalculé sans le signal neutralisé : plus rien n'est retenu
        assert a["nb_signalees"] == 0

    def test_signal_minoritaire_conserve(self):
        n = POPULATION_MIN_NEUTRALISATION
        rows = self._ledger_desequilibre(int(n * 0.2))
        for i in range(n):  # complément d'écritures saines
            rows += _piece_equilibree(f"OK{i}", 1000)
        a = analyser_journal(rows, seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["signaux_neutralises"] == {}
        assert a["par_signal"]["desequilibre"] == int(n * 0.2)

    def test_pas_de_neutralisation_sur_petite_population(self):
        # Trop peu d'écritures pour que la statistique soit stable
        a = analyser_journal(self._ledger_desequilibre(3),
                            seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["signaux_neutralises"] == {}
        assert a["par_signal"]["desequilibre"] == 3

    def test_taux_signalement_rapporte(self):
        a = analyser_journal(self._ledger_desequilibre(3),
                            seuil=1_000_000, exercice="2024", seuil_signalement=1)
        assert a["taux_signalement"] == 1.0


# ─── Route API ────────────────────────────────────────────────────────────────

class TestRouteJET:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    @staticmethod
    def _semer_grand_livre(pid: str, ecritures: list[tuple]) -> None:
        """Sème un grand livre importé : (piece, date, compte, debit, credit) par ligne."""
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        db.save_fichier_source({
            "id": "f-gl", "projet_id": pid, "nom": "gl.xlsx",
            "type": "grand_livre", "type_document": "grand_livre",
        })
        donnees = []

        def _d(ligne: int, col: str, valeur, type_: str):
            donnees.append({
                "id": str(uuid.uuid4()), "projet_id": pid,
                "fichier_source_id": "f-gl", "valeur": valeur, "type": type_,
                "localisation": f"gl.xlsx:{ligne}:{col}",
            })

        for i, (piece, date, compte, debit, credit) in enumerate(ecritures):
            _d(i, "NumeroPiece", piece, "numero_piece")
            _d(i, "Date", date, "date")
            _d(i, "Compte", compte, "compte")
            _d(i, "Debit", debit, "montant")
            _d(i, "Credit", credit, "montant")
        db.save_donnees_sourcees(donnees)
        db.update_projet(pid, {"etat_courant": "travaux_substantifs",
                               "seuil_signification": 1_000_000, "exercice": "2024"})

    def test_signal_neutralise_documente_au_dossier(self, client):
        """Un signal neutralisé produit un résultat qui l'explique — pas un « aucune
        écriture concernée », qui laisserait croire le grand livre équilibré."""
        pid = client.post("/api/projets", json={"nom": "T-D1-neutre"}).json()["id"]
        lignes = []
        for i in range(POPULATION_MIN_NEUTRALISATION):
            lignes.append((f"D{i}", "2024-06-12", "601000", 1000, 0))
            lignes.append((f"D{i}", "2024-06-12", "401000", 0, 700))
        self._semer_grand_livre(pid, lignes)

        r = client.post(f"/api/projets/{pid}/controles/journal-entries")
        assert r.status_code == 200, r.text
        analyse = r.json()["analyse"]
        assert "desequilibre" in analyse["signaux_neutralises"]
        assert r.json()["nb_signalees"] == 0

        from probare_engine.api.routes import _get_db
        res = [x for x in _get_db(pid).list_resultats(pid)
               if x["controle_ref"] == "JET-DESEQUILIBRE"]
        assert len(res) == 1
        assert res[0]["statut"] == "ok"
        assert "neutralisé" in res[0]["details"]
        assert "100.0 %" in res[0]["details"]
        # Aucune exception : le signal ne désigne pas un risque, il décrit le fichier
        excs = [e for e in _get_db(pid).list_exceptions(pid)
                if e["controle_ref"] == "JET-DESEQUILIBRE"]
        assert excs == []

    def test_refuse_sans_grand_livre(self, client):
        pid = client.post("/api/projets", json={"nom": "T-D1"}).json()["id"]
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        db.update_projet(pid, {"etat_courant": "travaux_substantifs"})
        # Aucune donnée importée
        r = client.post(f"/api/projets/{pid}/controles/journal-entries")
        assert r.status_code == 400

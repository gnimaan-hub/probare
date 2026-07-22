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


# ─── Route API ────────────────────────────────────────────────────────────────

class TestRouteJET:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def test_refuse_sans_grand_livre(self, client):
        pid = client.post("/api/projets", json={"nom": "T-D1"}).json()["id"]
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        db.update_projet(pid, {"etat_courant": "travaux_substantifs"})
        # Aucune donnée importée
        r = client.post(f"/api/projets/{pid}/controles/journal-entries")
        assert r.status_code == 400

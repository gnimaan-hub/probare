"""Moteur de contrôles déterministes — 27 contrôles, 3 cycles."""
from __future__ import annotations
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from ..provenance.models import DonneeSourcee
from .registry import REGISTRE


# ─── Types ────────────────────────────────────────────────────────────────────

# Un RowDict regroupe les DonneeSourcees d'une même ligne comptable.
# Clés possibles : 'compte', 'libelle', 'date', 'debit', 'credit', 'solde', 'numero_piece'
RowDict = dict[str, DonneeSourcee]


# ─── Utilitaires internes ──────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_ok(projet_id: str, controle_ref: str, valeur: Any,
               details: str, sources: list[str]) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        "controle_ref": controle_ref,
        "valeur": float(valeur) if isinstance(valeur, (int, float)) else None,
        "statut": "ok",
        "details": details,
        "sources": sources,
        "calcule_le": _now(),
    }


def _result_exception(projet_id: str, controle_ref: str, valeur: Any,
                      details: str, sources: list[str]) -> tuple[dict, dict]:
    defn = REGISTRE.get(controle_ref)
    nep_ref = defn.nep_ref if defn else "NEP 500"
    severite = defn.severite_defaut if defn else "significative"
    res = {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        "controle_ref": controle_ref,
        "valeur": float(valeur) if isinstance(valeur, (int, float)) else None,
        "statut": "exception",
        "details": details,
        "sources": sources,
        "calcule_le": _now(),
    }
    exc = {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        "controle_ref": controle_ref,
        "nep_ref": nep_ref,
        "severite": severite,
        "description": details,
        "statut": "ouverte",
        "sources": sources,
        "horodatage": _now(),
    }
    return res, exc


def _get_amount(row: RowDict, field: str) -> float:
    d = row.get(field)
    if d is None:
        return 0.0
    try:
        return float(d.valeur) if d.valeur is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _get_str(row: RowDict, field: str) -> str:
    d = row.get(field)
    return str(d.valeur or "").strip() if d else ""


def _sources_from_rows(rows: list[RowDict], *fields: str) -> list[str]:
    out = []
    for row in rows:
        for f in fields:
            d = row.get(f)
            if d:
                out.append(d.id)
    return out


def _is_round(amount: float, divisor: float = 100.0) -> bool:
    """Un montant est considéré 'rond' si divisible par divisor sans reste."""
    if amount <= 0:
        return False
    return abs(amount % divisor) < 0.005


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y",
                "%Y/%m/%d", "%d %m %Y", "%d-%b-%Y", "%d/%b/%Y"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _exercice_end(exercice: str | None) -> datetime | None:
    if not exercice:
        return None
    m = re.search(r"(\d{4})", str(exercice))
    if m:
        return datetime(int(m.group(1)), 12, 31)
    return None


# ─── Utilitaire de regroupement de lignes ─────────────────────────────────────

def _group_rows(donnees: list[DonneeSourcee]) -> list[RowDict]:
    """
    Regroupe les DonneeSourcees en lignes sémantiques.
    La localisation a le format '{source}:{row}:{col}'.
    """
    raw: dict[tuple, RowDict] = {}
    for d in donnees:
        parts = d.localisation.rsplit(":", 2)
        if len(parts) < 3:
            continue
        row_key = (d.fichier_source_id, parts[1])
        col = parts[2].lower().strip()
        if row_key not in raw:
            raw[row_key] = {}
        row = raw[row_key]

        if d.type == "compte":
            row["compte"] = d
        elif d.type == "numero_piece":
            row["numero_piece"] = d
        elif d.type == "date":
            row["date"] = d
        elif d.type == "montant":
            if any(k in col for k in ("debit", "débit", ":db", "db:")):
                row["debit"] = d
            elif any(k in col for k in ("credit", "crédit", ":cr", "cr:")):
                row["credit"] = d
            elif any(k in col for k in ("solde", "balance", "sold")):
                # Avoid capturing debit/credit as solde
                if not any(k in col for k in ("debit", "crédit", "credit", "débit")):
                    row["solde"] = d
        elif d.type == "texte":
            if any(k in col for k in ("libelle", "libellé", "label", "désig", "intitul")):
                row["libelle"] = d

    return list(raw.values())


def _filter_accounts(rows: list[RowDict], prefixes: tuple[str, ...]) -> list[RowDict]:
    """Filtre les lignes dont le compte commence par l'un des préfixes donnés."""
    result = []
    for row in rows:
        c = row.get("compte")
        if c and str(c.valeur or "").startswith(prefixes):
            result.append(row)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRÔLES EXISTANTS (conservés, signatures inchangées)
# ═══════════════════════════════════════════════════════════════════════════════

def controle_equilibre_balance(
    projet_id: str,
    donnees_debit: list[DonneeSourcee],
    donnees_credit: list[DonneeSourcee],
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """TRESOR-BAL-EQUIL : Σ débits = Σ crédits."""
    total_debit = sum(float(d.valeur) for d in donnees_debit if d.valeur is not None)
    total_credit = sum(float(d.valeur) for d in donnees_credit if d.valeur is not None)
    ecart = abs(total_debit - total_credit)
    sources = [d.id for d in donnees_debit + donnees_credit]

    if ecart <= tolerance:
        return _result_ok(
            projet_id, "TRESOR-BAL-EQUIL", ecart,
            f"Balance équilibrée. Σ Débit={total_debit:.2f}, Σ Crédit={total_credit:.2f}",
            sources,
        ), None
    else:
        res, exc = _result_exception(
            projet_id, "TRESOR-BAL-EQUIL", ecart,
            f"Balance déséquilibrée. Écart={ecart:.2f}. "
            f"Σ Débit={total_debit:.2f}, Σ Crédit={total_credit:.2f}",
            sources,
        )
        return res, exc


def controle_coherence_gl_balance(
    projet_id: str,
    gl_par_compte: dict[str, tuple[float, list[str]]],
    balance_par_compte: dict[str, tuple[float, list[str]]],
    tolerance: float = 0.01,
) -> tuple[list[dict], list[dict]]:
    """TRESOR-GL-COHER : mouvements GL = soldes balance par compte."""
    resultats, exceptions = [], []
    tous_comptes = set(gl_par_compte) | set(balance_par_compte)

    for compte in sorted(tous_comptes):
        gl_val, gl_src = gl_par_compte.get(compte, (0.0, []))
        bal_val, bal_src = balance_par_compte.get(compte, (0.0, []))
        ecart = abs(gl_val - bal_val)
        sources = gl_src + bal_src

        if ecart <= tolerance:
            resultats.append(_result_ok(
                projet_id, "TRESOR-GL-COHER", ecart,
                f"Compte {compte} cohérent. GL={gl_val:.2f}, Balance={bal_val:.2f}",
                sources,
            ))
        else:
            res, exc = _result_exception(
                projet_id, "TRESOR-GL-COHER", ecart,
                f"Compte {compte} : incohérence GL/Balance. "
                f"GL={gl_val:.2f}, Balance={bal_val:.2f}, Écart={ecart:.2f}",
                sources,
            )
            resultats.append(res)
            exceptions.append(exc)

    return resultats, exceptions


def controle_addition(
    projet_id: str,
    total_affiche: DonneeSourcee,
    donnees_lignes: list[DonneeSourcee],
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """TRESOR-ADDITION : recalcul indépendant du total affiché."""
    total_recalcule = sum(float(d.valeur) for d in donnees_lignes if d.valeur is not None)
    ecart = abs(float(total_affiche.valeur) - total_recalcule) if total_affiche.valeur is not None else float("inf")
    sources = [total_affiche.id] + [d.id for d in donnees_lignes]

    if ecart <= tolerance:
        return _result_ok(
            projet_id, "TRESOR-ADDITION", ecart,
            f"Foliotage OK. Total affiché={total_affiche.valeur}, Recalculé={total_recalcule:.2f}",
            sources,
        ), None
    else:
        res, exc = _result_exception(
            projet_id, "TRESOR-ADDITION", ecart,
            f"Erreur de foliotage. Affiché={total_affiche.valeur}, Recalculé={total_recalcule:.2f}, Écart={ecart:.2f}",
            sources,
        )
        return res, exc


def controle_sequence_pieces(
    projet_id: str,
    numeros: list[DonneeSourcee],
    controle_ref: str = "TRESOR-SEQ-PIECES",
) -> tuple[dict, dict | None]:
    """Détection de trous et doublons dans les numéros de pièces."""
    vals: list[tuple[int, str]] = []
    for d in numeros:
        try:
            raw = str(d.valeur).strip()
            num = int(float(raw))
            vals.append((num, d.id))
        except (ValueError, TypeError):
            continue

    if not vals:
        return _result_ok(
            projet_id, controle_ref, 0,
            "Aucun numéro de pièce numérique à vérifier.", [],
        ), None

    nums = [v[0] for v in vals]
    sources = [v[1] for v in vals]
    num_min, num_max = min(nums), max(nums)
    attendus = set(range(num_min, num_max + 1))
    presents = set(nums)
    trous = sorted(attendus - presents)
    doublons = sorted(set(n for n in nums if nums.count(n) > 1))

    issues = []
    if trous:
        affichage = trous[:10]
        suffix = f"… ({len(trous)} au total)" if len(trous) > 10 else ""
        issues.append(f"Trous : {affichage}{suffix}")
    if doublons:
        affichage = doublons[:10]
        suffix = f"… ({len(doublons)} au total)" if len(doublons) > 10 else ""
        issues.append(f"Doublons : {affichage}{suffix}")

    if not issues:
        return _result_ok(
            projet_id, controle_ref, 0,
            f"Séquence continue de {num_min} à {num_max}. {len(nums)} pièces vérifiées.",
            sources,
        ), None
    else:
        res, exc = _result_exception(
            projet_id, controle_ref, len(trous) + len(doublons),
            f"Anomalies de séquence détectées ({len(trous)} trou(s), {len(doublons)} doublon(s)). "
            + " | ".join(issues),
            sources,
        )
        return res, exc


def controle_variations(
    projet_id: str,
    soldes_n: dict[str, tuple[float, list[str]]],
    soldes_n1: dict[str, tuple[float, list[str]]],
    seuil_signification: float,
    controle_ref: str = "TRESOR-VARIATION",
) -> tuple[list[dict], list[dict]]:
    """Variations N/N-1 au-delà du seuil de signification."""
    resultats, exceptions = [], []
    tous_comptes = set(soldes_n) | set(soldes_n1)

    for compte in sorted(tous_comptes):
        val_n, src_n = soldes_n.get(compte, (0.0, []))
        val_n1, src_n1 = soldes_n1.get(compte, (0.0, []))
        variation = abs(val_n - val_n1)
        sources = src_n + src_n1

        if variation > seuil_signification:
            pct = (variation / val_n1 * 100) if val_n1 != 0 else float("inf")
            res, exc = _result_exception(
                projet_id, controle_ref, variation,
                f"Compte {compte} : variation N/N-1={variation:.2f} ({pct:.1f}%) > seuil={seuil_signification:.2f}. "
                f"N={val_n:.2f}, N-1={val_n1:.2f}",
                sources,
            )
            resultats.append(res)
            exceptions.append(exc)
        else:
            resultats.append(_result_ok(
                projet_id, controle_ref, variation,
                f"Compte {compte} : variation={variation:.2f} ≤ seuil={seuil_signification:.2f}",
                sources,
            ))

    return resultats, exceptions


def controle_rapprochement_bancaire(
    projet_id: str,
    solde_comptable: DonneeSourcee,
    solde_releve: DonneeSourcee,
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """TRESOR-RAPPROCH : solde comptable vs solde relevé bancaire."""
    val_compta = float(solde_comptable.valeur) if solde_comptable.valeur is not None else 0.0
    val_releve = float(solde_releve.valeur) if solde_releve.valeur is not None else 0.0
    ecart = abs(val_compta - val_releve)
    sources = [solde_comptable.id, solde_releve.id]

    if ecart <= tolerance:
        return _result_ok(
            projet_id, "TRESOR-RAPPROCH", ecart,
            f"Rapprochement OK. Comptable={val_compta:.2f}, Relevé={val_releve:.2f}",
            sources,
        ), None
    else:
        res, exc = _result_exception(
            projet_id, "TRESOR-RAPPROCH", ecart,
            f"Écart de rapprochement={ecart:.2f}. Comptable={val_compta:.2f}, Relevé={val_releve:.2f}",
            sources,
        )
        return res, exc


# ═══════════════════════════════════════════════════════════════════════════════
# NOUVEAUX CONTRÔLES — TRÉSORERIE
# ═══════════════════════════════════════════════════════════════════════════════

def controle_soldes_anormaux_tresorerie(
    projet_id: str,
    rows: list[RowDict],
    tolerance: float = 0.01,
) -> tuple[list[dict], list[dict]]:
    """TRESOR-SOLDE-ANORMAL : comptes 5xx avec solde net créditeur."""
    rows_5xx = _filter_accounts(rows, ("5",))
    if not rows_5xx:
        return [_result_ok(projet_id, "TRESOR-SOLDE-ANORMAL", 0,
                           "Aucun compte de trésorerie (5xx) dans les données.", [])], []

    # Agréger par numéro de compte
    par_compte: dict[str, dict] = {}
    for row in rows_5xx:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        if num not in par_compte:
            par_compte[num] = {"debit": 0.0, "credit": 0.0, "sources": []}
        par_compte[num]["debit"] += _get_amount(row, "debit") + max(_get_amount(row, "solde"), 0)
        par_compte[num]["credit"] += _get_amount(row, "credit") + abs(min(_get_amount(row, "solde"), 0))
        par_compte[num]["sources"].append(c.id)

    resultats, exceptions = [], []
    for compte, data in sorted(par_compte.items()):
        d, cr, srcs = data["debit"], data["credit"], data["sources"]
        net = d - cr
        if net < -tolerance:
            res, exc = _result_exception(
                projet_id, "TRESOR-SOLDE-ANORMAL", abs(net),
                f"Compte {compte} : solde créditeur anormal de {abs(net):.2f}. "
                f"Σ Débit={d:.2f}, Σ Crédit={cr:.2f}. "
                f"Un compte de trésorerie ne devrait pas présenter de solde créditeur "
                f"hors découvert bancaire autorisé.",
                srcs,
            )
            resultats.append(res)
            exceptions.append(exc)
        else:
            resultats.append(_result_ok(
                projet_id, "TRESOR-SOLDE-ANORMAL", net,
                f"Compte {compte} : solde débiteur normal. Net={net:.2f}",
                srcs,
            ))

    return resultats, exceptions


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRÔLES PARTAGÉS (utilisés par les 3 cycles)
# ═══════════════════════════════════════════════════════════════════════════════

def controle_coherence_cycle(
    projet_id: str,
    controle_ref: str,
    rows_gl: list[RowDict],
    rows_balance: list[RowDict],
    compte_prefixes: tuple[str, ...],
    tolerance: float = 0.01,
) -> tuple[list[dict], list[dict]]:
    """
    Cohérence GL/balance pour un ensemble de comptes identifiés par leurs préfixes.
    GL : somme des mouvements (Σdébit - Σcrédit) par compte.
    Balance : solde net (colonne Solde, ou Σdébit - Σcrédit) par compte.
    """
    gl_filtres = _filter_accounts(rows_gl, compte_prefixes)
    bal_filtres = _filter_accounts(rows_balance, compte_prefixes)

    if not gl_filtres and not bal_filtres:
        return [_result_ok(projet_id, controle_ref, 0,
                           f"Aucun compte {compte_prefixes} trouvé dans les données importées.", [])], []

    # Agréger GL par compte : net = Σdebit - Σcredit
    gl_par_compte: dict[str, tuple[float, list[str]]] = {}
    for row in gl_filtres:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        prev_net, prev_srcs = gl_par_compte.get(num, (0.0, []))
        net = _get_amount(row, "debit") - _get_amount(row, "credit")
        gl_par_compte[num] = (prev_net + net, prev_srcs + [c.id])

    # Agréger balance par compte
    bal_par_compte: dict[str, tuple[float, list[str]]] = {}
    for row in bal_filtres:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        prev_net, prev_srcs = bal_par_compte.get(num, (0.0, []))
        s = _get_amount(row, "solde")
        if s != 0:
            net = s
        else:
            net = _get_amount(row, "debit") - _get_amount(row, "credit")
        bal_par_compte[num] = (prev_net + net, prev_srcs + [c.id])

    tous_comptes = set(gl_par_compte) | set(bal_par_compte)
    resultats, exceptions = [], []

    for compte in sorted(tous_comptes):
        gl_net, gl_srcs = gl_par_compte.get(compte, (0.0, []))
        bal_net, bal_srcs = bal_par_compte.get(compte, (0.0, []))
        ecart = abs(gl_net - bal_net)
        sources = gl_srcs + bal_srcs

        if ecart <= tolerance:
            resultats.append(_result_ok(
                projet_id, controle_ref, ecart,
                f"Compte {compte} cohérent. GL net={gl_net:.2f}, Balance={bal_net:.2f}",
                sources,
            ))
        else:
            res, exc = _result_exception(
                projet_id, controle_ref, ecart,
                f"Compte {compte} : GL net={gl_net:.2f} ≠ Balance={bal_net:.2f}. "
                f"Écart={ecart:.2f}. Risque d'incohérence ou d'écriture manquante.",
                sources,
            )
            resultats.append(res)
            exceptions.append(exc)

    return resultats, exceptions


def controle_soldes_anormaux(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    compte_prefixes: tuple[str, ...],
    sens_normal: str,  # "debit" ou "credit"
    tolerance: float = 0.01,
) -> tuple[list[dict], list[dict]]:
    """
    Détecte les soldes anormaux sur des comptes d'un cycle.
    - sens_normal='debit'  : le solde devrait être débiteur (ex: clients 41x).
    - sens_normal='credit' : le solde devrait être créditeur (ex: fournisseurs 40x).
    """
    rows_f = _filter_accounts(rows, compte_prefixes)
    if not rows_f:
        return [_result_ok(projet_id, controle_ref, 0,
                           f"Aucun compte {compte_prefixes} trouvé.", [])], []

    par_compte: dict[str, dict] = {}
    for row in rows_f:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        if num not in par_compte:
            par_compte[num] = {"debit": 0.0, "credit": 0.0, "sources": []}
        s = _get_amount(row, "solde")
        if s != 0:
            if s > 0:
                par_compte[num]["debit"] += s
            else:
                par_compte[num]["credit"] += abs(s)
        else:
            par_compte[num]["debit"] += _get_amount(row, "debit")
            par_compte[num]["credit"] += _get_amount(row, "credit")
        par_compte[num]["sources"].append(c.id)

    resultats, exceptions = [], []
    for compte, data in sorted(par_compte.items()):
        d, cr, srcs = data["debit"], data["credit"], data["sources"]
        net = d - cr  # positive = debit balance, negative = credit balance
        is_abnormal = (sens_normal == "debit" and net < -tolerance) or \
                      (sens_normal == "credit" and net > tolerance)

        if is_abnormal:
            label_anormal = "débiteur" if sens_normal == "credit" else "créditeur"
            label_normal = "créditeur" if sens_normal == "credit" else "débiteur"
            montant_anormal = abs(net)
            res, exc = _result_exception(
                projet_id, controle_ref, montant_anormal,
                f"Compte {compte} : solde {label_anormal} anormal de {montant_anormal:.2f}. "
                f"Σ Débit={d:.2f}, Σ Crédit={cr:.2f}. "
                f"Ce type de compte devrait normalement présenter un solde {label_normal}.",
                srcs,
            )
            resultats.append(res)
            exceptions.append(exc)
        else:
            resultats.append(_result_ok(
                projet_id, controle_ref, abs(net),
                f"Compte {compte} : solde net={net:.2f} (normal pour ce type de compte).",
                srcs,
            ))

    return resultats, exceptions


def controle_montants_ronds(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    compte_prefixes: tuple[str, ...],
    seuil_ratio: float = 0.40,
    diviseur: float = 100.0,
) -> tuple[dict, dict | None]:
    """
    Détecte une proportion anormalement élevée de montants ronds dans les mouvements d'un cycle.
    Un montant rond est défini comme multiple de `diviseur` (défaut: 100).
    """
    rows_f = _filter_accounts(rows, compte_prefixes)
    if not rows_f:
        return _result_ok(projet_id, controle_ref, 0,
                          f"Aucun compte {compte_prefixes} trouvé.", []), None

    montants = []
    sources = []
    for row in rows_f:
        for field in ("debit", "credit", "solde"):
            d = row.get(field)
            if d and d.valeur is not None:
                try:
                    amt = float(d.valeur)
                    if amt > 0:
                        montants.append(amt)
                        sources.append(d.id)
                except (ValueError, TypeError):
                    pass

    if not montants:
        return _result_ok(projet_id, controle_ref, 0,
                          "Aucun montant à analyser.", []), None

    nb_ronds = sum(1 for m in montants if _is_round(m, diviseur))
    ratio = nb_ronds / len(montants)

    if ratio >= seuil_ratio:
        res, exc = _result_exception(
            projet_id, controle_ref, ratio,
            f"{nb_ronds}/{len(montants)} montants ronds ({ratio*100:.1f}%) — seuil={seuil_ratio*100:.0f}%. "
            f"Une proportion élevée de montants ronds (multiples de {diviseur:.0f}) peut indiquer "
            f"des montants estimés, fictifs ou arrondis avant comptabilisation.",
            sources[:50],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, controle_ref, ratio,
            f"{nb_ronds}/{len(montants)} montants ronds ({ratio*100:.1f}%) — dans la norme.",
            sources[:20],
        ), None


def controle_cut_off(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    compte_prefixes: tuple[str, ...],
    exercice: str | None,
    nb_jours: int = 15,
    seuil_ratio: float = 0.30,
) -> tuple[dict, dict | None]:
    """
    Détecte une concentration d'écritures dans les nb_jours derniers jours de l'exercice.
    Nécessite une colonne 'date' dans les données.
    """
    fin_exercice = _exercice_end(exercice)
    rows_f = _filter_accounts(rows, compte_prefixes)

    if not fin_exercice:
        return _result_ok(projet_id, controle_ref, 0,
                          "Exercice non renseigné, analyse cut-off ignorée.", []), None

    debut_fenetre = fin_exercice - timedelta(days=nb_jours - 1)

    rows_avec_date = [(row, _parse_date(_get_str(row, "date")))
                      for row in rows_f if row.get("date")]
    rows_avec_date = [(row, dt) for row, dt in rows_avec_date if dt is not None]

    if not rows_avec_date:
        return _result_ok(projet_id, controle_ref, 0,
                          "Aucune date trouvée dans les données, analyse cut-off ignorée.", []), None

    total = len(rows_avec_date)
    en_fenetre = [(row, dt) for row, dt in rows_avec_date
                  if debut_fenetre <= dt <= fin_exercice]
    nb_fenetre = len(en_fenetre)
    ratio = nb_fenetre / total

    sources = [row.get("compte").id for row, _ in en_fenetre if row.get("compte")]

    if ratio >= seuil_ratio:
        res, exc = _result_exception(
            projet_id, controle_ref, ratio,
            f"{nb_fenetre}/{total} écritures ({ratio*100:.1f}%) dans les {nb_jours} derniers jours "
            f"de l'exercice {exercice or ''} — seuil={seuil_ratio*100:.0f}%. "
            f"Cette concentration est anormale et signale un risque de cut-off.",
            sources[:50],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, controle_ref, ratio,
            f"{nb_fenetre}/{total} écritures ({ratio*100:.1f}%) en fin d'exercice — dans la norme.",
            sources[:20],
        ), None


def controle_doublons_factures(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    compte_prefixes: tuple[str, ...],
) -> tuple[dict, dict | None]:
    """
    Détecte les factures en doublon : même compte + même montant + même numéro de pièce.
    Détecte également les doublons par (compte, montant) sans numéro de pièce distinct.
    """
    rows_f = _filter_accounts(rows, compte_prefixes)
    if not rows_f:
        return _result_ok(projet_id, controle_ref, 0,
                          f"Aucun compte {compte_prefixes} trouvé.", []), None

    # Clé exacte : (compte, montant, numero_piece)
    vus_exact: dict[tuple, list[str]] = defaultdict(list)
    # Clé large : (compte, montant) pour détecter doublons sans numéro de pièce
    vus_large: dict[tuple, list[str]] = defaultdict(list)

    for row in rows_f:
        compte_val = _get_str(row, "compte")
        piece_val = _get_str(row, "numero_piece")
        montant = max(_get_amount(row, "debit"), _get_amount(row, "credit"),
                      abs(_get_amount(row, "solde")))
        if montant <= 0:
            continue
        montant_arrondi = round(montant, 2)
        src = (row.get("compte") or row.get("debit") or row.get("credit"))
        src_id = src.id if src else str(uuid.uuid4())

        if piece_val:
            vus_exact[(compte_val, montant_arrondi, piece_val)].append(src_id)
        vus_large[(compte_val, montant_arrondi)].append(src_id)

    doublons = []
    all_sources = []

    for (compte, montant, piece), ids in vus_exact.items():
        if len(ids) > 1:
            doublons.append(f"Compte {compte} | Pièce {piece} | Montant {montant:.2f} ({len(ids)} fois)")
            all_sources.extend(ids)

    # Doublons par montant uniquement (sans pièce ou pièce différente)
    for (compte, montant), ids in vus_large.items():
        if len(ids) > 1 and len(ids) <= 5:  # Éviter les faux positifs sur petits montants répétitifs
            key_ids = set(ids)
            # Ne signaler que si non déjà couvert par doublon exact
            deja_exact = any(
                set(v) == key_ids
                for (c, m, _), v in vus_exact.items()
                if c == compte and m == montant
            )
            if not deja_exact:
                doublons.append(f"Compte {compte} | Montant {montant:.2f} sans pièce distincte ({len(ids)} occurrences)")
                all_sources.extend(ids[:5])

    if doublons:
        res, exc = _result_exception(
            projet_id, controle_ref, len(doublons),
            f"{len(doublons)} doublon(s) détecté(s) : " + " | ".join(doublons[:5]),
            list(dict.fromkeys(all_sources))[:50],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, controle_ref, 0,
            f"Aucun doublon détecté parmi les {len(rows_f)} lignes analysées.",
            _sources_from_rows(rows_f[:20], "compte"),
        ), None


def controle_concentration_compte(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    compte_prefixes: tuple[str, ...],
    sens: str,  # "credit" pour fournisseurs (40x), "debit" pour clients (41x)
    seuil_concentration: float = 0.30,
) -> tuple[dict, dict | None]:
    """
    Détecte une concentration des flux sur un seul compte (fournisseur ou client).
    Chaque numéro de compte = un tiers distinct.
    """
    rows_f = _filter_accounts(rows, compte_prefixes)
    if not rows_f:
        return _result_ok(projet_id, controle_ref, 0,
                          f"Aucun compte {compte_prefixes} trouvé.", []), None

    par_compte: dict[str, tuple[float, list[str]]] = {}
    for row in rows_f:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        montant = _get_amount(row, sens)
        if montant <= 0:
            continue
        prev, srcs = par_compte.get(num, (0.0, []))
        par_compte[num] = (prev + montant, srcs + [c.id])

    if not par_compte:
        return _result_ok(projet_id, controle_ref, 0,
                          "Aucun flux dans le sens attendu.", []), None

    total = sum(v for v, _ in par_compte.values())
    if total <= 0:
        return _result_ok(projet_id, controle_ref, 0, "Total nul.", []), None

    compte_max, (montant_max, srcs_max) = max(par_compte.items(), key=lambda x: x[1][0])
    ratio = montant_max / total

    label = "crédit" if sens == "credit" else "débit"
    if ratio >= seuil_concentration:
        res, exc = _result_exception(
            projet_id, controle_ref, ratio,
            f"Compte {compte_max} représente {ratio*100:.1f}% des {label}s "
            f"({montant_max:.2f} / {total:.2f}) — seuil={seuil_concentration*100:.0f}%. "
            f"Concentration élevée sur un seul tiers : risque de dépendance ou de fraude.",
            srcs_max[:20],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, controle_ref, ratio,
            f"Concentration maximale : compte {compte_max} à {ratio*100:.1f}% — dans la norme.",
            srcs_max[:10],
        ), None


def controle_ratio_avoirs(
    projet_id: str,
    controle_ref: str,
    rows: list[RowDict],
    prefixe_tiers: tuple[str, ...],
    sens_avoir: str,  # "debit" pour avoirs fournisseurs (débit sur 40x), "credit" pour avoirs clients
    seuil_ratio: float = 0.05,
) -> tuple[dict, dict | None]:
    """
    Détecte un ratio avoirs/total anormal.
    - Avoirs fournisseurs : mouvements débiteurs sur les comptes 40x (remboursements)
    - Avoirs clients : mouvements créditeurs sur les comptes 41x (notes de crédit)
    Complété par la détection de lignes avec "AVOIR" dans le libellé.
    """
    rows_f = _filter_accounts(rows, prefixe_tiers)
    if not rows_f:
        return _result_ok(projet_id, controle_ref, 0,
                          f"Aucun compte {prefixe_tiers} trouvé.", []), None

    total = 0.0
    avoirs = 0.0
    sources_avoirs = []

    sens_normal = "credit" if sens_avoir == "debit" else "debit"

    for row in rows_f:
        mvt_normal = _get_amount(row, sens_normal)
        mvt_avoir = _get_amount(row, sens_avoir)
        libelle = _get_str(row, "libelle").upper()
        est_avoir = mvt_avoir > 0 or "AVOIR" in libelle or "AVOC" in libelle

        total += mvt_normal
        if est_avoir and mvt_avoir > 0:
            avoirs += mvt_avoir
            c = row.get("compte") or row.get(sens_avoir)
            if c:
                sources_avoirs.append(c.id)

    if total <= 0:
        return _result_ok(projet_id, controle_ref, 0, "Aucun flux à analyser.", []), None

    ratio = avoirs / total if total > 0 else 0.0

    if ratio >= seuil_ratio:
        res, exc = _result_exception(
            projet_id, controle_ref, ratio,
            f"Ratio avoirs / total = {ratio*100:.1f}% ({avoirs:.2f} / {total:.2f}) — "
            f"seuil={seuil_ratio*100:.0f}%. "
            f"Un ratio élevé d'avoirs signale des retours fréquents, des litiges ou "
            f"des régularisations suspectes.",
            sources_avoirs[:20],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, controle_ref, ratio,
            f"Ratio avoirs = {ratio*100:.1f}% ({avoirs:.2f} / {total:.2f}) — dans la norme.",
            sources_avoirs[:10],
        ), None


def controle_amortissement_manquant(
    projet_id: str,
    rows: list[RowDict],
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """
    IMO-AMORTISSEMENT : détecte des immobilisations amortissables (21x-25x) sans
    aucun amortissement cumulé correspondant (28xx).
    """
    rows_imo = _filter_accounts(rows, ("21", "22", "23", "24", "25"))
    rows_amort = _filter_accounts(rows, ("28",))

    if not rows_imo:
        return _result_ok(projet_id, "IMO-AMORTISSEMENT", 0,
                          "Aucune immobilisation corporelle/incorporelle (21x-25x) détectée.", []), None

    total_imo = 0.0
    sources_imo = []
    for row in rows_imo:
        c = row.get("compte")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        if s > 0:
            total_imo += s
            if c:
                sources_imo.append(c.id)

    if total_imo <= tolerance:
        return _result_ok(projet_id, "IMO-AMORTISSEMENT", 0,
                          "Aucune immobilisation nette positive à amortir.", []), None

    total_amort = 0.0
    for row in rows_amort:
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        total_amort += abs(s)

    if total_amort <= tolerance:
        res, exc = _result_exception(
            projet_id, "IMO-AMORTISSEMENT", total_imo,
            f"Immobilisations amortissables de {total_imo:.2f} (21x-25x) sans aucun amortissement "
            f"cumulé (28xx). Risque de sous-amortissement ou d'omission du plan d'amortissement.",
            sources_imo[:20],
        )
        return res, exc

    taux = total_amort / total_imo
    return _result_ok(
        projet_id, "IMO-AMORTISSEMENT", taux,
        f"Amortissements cumulés : {total_amort:.2f} pour {total_imo:.2f} d'immobilisations "
        f"({taux*100:.1f}%).",
        sources_imo[:10],
    ), None


def controle_amort_excedent(
    projet_id: str,
    rows: list[RowDict],
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """
    IMO-AMORT-EXCEDENT : détecte si les amortissements cumulés (28xx) dépassent
    la valeur brute des immobilisations (20x-27x hors 28xx).
    """
    rows_brut = _filter_accounts(rows, ("20", "21", "22", "23", "24", "25", "26", "27"))
    rows_amort = _filter_accounts(rows, ("28",))

    total_brut = 0.0
    sources_brut = []
    for row in rows_brut:
        c = row.get("compte")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        if s > 0:
            total_brut += s
            if c:
                sources_brut.append(c.id)

    if total_brut <= tolerance:
        return _result_ok(projet_id, "IMO-AMORT-EXCEDENT", 0,
                          "Aucune valeur brute d'immobilisation détectée.", []), None

    total_amort = 0.0
    sources_amort = []
    for row in rows_amort:
        c = row.get("compte")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        total_amort += abs(s)
        if c:
            sources_amort.append(c.id)

    sources = (sources_brut + sources_amort)[:30]

    if total_amort > total_brut + tolerance:
        excedent = total_amort - total_brut
        res, exc = _result_exception(
            projet_id, "IMO-AMORT-EXCEDENT", excedent,
            f"Amortissements cumulés ({total_amort:.2f}) supérieurs à la valeur brute "
            f"({total_brut:.2f}). Excédent de {excedent:.2f}. "
            f"Une immobilisation ne peut être amortie au-delà de sa valeur d'acquisition.",
            sources,
        )
        return res, exc

    return _result_ok(
        projet_id, "IMO-AMORT-EXCEDENT", total_amort,
        f"Amortissements ({total_amort:.2f}) ≤ valeur brute ({total_brut:.2f}) — cohérent.",
        sources[:10],
    ), None


def controle_ratio_charges_sociales(
    projet_id: str,
    rows: list[RowDict],
    seuil_min: float = 0.20,
    seuil_max: float = 0.60,
) -> tuple[dict, dict | None]:
    """
    PAIE-RATIO-SOCIAL : ratio cotisations patronales (645x) / salaires bruts (641x).
    Fourchette normale : 20 %–60 %. Hors fourchette → exception.
    """
    rows_salaires = _filter_accounts(rows, ("641",))
    rows_charges = _filter_accounts(rows, ("645",))

    if not rows_salaires:
        return _result_ok(projet_id, "PAIE-RATIO-SOCIAL", 0,
                          "Aucun compte de salaires (641x) détecté.", []), None

    total_salaires = 0.0
    sources_sal = []
    for row in rows_salaires:
        c = row.get("compte")
        s = _get_amount(row, "debit")
        if s == 0:
            s = abs(_get_amount(row, "solde"))
        total_salaires += s
        if c:
            sources_sal.append(c.id)

    if total_salaires <= 0:
        return _result_ok(projet_id, "PAIE-RATIO-SOCIAL", 0,
                          "Total salaires nul — contrôle non applicable.", []), None

    total_charges = 0.0
    sources_ch = []
    for row in rows_charges:
        c = row.get("compte")
        s = _get_amount(row, "debit")
        if s == 0:
            s = abs(_get_amount(row, "solde"))
        total_charges += s
        if c:
            sources_ch.append(c.id)

    ratio = total_charges / total_salaires
    sources = (sources_sal + sources_ch)[:30]

    if ratio < seuil_min or ratio > seuil_max:
        msg = (
            f"Ratio trop bas — risque de sous-déclaration des charges sociales."
            if ratio < seuil_min
            else "Ratio trop élevé — anomalie dans la structure salariale."
        )
        res, exc = _result_exception(
            projet_id, "PAIE-RATIO-SOCIAL", ratio,
            f"Ratio charges sociales / salaires = {ratio*100:.1f}% "
            f"({total_charges:.2f} / {total_salaires:.2f}). "
            f"Plage attendue : {seuil_min*100:.0f}%–{seuil_max*100:.0f}%. {msg}",
            sources,
        )
        return res, exc

    return _result_ok(
        projet_id, "PAIE-RATIO-SOCIAL", ratio,
        f"Ratio charges sociales / salaires = {ratio*100:.1f}% — dans la fourchette attendue.",
        sources[:10],
    ), None


def controle_mensualite_paie(
    projet_id: str,
    rows: list[RowDict],
    exercice: str | None,
    nb_mois_min: int = 10,
) -> tuple[dict, dict | None]:
    """
    PAIE-MENSUALITE : vérifie la régularité des paiements mensuels de salaires (641x-648x).
    Un exercice complet doit avoir des écritures dans au moins nb_mois_min mois.
    """
    fin_exercice = _exercice_end(exercice)
    rows_paie = _filter_accounts(rows, ("641", "642", "643", "644", "645", "646", "648"))

    if not fin_exercice:
        return _result_ok(projet_id, "PAIE-MENSUALITE", 0,
                          "Exercice non renseigné — analyse de mensualité ignorée.", []), None

    if not rows_paie:
        return _result_ok(projet_id, "PAIE-MENSUALITE", 0,
                          "Aucun compte de charges de personnel (641x-648x) détecté.", []), None

    annee = fin_exercice.year
    mois_presents: set[int] = set()
    sources = []

    for row in rows_paie:
        dt = _parse_date(_get_str(row, "date"))
        if dt and dt.year == annee:
            mois_presents.add(dt.month)
            c = row.get("compte")
            if c:
                sources.append(c.id)

    if not mois_presents:
        return _result_ok(projet_id, "PAIE-MENSUALITE", 0,
                          "Aucune date dans les écritures de paie — analyse ignorée.", []), None

    nb_mois = len(mois_presents)

    if nb_mois < nb_mois_min:
        mois_manquants = sorted(set(range(1, 13)) - mois_presents)
        res, exc = _result_exception(
            projet_id, "PAIE-MENSUALITE", nb_mois,
            f"Seulement {nb_mois}/12 mois avec des écritures de paie (641x). "
            f"Mois sans écriture : {mois_manquants}. "
            f"Risque d'omission de salaires ou de non-déclaration sur certaines périodes.",
            sources[:20],
        )
        return res, exc

    return _result_ok(
        projet_id, "PAIE-MENSUALITE", nb_mois,
        f"Paie présente sur {nb_mois}/12 mois — régularité satisfaisante.",
        sources[:10],
    ), None


def controle_tva_coherence(
    projet_id: str,
    rows: list[RowDict],
    seuil_ratio: float = 1.10,
) -> tuple[dict, dict | None]:
    """
    TAXE-TVA-COHERENCE : vérifie que la TVA déductible (4456x) ne dépasse pas anormalement
    la TVA collectée (4457x). Ratio > seuil_ratio → exception.
    """
    rows_deductible = _filter_accounts(rows, ("4456",))
    rows_collectee = _filter_accounts(rows, ("4457",))

    if not rows_deductible and not rows_collectee:
        return _result_ok(projet_id, "TAXE-TVA-COHERENCE", 0,
                          "Aucun compte TVA (4456x/4457x) détecté.", []), None

    total_deductible = 0.0
    sources_ded = []
    for row in rows_deductible:
        c = row.get("compte")
        s = _get_amount(row, "debit")
        if s == 0:
            s = abs(_get_amount(row, "solde"))
        total_deductible += s
        if c:
            sources_ded.append(c.id)

    total_collectee = 0.0
    sources_col = []
    for row in rows_collectee:
        c = row.get("compte")
        s = _get_amount(row, "credit")
        if s == 0:
            s = abs(_get_amount(row, "solde"))
        total_collectee += s
        if c:
            sources_col.append(c.id)

    sources = (sources_ded + sources_col)[:30]

    if total_collectee <= 0:
        if total_deductible > 0:
            res, exc = _result_exception(
                projet_id, "TAXE-TVA-COHERENCE", total_deductible,
                f"TVA déductible de {total_deductible:.2f} sans TVA collectée. "
                f"Anomalie : activité assujettie sans opérations taxables ?",
                sources,
            )
            return res, exc
        return _result_ok(projet_id, "TAXE-TVA-COHERENCE", 0,
                          "Aucun flux TVA (4456x/4457x) détecté.", []), None

    ratio = total_deductible / total_collectee

    if ratio > seuil_ratio:
        res, exc = _result_exception(
            projet_id, "TAXE-TVA-COHERENCE", ratio,
            f"TVA déductible ({total_deductible:.2f}) / collectée ({total_collectee:.2f}) = "
            f"{ratio*100:.1f}% — seuil={seuil_ratio*100:.0f}%. "
            f"La TVA récupérée excède anormalement la TVA collectée. "
            f"Risque de déductibilité incorrecte ou d'activité exonérée non identifiée.",
            sources,
        )
        return res, exc

    return _result_ok(
        projet_id, "TAXE-TVA-COHERENCE", ratio,
        f"TVA déductible / collectée = {ratio*100:.1f}% — cohérent.",
        sources[:10],
    ), None


def controle_mouvement_provisions(
    projet_id: str,
    rows: list[RowDict],
    seuil_ratio: float = 0.20,
) -> tuple[dict, dict | None]:
    """
    CP-PROVISION-MOUVEMENT : détecte des crédits sur provisions pour risques (15x)
    sans charge de dotation correspondante en 68x dans le grand livre.
    """
    rows_prov = _filter_accounts(rows, ("15",))
    rows_charges_prov = _filter_accounts(rows, ("68",))

    if not rows_prov:
        return _result_ok(projet_id, "CP-PROVISION-MOUVEMENT", 0,
                          "Aucun compte de provisions pour risques (15x) détecté.", []), None

    total_dotation_prov = 0.0
    sources_prov = []
    for row in rows_prov:
        c = row.get("compte")
        cr = _get_amount(row, "credit")
        if cr > 0:
            total_dotation_prov += cr
            if c:
                sources_prov.append(c.id)

    if total_dotation_prov <= 0:
        return _result_ok(projet_id, "CP-PROVISION-MOUVEMENT", 0,
                          "Aucune dotation aux provisions (crédit 15x) sur l'exercice.", []), None

    total_charges_dot = 0.0
    sources_charges = []
    for row in rows_charges_prov:
        c = row.get("compte")
        d = _get_amount(row, "debit")
        if d > 0:
            total_charges_dot += d
            if c:
                sources_charges.append(c.id)

    sources = (sources_prov + sources_charges)[:30]

    if total_charges_dot <= 0:
        res, exc = _result_exception(
            projet_id, "CP-PROVISION-MOUVEMENT", total_dotation_prov,
            f"Dotations provisions (crédit 15x) : {total_dotation_prov:.2f} sans aucune "
            f"charge de dotation (débit 68x). Risque de provision sans justification comptable.",
            sources_prov[:20],
        )
        return res, exc

    ratio = total_charges_dot / total_dotation_prov

    if ratio < seuil_ratio:
        res, exc = _result_exception(
            projet_id, "CP-PROVISION-MOUVEMENT", ratio,
            f"Dotations provisions 15x : {total_dotation_prov:.2f}, "
            f"Charges 68x : {total_charges_dot:.2f}. Ratio = {ratio*100:.1f}% < seuil={seuil_ratio*100:.0f}%. "
            f"Les dotations aux provisions semblent insuffisamment justifiées par les charges 68x.",
            sources,
        )
        return res, exc

    return _result_ok(
        projet_id, "CP-PROVISION-MOUVEMENT", ratio,
        f"Dotations provisions (15x) : {total_dotation_prov:.2f}, "
        f"Charges dotation (68x) : {total_charges_dot:.2f} — ratio {ratio*100:.1f}% cohérent.",
        sources[:10],
    ), None


def controle_coherence_resultat(
    projet_id: str,
    rows: list[RowDict],
    tolerance: float = 0.01,
) -> tuple[dict, dict | None]:
    """
    CP-RESULTAT-COHERENCE : vérifie que 120 (bénéfice) et 129 (déficit)
    ne sont pas tous deux non nuls simultanément dans la balance.
    """
    rows_120 = _filter_accounts(rows, ("120",))
    rows_129 = _filter_accounts(rows, ("129",))

    if not rows_120 and not rows_129:
        return _result_ok(projet_id, "CP-RESULTAT-COHERENCE", 0,
                          "Aucun compte de résultat (120/129) détecté.", []), None

    solde_120 = 0.0
    sources_120 = []
    for row in rows_120:
        c = row.get("compte")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "credit") - _get_amount(row, "debit")
        solde_120 += s
        if c:
            sources_120.append(c.id)

    solde_129 = 0.0
    sources_129 = []
    for row in rows_129:
        c = row.get("compte")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        solde_129 += s
        if c:
            sources_129.append(c.id)

    sources = (sources_120 + sources_129)[:20]

    if solde_120 > tolerance and solde_129 > tolerance:
        res, exc = _result_exception(
            projet_id, "CP-RESULTAT-COHERENCE", solde_120 + solde_129,
            f"Compte 120 (bénéfice : {solde_120:.2f}) et compte 129 (déficit : {solde_129:.2f}) "
            f"tous deux non nuls. Une entité ne peut avoir simultanément un résultat bénéficiaire "
            f"et déficitaire — erreur comptable ou mauvaise affectation du résultat.",
            sources,
        )
        return res, exc

    if solde_120 > tolerance:
        return _result_ok(
            projet_id, "CP-RESULTAT-COHERENCE", solde_120,
            f"Résultat bénéficiaire : {solde_120:.2f} (compte 120) — cohérent.",
            sources_120[:10],
        ), None

    if solde_129 > tolerance:
        return _result_ok(
            projet_id, "CP-RESULTAT-COHERENCE", solde_129,
            f"Résultat déficitaire : {solde_129:.2f} (compte 129) — cohérent.",
            sources_129[:10],
        ), None

    return _result_ok(
        projet_id, "CP-RESULTAT-COHERENCE", 0,
        "Aucun solde significatif dans les comptes de résultat (120/129).",
        sources,
    ), None


def controle_creances_echues(
    projet_id: str,
    rows: list[RowDict],
    exercice: str | None,
    nb_jours_seuil: int = 90,
    seuil_ratio: float = 0.10,
) -> tuple[dict, dict | None]:
    """
    VENTE-CREANCES-ECHUES : détecte les créances clients (41x) dont la date
    d'émission est antérieure à (fin_exercice - nb_jours), signalant un risque
    d'irrécouvrabilité non provisionné.
    """
    rows_41x = _filter_accounts(rows, ("41",))
    fin_exercice = _exercice_end(exercice)

    if not fin_exercice:
        return _result_ok("", "VENTE-CREANCES-ECHUES", 0,
                          "Exercice non renseigné, analyse des créances échues ignorée.", []), None

    seuil_date = fin_exercice - timedelta(days=nb_jours_seuil)

    total_debit = 0.0
    ancien_debit = 0.0
    sources_anciens = []

    for row in rows_41x:
        debit = _get_amount(row, "debit")
        if debit <= 0:
            continue
        total_debit += debit
        dt = _parse_date(_get_str(row, "date"))
        if dt and dt <= seuil_date:
            ancien_debit += debit
            c = row.get("compte") or row.get("debit")
            if c:
                sources_anciens.append(c.id)

    if total_debit <= 0:
        return _result_ok(projet_id, "VENTE-CREANCES-ECHUES", 0,
                          "Aucune créance client (41x) à analyser.", []), None

    ratio = ancien_debit / total_debit

    if ratio >= seuil_ratio:
        res, exc = _result_exception(
            projet_id, "VENTE-CREANCES-ECHUES", ratio,
            f"{ancien_debit:.2f} / {total_debit:.2f} ({ratio*100:.1f}%) de créances clients "
            f"ont plus de {nb_jours_seuil} jours (antérieures au {seuil_date.strftime('%d/%m/%Y')}). "
            f"Risque d'irrécouvrabilité non provisionné à évaluer.",
            sources_anciens[:30],
        )
        return res, exc
    else:
        return _result_ok(
            projet_id, "VENTE-CREANCES-ECHUES", ratio,
            f"Créances > {nb_jours_seuil}j : {ratio*100:.1f}% — dans la norme.",
            sources_anciens[:10],
        ), None

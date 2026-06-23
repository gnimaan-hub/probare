"""Procédures analytiques N/N-1 — calculs purement déterministes.

Règle fondamentale : aucun appel LLM ici. Uniquement des agrégats Python
à partir des DonneeSourcee stockées en base.
"""
from __future__ import annotations
import re
from typing import Any

PREFIXE_CA = ("70", "71", "72")
PREFIXE_CHARGES = ("60", "61", "62", "63", "64", "65", "66", "67", "68")
PREFIXE_PRODUITS = ("70", "71", "72", "73", "74", "75", "76", "77", "78")


def _reconstruire_balance(conn, projet_id: str, fichier_source_id: str) -> dict[str, dict]:
    """
    Reconstruit la balance comptable depuis les DonneeSourcee d'un fichier.
    Retourne { compte: {compte, libelle, debit, credit, solde} }.
    """
    rows = conn.execute(
        """SELECT valeur, type, localisation
           FROM donnee_sourcee
           WHERE projet_id=? AND fichier_source_id=?
           ORDER BY localisation""",
        (projet_id, fichier_source_id),
    ).fetchall()

    # Grouper par numéro de ligne (avant-dernier segment de la localisation)
    by_row: dict[str, dict[str, Any]] = {}
    for r in rows:
        loc = r["localisation"] or ""
        # format : {prefix}:{row_num}:{col_name}
        # on utilise rsplit pour être robuste aux préfixes contenant ':'
        parts = loc.rsplit(":", 2)
        if len(parts) < 3:
            continue
        row_key = parts[1]
        col_name = parts[2].lower().strip()
        if row_key not in by_row:
            by_row[row_key] = {}
        by_row[row_key][col_name] = {"valeur": r["valeur"], "type": r["type"]}

    balance: dict[str, dict] = {}
    for _row_key, cells in by_row.items():
        compte = None
        libelle = ""
        debit = 0.0
        credit = 0.0

        for col, cell in cells.items():
            v = cell["valeur"]
            t = cell["type"]

            if t == "compte" or any(k in col for k in ("compte", "account", "code_c")):
                if v:
                    compte = str(v).strip()
            elif t == "texte" and any(k in col for k in (
                "libelle", "libellé", "label", "intitule", "intitulé", "designation", "désig"
            )):
                libelle = str(v).strip() if v else ""
            elif t == "montant":
                try:
                    fval = float(v) if v is not None else 0.0
                except (ValueError, TypeError):
                    fval = 0.0
                if any(k in col for k in ("debit", "débit", " db", "_db", "deb")):
                    debit = abs(fval)
                elif any(k in col for k in ("credit", "crédit", " cr", "_cr", "cred")):
                    credit = abs(fval)
                elif any(k in col for k in ("solde", "sold", "balance", "net")):
                    if fval >= 0:
                        debit = fval
                    else:
                        credit = abs(fval)

        # Garder seulement les comptes qui commencent par un chiffre
        if compte and re.match(r"^\d", compte):
            cle = compte
            if cle not in balance:
                balance[cle] = {"compte": cle, "libelle": libelle, "debit": 0.0, "credit": 0.0}
            elif not balance[cle]["libelle"] and libelle:
                balance[cle]["libelle"] = libelle
            balance[cle]["debit"] += debit
            balance[cle]["credit"] += credit

    for b in balance.values():
        b["solde"] = round(b["debit"] - b["credit"], 2)

    return balance


def calculer_variations(
    conn,
    projet_id: str,
    fichier_n_id: str,
    fichier_n1_id: str | None,
    seuil_signification: float | None = None,
    seuil_pct_min: float = 20.0,
    seuil_abs_min: float = 10_000.0,
) -> list[dict]:
    """
    Compare la balance N et N-1 (optionnelle).
    Retourne les variations par compte, triées par delta absolu décroissant.
    """
    balance_n = _reconstruire_balance(conn, projet_id, fichier_n_id)
    balance_n1 = _reconstruire_balance(conn, projet_id, fichier_n1_id) if fichier_n1_id else {}

    all_comptes = sorted(set(balance_n) | set(balance_n1))
    variations: list[dict] = []

    for compte in all_comptes:
        row_n = balance_n.get(compte, {"libelle": "", "solde": 0.0, "debit": 0.0, "credit": 0.0})
        row_n1 = balance_n1.get(compte, {"libelle": "", "solde": 0.0, "debit": 0.0, "credit": 0.0})

        libelle = row_n.get("libelle") or row_n1.get("libelle", "")
        solde_n = row_n.get("solde", 0.0) or 0.0
        solde_n1 = row_n1.get("solde", 0.0) or 0.0
        delta = round(solde_n - solde_n1, 2)

        if solde_n1 != 0:
            delta_pct = round((delta / abs(solde_n1)) * 100.0, 2)
        elif solde_n != 0:
            delta_pct = 100.0
        else:
            delta_pct = 0.0

        # Variation significative : au-dessus du seuil absolu OU au-dessus du seuil relatif
        significative = False
        if seuil_signification is not None and abs(delta) >= seuil_signification:
            significative = True
        elif abs(delta) >= seuil_abs_min and abs(delta_pct) >= seuil_pct_min:
            significative = True

        # Ignorer les lignes entièrement à zéro
        if solde_n == 0.0 and solde_n1 == 0.0:
            continue

        variations.append({
            "compte": compte,
            "libelle": libelle,
            "solde_n": solde_n,
            "solde_n1": solde_n1,
            "delta": delta,
            "delta_pct": delta_pct,
            "significative": significative,
        })

    # Trier par delta absolu décroissant
    variations.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return variations


def calculer_agregats(conn, projet_id: str, fichier_n_id: str) -> dict[str, float]:
    """
    Calcule les agrégats principaux (total bilan, CA, résultat net, etc.)
    depuis la balance N. Purement déterministe.
    """
    balance = _reconstruire_balance(conn, projet_id, fichier_n_id)

    total_debit = 0.0
    total_credit = 0.0
    ca = 0.0
    charges_tot = 0.0
    produits_tot = 0.0
    actif_net = 0.0  # comptes de bilan côté débit net

    for compte, b in balance.items():
        d = b.get("debit", 0.0) or 0.0
        c = b.get("credit", 0.0) or 0.0
        s = b.get("solde", 0.0) or 0.0
        total_debit += d
        total_credit += c

        if any(compte.startswith(p) for p in PREFIXE_CA):
            ca += c

        if compte.startswith("6"):
            charges_tot += d

        if compte.startswith("7"):
            produits_tot += c

        if compte[0] in "12345" and s > 0:
            actif_net += s

    total_bilan = max(total_debit, total_credit)
    resultat_net = round(produits_tot - charges_tot, 2)

    return {
        "total_bilan": round(total_bilan, 2),
        "chiffre_affaires": round(ca, 2),
        "resultat_net": resultat_net,
        "total_actif": round(actif_net, 2),
        "charges_totales": round(charges_tot, 2),
        "produits_totaux": round(produits_tot, 2),
    }

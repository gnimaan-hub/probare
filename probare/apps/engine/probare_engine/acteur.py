"""Identité de l'auteur des actions — piste d'audit (ISA 230).

La piste d'audit dit ce qui a été fait et quand ; sans le nom de l'auteur elle
ne dit pas QUI, et une documentation d'audit qui n'identifie pas la personne
ayant exécuté le travail ne satisfait pas ISA 230.

Le nom vient de la fiche Cabinet (« Responsable signataire »), saisie dans la
page Configuration et conservée sur le poste. Le renderer le transmet à chaque
requête via l'en-tête « X-Probare-Acteur ».

Il ne s'agit PAS d'une authentification : le poste est mono-utilisateur et le
moteur n'écoute que sur 127.0.0.1 derrière un jeton partagé. C'est une
attribution — elle documente qui a mené la diligence, elle ne contrôle pas
l'accès. Un acteur usurpé n'ouvre aucun droit qu'il n'avait pas déjà.

Le nom circule par `ContextVar` plutôt qu'en paramètre : `db.log()` est appelé
depuis des centaines de points (routes, moteur de contrôles, exports) et les
faire tous transiter un argument supplémentaire multiplierait les occasions
d'oublier — un oubli produirait une ligne de journal anonyme, exactement ce
qu'on cherche à supprimer. Le contexte est propagé jusqu'aux routes
synchrones : Starlette exécute celles-ci via `anyio.to_thread.run_sync`, qui
recopie le contexte courant dans le thread de travail.
"""
from __future__ import annotations

from contextvars import ContextVar

# En-tête portant le nom de l'auteur, posé par le renderer sur chaque requête.
ENTETE_ACTEUR = "x-probare-acteur"

# Longueur maximale retenue : un nom de signataire, pas un texte libre.
_LONGUEUR_MAX = 120

_acteur: ContextVar[str | None] = ContextVar("probare_acteur", default=None)


def normaliser(nom: str | None) -> str | None:
    """Nettoie un nom d'acteur. Rend None si rien d'exploitable.

    Les caractères de contrôle sont retirés : le nom est réécrit tel quel dans
    le journal, et une ligne de journal ne doit pas pouvoir être maquillée par
    un retour chariot ou un caractère nul.
    """
    if not nom:
        return None
    propre = "".join(c for c in nom if c.isprintable()).strip()
    if not propre:
        return None
    return propre[:_LONGUEUR_MAX]


def definir_acteur(nom: str | None):
    """Fixe l'acteur du contexte courant. Rend le jeton de réinitialisation."""
    return _acteur.set(normaliser(nom))


def reinitialiser_acteur(token) -> None:
    """Restaure l'acteur précédent (jeton rendu par `definir_acteur`)."""
    _acteur.reset(token)


def acteur_courant() -> str | None:
    """Nom de l'auteur de l'action en cours, ou None hors requête HTTP."""
    return _acteur.get()

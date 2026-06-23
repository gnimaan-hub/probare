"""Abstraction LLMClient — l'implémentation concrète est derrière cette interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Interface unique pour tous les LLM. Ne jamais appeler directement un SDK."""

    @abstractmethod
    def mapper_colonnes(
        self,
        colonnes: list[str],
        exemples: dict[str, list[str]],
    ) -> dict:
        """Propose un mapping colonnes → champs audit. Sortie structurée JSON."""
        ...

    @abstractmethod
    def interpreter_exception(
        self,
        exception: dict,
        donnees_sources: list[dict],
        contexte_projet: dict,
    ) -> dict:
        """Explique une exception en langage clair. Ne recalcule rien. Sortie JSON."""
        ...

    @abstractmethod
    def rediger_feuille_travail(
        self,
        cycle: str,
        resultats: list[dict],
        exceptions: list[dict],
        contexte_projet: dict,
    ) -> dict:
        """Rédige une feuille de travail à partir de résultats calculés. Sortie JSON."""
        ...

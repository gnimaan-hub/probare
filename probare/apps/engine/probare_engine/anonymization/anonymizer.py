"""Anonymisation des identifiants nominatifs avant envoi au LLM."""
from __future__ import annotations
import re
import uuid


class Anonymizer:
    """Table de correspondance locale token ↔ valeur réelle.
    Jamais sérialisée ni envoyée à l'API.
    """

    def __init__(self):
        self._token_to_real: dict[str, str] = {}
        self._real_to_token: dict[str, str] = {}

    def _make_token(self, value: str) -> str:
        token = f"[ENTITE_{uuid.uuid4().hex[:8].upper()}]"
        self._token_to_real[token] = value
        self._real_to_token[value] = token
        return token

    def pseudonymiser(self, text: str, entites: list[str]) -> str:
        """Remplace chaque entité par son token dans le texte."""
        result = text
        for entite in sorted(entites, key=len, reverse=True):
            if not entite.strip():
                continue
            if entite not in self._real_to_token:
                self._make_token(entite)
            token = self._real_to_token[entite]
            result = re.sub(re.escape(entite), token, result, flags=re.IGNORECASE)
        return result

    def re_identifier(self, text: str) -> str:
        """Réidentifie les tokens dans la réponse du LLM."""
        result = text
        for token, real in self._token_to_real.items():
            result = result.replace(token, real)
        return result

    def pseudonymiser_dict(self, data: dict, champs_sensibles: list[str],
                           entites: list[str]) -> dict:
        """Pseudonymise les champs sensibles d'un dict."""
        result = dict(data)
        for champ in champs_sensibles:
            if champ in result and result[champ]:
                result[champ] = self.pseudonymiser(str(result[champ]), entites)
        return result

    def re_identifier_dict(self, data: dict, champs: list[str]) -> dict:
        result = dict(data)
        for champ in champs:
            if champ in result and result[champ]:
                result[champ] = self.re_identifier(str(result[champ]))
        return result

    @property
    def nb_entites(self) -> int:
        return len(self._real_to_token)

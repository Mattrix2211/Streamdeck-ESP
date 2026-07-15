"""Client Home Assistant minimal : lecture d'etat et appel de service via
l'API REST (pas de websocket - un polling simple suffit pour rafraichir
quelques widgets toutes les quelques secondes, voir ha_poller.py).

Utilise pour :
- les emplacements de type widget ("barre"/"texte") qui affichent l'etat
  en direct d'une entite Home Assistant (temperature, volume, etc.)
- le type d'action "home_assistant" (un bouton qui appelle un service HA,
  ex: basculer une lumiere/prise/scene)
"""

from __future__ import annotations

import requests


class HomeAssistantClient:
    def __init__(self, base_url: str, token: str, timeout: float = 5.0):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_state(self, entity_id: str) -> dict | None:
        if not self.configured or not entity_id:
            return None
        url = f"{self.base_url}/api/states/{entity_id}"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict | None = None,
    ) -> None:
        if not self.configured:
            raise RuntimeError("Home Assistant n'est pas configure (url/token manquants)")
        url = f"{self.base_url}/api/services/{domain}/{service}"
        payload = dict(data or {})
        if entity_id:
            payload.setdefault("entity_id", entity_id)
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()


def format_widget_value(state: dict, slot_type: str) -> str:
    """Convertit un etat HA en texte a pousser vers l'ecran.

    'barre' -> pourcentage entier 0-100 (l'entite doit avoir un etat
    numerique, ex: un capteur de volume/luminosite/batterie).
    'texte' -> valeur brute + unite si connue (ex: '21.5°C')."""
    raw = state.get("state", "")
    if slot_type == "barre":
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return "0"
        value = max(0, min(100, round(value)))
        return str(int(value))
    unit = (state.get("attributes") or {}).get("unit_of_measurement", "")
    return f"{raw}{unit}" if unit else str(raw)

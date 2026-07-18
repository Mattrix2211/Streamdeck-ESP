"""Client Home Assistant minimal : lecture d'etat et appel de service via
l'API REST (pas de websocket - un polling simple suffit pour rafraichir
quelques widgets toutes les quelques secondes, voir ha_poller.py).

Utilise pour :
- les emplacements de type widget ("barre"/"texte") qui affichent l'etat
  en direct d'une entite Home Assistant (temperature, volume, etc.)
- le type d'action "home_assistant" (un bouton qui appelle un service HA,
  ex: basculer une lumiere/prise/scene)
- le picker d'entites de la popup d'emplacement (list_entities), pour
  choisir une entite dans une liste recherchable plutot que de taper son
  entity_id a la main.
"""

from __future__ import annotations

import requests

# Services HA courants par domaine, pour le menu deroulant du picker
# d'action "home_assistant" - pas une introspection complete de l'API HA
# (qui exposerait des centaines de services), juste les plus utiles pour
# un bouton de Stream Deck. "toggle" en tete quand disponible (le plus
# frequent pour un bouton).
COMMON_SERVICES: dict[str, list[str]] = {
    "light": ["toggle", "turn_on", "turn_off"],
    "switch": ["toggle", "turn_on", "turn_off"],
    "fan": ["toggle", "turn_on", "turn_off"],
    "input_boolean": ["toggle", "turn_on", "turn_off"],
    "cover": ["toggle", "open_cover", "close_cover", "stop_cover"],
    "lock": ["lock", "unlock"],
    "climate": ["turn_on", "turn_off", "set_temperature"],
    "media_player": [
        "media_play_pause", "media_play", "media_pause", "media_stop",
        "media_next_track", "media_previous_track", "volume_up", "volume_down", "volume_mute",
    ],
    "scene": ["turn_on"],
    "script": ["turn_on"],
    "automation": ["trigger", "turn_on", "turn_off"],
    "vacuum": ["start", "pause", "stop", "return_to_base"],
    "alarm_control_panel": ["alarm_arm_away", "alarm_arm_home", "alarm_disarm"],
    "update": ["install", "skip", "clear_skipped"],
}
DEFAULT_SERVICES = ["turn_on", "turn_off", "toggle"]


def common_services(domain: str) -> list[str]:
    return COMMON_SERVICES.get(domain, DEFAULT_SERVICES)


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

    def list_entities(self) -> list[dict]:
        """Toutes les entites de l'installation HA, pour le picker
        recherchable (popup d'emplacement) - evite d'avoir a connaitre/
        taper un entity_id a la main."""
        if not self.configured:
            return []
        url = f"{self.base_url}/api/states"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        entities = []
        for item in resp.json():
            entity_id = item.get("entity_id", "")
            domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
            name = (item.get("attributes") or {}).get("friendly_name") or entity_id
            entities.append({
                "entity_id": entity_id,
                "name": name,
                "domain": domain,
                "state": item.get("state", ""),
            })
        entities.sort(key=lambda e: e["name"].lower())
        return entities

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

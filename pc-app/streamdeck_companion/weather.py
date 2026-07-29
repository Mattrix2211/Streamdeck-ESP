"""Carte meteo (widget dedie, distinct des emplacements generiques) -
lit une entite `weather.*` Home Assistant et en deduit une icone + un
"style d'animation" pour l'ecran (voir firmware/weather_card.yaml, qui
affiche/anime en consequence). La correspondance condition -> (icone,
style) vit ici plutot que dans le lambda firmware pour rester facile a
etendre/corriger sans reflasher pour le mapping lui-meme (seul le
firmware a besoin d'un reflash si un NOUVEAU style d'animation apparait).

Conditions standard Home Assistant (`weather.Weather.condition`) :
clear-night, cloudy, exceptional, fog, hail, lightning, lightning-rainy,
partlycloudy, pouring, rainy, snowy, snowy-rainy, sunny, windy,
windy-variant.
"""

from __future__ import annotations

from . import icons

# Styles d'animation geres cote firmware (voir weather_card.yaml) - un
# style regroupe plusieurs conditions proches visuellement, pour rester
# a un nombre de familles d'animation gerable (chacune est un pool
# d'objets LVGL pre-declares, pas de creation dynamique possible).
_CONDITION_MAP: dict[str, tuple[str, str]] = {
    "sunny": ("wb_sunny", "soleil"),
    "clear-night": ("nightlight_round", "nuit"),
    "partlycloudy": ("wb_cloudy", "nuage"),
    "cloudy": ("cloud", "nuage"),
    "fog": ("cloud_off", "nuage"),
    "windy": ("air", "aucune"),
    "windy-variant": ("air", "aucune"),
    "rainy": ("water_drop", "pluie"),
    "pouring": ("water_drop", "pluie"),
    "hail": ("grain", "pluie"),
    "lightning": ("thunderstorm", "pluie"),
    "lightning-rainy": ("thunderstorm", "pluie"),
    "snowy": ("ac_unit", "neige"),
    "snowy-rainy": ("ac_unit", "neige"),
    "exceptional": ("warning", "aucune"),
}
_DEFAULT_ICON, _DEFAULT_STYLE = "wb_cloudy", "aucune"


def condition_icon_char(condition: str) -> str:
    """Glyphe (voir icons.py) pour une condition meteo HA - case vide sur
    l'ecran si la condition est inconnue plutot qu'une erreur (une future
    version de HA pourrait ajouter une condition non repertoriee ici)."""
    icon_key, _ = _CONDITION_MAP.get(condition, (_DEFAULT_ICON, _DEFAULT_STYLE))
    return icons.icon_char(icon_key)


def condition_animation_style(condition: str) -> str:
    """Style d'animation (voir firmware/weather_card.yaml) pour une
    condition meteo HA - 'aucune' (icone statique) si inconnue."""
    _, style = _CONDITION_MAP.get(condition, (_DEFAULT_ICON, _DEFAULT_STYLE))
    return style


def format_temperature(state: dict) -> str:
    """'21.5°C' a partir de l'etat brut d'une entite weather.* - la
    temperature est un ATTRIBUT (pas l'etat lui-meme, qui est la
    condition textuelle 'sunny'/'rainy'/...), contrairement a un simple
    capteur numerique."""
    attrs = state.get("attributes") or {}
    temp = attrs.get("temperature")
    if temp is None:
        return ""
    unit = attrs.get("temperature_unit", "°C")
    try:
        return f"{float(temp):g}{unit}"
    except (TypeError, ValueError):
        return f"{temp}{unit}"


def read_weather(client, entity_id: str) -> dict | None:
    """{icon_char, animation_style, temperature} pour `entity_id`, ou None
    si l'entite est introuvable/non configuree - voir ha_poller.py, qui
    pousse ces 3 valeurs vers l'ecran (Meteo - icone/animation/temperature)."""
    if not entity_id:
        return None
    state = client.get_state(entity_id)
    if state is None:
        return None
    condition = state.get("state", "")
    return {
        "icon_char": condition_icon_char(condition),
        "animation_style": condition_animation_style(condition),
        "temperature": format_temperature(state),
    }

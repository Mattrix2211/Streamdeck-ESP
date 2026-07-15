"""Catalogue d'icones pour les emplacements de l'ecran.

Chaque icone est un caractere Material Icons (police "gfonts://Material
Icons" embarquee dans firmware/package.yaml, avec un `glyphs:` limite a
exactement ce jeu). Les points de code viennent du fichier officiel
MaterialIcons-Regular.codepoints - ne pas en ajouter un nouveau ici sans
l'ajouter aussi au `glyphs:` du firmware, sinon il s'affichera comme une
case vide sur l'ecran.
"""

from __future__ import annotations

ICONS: dict[str, int] = {
    "play_arrow": 0xE037,
    "pause": 0xE034,
    "stop": 0xE047,
    "skip_next": 0xE044,
    "skip_previous": 0xE045,
    "volume_up": 0xE050,
    "volume_down": 0xE04D,
    "volume_off": 0xE04F,
    "mic": 0xE029,
    "home": 0xE88A,
    "lightbulb_outline": 0xE90F,
    "wb_sunny": 0xE430,
    "ac_unit": 0xEB3B,
    "thermostat": 0xF076,
    "power_settings_new": 0xE8AC,
    "settings": 0xE8B8,
    "wifi": 0xE63E,
    "lock": 0xE897,
    "tv": 0xE333,
    "notifications": 0xE7F4,
    "star": 0xE838,
    "favorite": 0xE87D,
    "bluetooth": 0xE1A7,
}

# Libelles humains affiches dans le selecteur d'icone de l'appli PC.
ICON_LABELS: dict[str, str] = {
    "play_arrow": "Lecture",
    "pause": "Pause",
    "stop": "Stop",
    "skip_next": "Suivant",
    "skip_previous": "Precedent",
    "volume_up": "Volume +",
    "volume_down": "Volume -",
    "volume_off": "Muet",
    "mic": "Micro",
    "home": "Maison",
    "lightbulb_outline": "Lumiere",
    "wb_sunny": "Meteo / soleil",
    "ac_unit": "Froid / clim",
    "thermostat": "Temperature",
    "power_settings_new": "Marche/arret",
    "settings": "Parametres",
    "wifi": "Wifi",
    "lock": "Verrou",
    "tv": "TV",
    "notifications": "Notification",
    "star": "Favori",
    "favorite": "Coeur",
    "bluetooth": "Bluetooth",
}


def icon_char(icon_key: str) -> str:
    """Caractere UTF-8 a pousser vers l'entite 'Slot N - icone' du firmware."""
    codepoint = ICONS.get(icon_key)
    return chr(codepoint) if codepoint is not None else ""


def icon_choices() -> list[dict[str, str]]:
    """Liste [{key, label, char}] pour le selecteur d'icone de l'appli PC."""
    return [
        {"key": key, "label": ICON_LABELS.get(key, key), "char": icon_char(key)}
        for key in ICONS
    ]

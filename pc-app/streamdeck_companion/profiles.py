"""Modele des profils : chaque profil a sa propre grille de 16
emplacements + 3 encodeurs, et un declencheur optionnel (nom de
processus). L'ecran bascule automatiquement sur le profil dont le
declencheur correspond a l'application au premier plan sur le PC (voir
profile_watcher.py) - le comportement "profils par application" d'un
Stream Deck du commerce. Le premier profil sans declencheur ("Defaut")
sert de repli quand aucun declencheur ne correspond.

Module partage par dashboard.py (edition web) et device_client.py
(resolution des actions + push vers l'ecran) - independant des deux pour
eviter tout import circulaire.
"""

from __future__ import annotations

SLOT_COUNT = 16
DEFAULT_PROFILE_NAME = "Defaut"

# Grille invisible de cases carrees (voir firmware/slot_grid.yaml et
# scripts/gen_slot_grid.py - CES 3 endroits doivent rester coherents si la
# geometrie change un jour) : un emplacement occupe 1 ou plusieurs cases
# ("colspan"/"rowspan"), facon "sections" de Home Assistant, au lieu d'une
# grille fixe 4x4 a une seule taille de tuile.
GRID_COLS = 9
GRID_ROWS = 4


def default_grid(i: int) -> dict:
    """Disposition par defaut (avant toute personnalisation au glisser-
    depose/redimensionnement) : range dans l'ordre de lecture, 1x1 case."""
    return {"col": i % GRID_COLS, "row": i // GRID_COLS, "colspan": 1, "rowspan": 1}


def default_slot(i: int) -> dict:
    return {
        "label": f"Slot {i + 1}",
        "icon": "",
        "type": "bouton",
        "visible": i < 12,
        "action": {"type": "none", "target": ""},
        "ha_entity": "",
        "show_light_color": False,
        "grid": default_grid(i),
    }


def default_slots() -> list[dict]:
    return [default_slot(i) for i in range(SLOT_COUNT)]


def default_encoders() -> list[dict]:
    empty = {"type": "none", "target": ""}
    return [{"clockwise": dict(empty), "anticlockwise": dict(empty), "press": dict(empty)} for _ in range(3)]


def default_profile(name: str = DEFAULT_PROFILE_NAME, trigger: dict | None = None) -> dict:
    return {"name": name, "trigger": trigger, "slots": default_slots(), "encoders": default_encoders()}


def migrate_profiles(config: dict) -> list[dict]:
    """Retourne config['profiles'], migrant l'ancien format (slots/encoders
    a la racine, avant l'introduction des profils) vers un profil "Defaut"
    unique si besoin - transparent pour les configs existantes."""
    profiles = config.get("profiles")
    if profiles:
        return profiles
    profile = default_profile()
    if "slots" in config:
        profile["slots"] = config["slots"]
    if "encoders" in config:
        profile["encoders"] = config["encoders"]
    return [profile]


def find_profile(profiles: list[dict], name: str | None) -> dict | None:
    if name is None:
        return None
    return next((p for p in profiles if p.get("name") == name), None)


def match_profile(profiles: list[dict], process_name: str | None) -> dict:
    """Le premier profil (dans l'ordre de la liste) dont le declencheur
    correspond au processus au premier plan sur le PC, sinon le premier
    profil sans declencheur ("Defaut"). `profiles` ne devrait jamais etre
    vide en pratique (migrate_profiles en garantit au moins un), mais on
    retombe sur un profil par defaut "en memoire" par securite."""
    if process_name:
        needle = process_name.lower()
        for profile in profiles:
            trigger = profile.get("trigger")
            if trigger and (trigger.get("process") or "").lower() == needle:
                return profile
    for profile in profiles:
        if not profile.get("trigger"):
            return profile
    return profiles[0] if profiles else default_profile()

"""Surveille l'application au premier plan sur le PC et bascule
automatiquement l'ecran sur le profil dont le declencheur correspond (voir
profiles.py) - le comportement "profils par application" d'un Stream Deck
du commerce : la grille change toute seule selon l'appli active, sans
intervention. Tourne dans son propre thread (voir tray.py), a l'image de
ha_poller.py.

Windows uniquement (necessite pywin32 + psutil pour identifier la fenetre
au premier plan) - no-op silencieux sur les autres systemes, la bascule
manuelle (bouton "Forcer ce profil") reste utilisable partout.
"""

from __future__ import annotations

import logging
import threading

from . import profiles as profile_utils
from .actions import SYSTEM
from .device_client import DeviceClient

LOG = logging.getLogger("streamdeck_profile_watcher")

POLL_INTERVAL = 1.5


def foreground_process_name() -> str | None:
    """Nom (minuscules, ex 'obs64.exe') du processus de la fenetre au
    premier plan sur le PC, ou None si indisponible/non-Windows."""
    if SYSTEM != "Windows":
        return None
    import psutil
    import win32gui
    import win32process

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid:
        return None
    try:
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    if SYSTEM != "Windows":
        LOG.info("Bascule automatique de profil indisponible sur cette plateforme (Windows uniquement)")
        return
    while not stop_event.is_set():
        try:
            if device_client.manual_override is None:
                process_name = foreground_process_name()
                matched = profile_utils.match_profile(device_client.profiles, process_name)
                device_client.schedule_set_active_profile(matched.get("name"))
        except Exception:
            LOG.exception("Echec de la verification du profil actif")
        stop_event.wait(POLL_INTERVAL)

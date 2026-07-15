"""Lance l'appli compagnon Stream Deck comme une icone de barre des taches
Windows (system tray), sans fenetre de terminal visible : c'est la facon
recommandee de faire tourner ce programme au quotidien.

Deux choses tournent en fond :
  - device_client.DeviceClient : connexion persistante a l'ecran (thread
    dedie avec sa propre boucle asyncio), execute les actions configurees.
  - dashboard.py : page web de configuration (autre thread), lit/ecrit
    dashboard_config.yaml et demande a DeviceClient de pousser les
    changements vers l'ecran.

Lancer :
    pythonw -m streamdeck_companion.tray      (pythonw = pas de console)

Pour un demarrage automatique avec Windows, voir install_startup.ps1 et le
README de ce dossier.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from . import dashboard
from . import ha_poller
from .device_client import DEFAULT_CONFIG_PATH, DeviceClient, load_config

LOG = logging.getLogger("streamdeck_tray")

# Couleurs du design system (navy / signal)
NAVY = (11, 25, 41, 255)
SIGNAL = (0, 180, 216, 255)


def make_icon_image() -> Image.Image:
    """Genere l'icone directement en memoire (pas de fichier .ico a fournir) :
    un cercle signal sur fond navy, aux couleurs du design system."""
    size = 64
    img = Image.new("RGBA", (size, size), NAVY)
    draw = ImageDraw.Draw(img)
    margin = 14
    draw.ellipse((margin, margin, size - margin, size - margin), fill=SIGNAL)
    return img


def build_menu(config: dict) -> pystray.Menu:
    ha_conf = config.get("home_assistant") or {}
    ha_url = ha_conf.get("url") or "http://homeassistant.local:8123"

    def open_dashboard(_icon, _item):
        webbrowser.open(f"http://127.0.0.1:{dashboard.DASHBOARD_PORT}")

    def open_home_assistant(_icon, _item):
        webbrowser.open(ha_url)

    def quit_app(icon, _item):
        icon.stop()
        os._exit(0)  # noqa: SLF001 - threads daemon, on arrete tout le process direct

    return pystray.Menu(
        pystray.MenuItem("Stream Deck", None, enabled=False),
        pystray.MenuItem("Configurer le Stream Deck", open_dashboard, default=True),
        pystray.MenuItem("Ouvrir Home Assistant", open_home_assistant),
        pystray.MenuItem("Quitter", quit_app),
    )


def run_device_client(client: DeviceClient) -> None:
    """Cible du thread de connexion : sa propre boucle asyncio, tourne en
    continu (reconnecte si l'ecran redemarre ou change d'IP apres correction
    dans la page de config, puisque asyncio.run() relance run_forever a
    chaque erreur non geree via la boucle exterieure ci-dessous)."""
    while True:
        try:
            asyncio.run(client.run_forever())
        except Exception:
            LOG.exception("Connexion au Stream Deck perdue, nouvelle tentative dans 10s")
        client.connected = False
        client.loop = None
        time.sleep(10)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        LOG.error(
            "Fichier de config introuvable: %s (copiez dashboard_config.yaml.example)",
            config_path,
        )
        sys.exit(1)

    device_client = DeviceClient(config_path)
    client_thread = threading.Thread(target=run_device_client, args=(device_client,), daemon=True)
    client_thread.start()

    dashboard_thread = threading.Thread(
        target=dashboard.run_server, args=(config_path, device_client), daemon=True
    )
    dashboard_thread.start()

    ha_stop_event = threading.Event()
    ha_thread = threading.Thread(
        target=ha_poller.run_forever, args=(device_client, ha_stop_event), daemon=True
    )
    ha_thread.start()

    config = load_config(config_path)
    icon = pystray.Icon("streamdeck", make_icon_image(), "Stream Deck", menu=build_menu(config))
    icon.run()


if __name__ == "__main__":
    main()

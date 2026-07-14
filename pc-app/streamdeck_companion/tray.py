"""Lance l'appli compagnon Stream Deck comme une icone de barre des taches
Windows (system tray), sans fenetre de terminal visible : c'est la facon
recommandee de faire tourner ce programme au quotidien.

Le serveur receveur d'actions (receiver.py) tourne dans un thread en fond ;
l'icone affiche juste un menu (statut, ouvrir Home Assistant, quitter).

Lancer :
    pythonw -m streamdeck_companion.tray      (pythonw = pas de console)

Pour un demarrage automatique avec Windows, voir install_startup.ps1 et le
README de ce dossier.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from . import receiver

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
    ha_url = config.get("home_assistant_url") or "http://homeassistant.local:8123"
    port = config.get("port", 8765)

    def open_home_assistant(_icon, _item):
        webbrowser.open(ha_url)

    def open_screen_settings(_icon, _item):
        webbrowser.open(f"http://127.0.0.1:{port}/screen")

    def quit_app(icon, _item):
        icon.stop()
        os._exit(0)  # noqa: SLF001 - le serveur tourne dans un thread daemon, on arrete tout le process direct

    return pystray.Menu(
        pystray.MenuItem(f"Stream Deck - port {port}", None, enabled=False),
        pystray.MenuItem("Personnaliser l'ecran", open_screen_settings),
        pystray.MenuItem("Ouvrir Home Assistant", open_home_assistant),
        pystray.MenuItem("Quitter", quit_app),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else receiver.DEFAULT_CONFIG_PATH
    try:
        config = receiver.resolve_config(config_path)
    except ValueError as exc:
        LOG.error("%s (copiez receiver_config.yaml.example)", exc)
        sys.exit(1)

    server_thread = threading.Thread(target=receiver.run_server, args=(config, config_path), daemon=True)
    server_thread.start()

    icon = pystray.Icon("streamdeck", make_icon_image(), "Stream Deck", menu=build_menu(config))
    icon.run()


if __name__ == "__main__":
    main()

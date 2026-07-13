"""Appli compagnon PC : connecte le Stream Deck (API native ESPHome) aux
actions locales (raccourcis, media, lancement d'applis) et pousse un statut
texte a afficher sur l'ecran.

C'est le meme protocole que celui utilise par Home Assistant pour parler a
ce meme appareil : aucun serveur HTTP separe n'est necessaire.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml
from aioesphomeapi import APIClient, Event, EventInfo, TextInfo

from . import actions as action_runner

LOG = logging.getLogger("streamdeck_companion")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
STATUS_ENTITY_NAME = "Statut PC"


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Companion:
    def __init__(self, config: dict):
        conn = config["connection"]
        self.actions_by_entity: dict = config.get("actions", {})
        self.client = APIClient(
            conn["host"],
            conn.get("port", 6053),
            conn.get("password", ""),
            noise_psk=conn.get("api_encryption_key") or None,
        )
        self.key_to_entity_name: dict[int, str] = {}
        self.status_text_key: int | None = None

    async def connect(self) -> None:
        await self.client.connect(login=False)
        entities, _services = await self.client.list_entities_services()
        for ent in entities:
            if isinstance(ent, EventInfo) and ent.name in self.actions_by_entity:
                self.key_to_entity_name[ent.key] = ent.name
            elif isinstance(ent, TextInfo) and ent.name == STATUS_ENTITY_NAME:
                self.status_text_key = ent.key
        LOG.info(
            "Connecte a %s : %d entite(s) d'evenement mappee(s), statut=%s",
            self.client.address,
            len(self.key_to_entity_name),
            "ok" if self.status_text_key is not None else "absent",
        )

    def on_state(self, state) -> None:
        if not isinstance(state, Event):
            return
        entity_name = self.key_to_entity_name.get(state.key)
        if entity_name is None:
            return
        action = self.actions_by_entity.get(entity_name, {}).get(state.event_type)
        if action is None:
            LOG.debug("Pas d'action mappee pour %s / %s", entity_name, state.event_type)
            return
        try:
            action_runner.run(action)
        except Exception:
            LOG.exception("Echec de l'action %r pour %s/%s", action, entity_name, state.event_type)

    def push_status(self, text: str) -> None:
        if self.status_text_key is not None:
            self.client.text_command(self.status_text_key, text[:64])

    async def run_forever(self) -> None:
        await self.connect()
        self.client.subscribe_states(self.on_state)
        self.push_status("PC connecte")
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            self.push_status("PC hors ligne")
            await self.client.disconnect()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        LOG.error(
            "Fichier de config introuvable: %s (copiez config.yaml.example en config.yaml)",
            config_path,
        )
        sys.exit(1)
    config = load_config(config_path)
    try:
        asyncio.run(_run(config))
    except KeyboardInterrupt:
        pass


async def _run(config: dict) -> None:
    # Construit l'APIClient a l'interieur de la boucle asyncio active :
    # son constructeur echoue sinon avec "no running event loop".
    companion = Companion(config)
    await companion.run_forever()


if __name__ == "__main__":
    main()

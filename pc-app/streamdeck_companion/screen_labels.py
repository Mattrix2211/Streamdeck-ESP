"""Pousse les libelles des boutons d'action vers l'ecran, via une connexion
ponctuelle a l'API native ESPHome (pas de connexion permanente comme
l'ancienne appli compagnon - juste le temps d'envoyer les nouvelles valeurs).

Utilise par la page web "Personnaliser l'ecran" (voir receiver.py, routes
/screen et /screen/save), ouverte depuis le menu de l'icone de la barre des
taches (tray.py).
"""

from __future__ import annotations

import asyncio

from aioesphomeapi import APIClient, TextInfo

LABEL_ENTITY_NAMES = [
    "Action 1 - libelle",
    "Action 2 - libelle",
    "Action 3 - libelle",
    "Action 4 - libelle",
    "Action 5 - libelle",
    "Action 6 - libelle",
]


async def push_labels(host: str, port: int, api_key: str, labels: list[str]) -> None:
    """Connexion ponctuelle : se connecte, pousse chaque libelle, se
    deconnecte. Leve une exception aioesphomeapi si la connexion echoue -
    a l'appelant de l'afficher proprement (voir receiver.py)."""
    client = APIClient(host, port, "", noise_psk=api_key or None)
    await client.connect(login=False)
    try:
        entities, _services = await client.list_entities_services()
        name_to_key = {
            ent.name: ent.key for ent in entities if isinstance(ent, TextInfo) and ent.name in LABEL_ENTITY_NAMES
        }
        for name, value in zip(LABEL_ENTITY_NAMES, labels):
            key = name_to_key.get(name)
            if key is not None and value:
                client.text_command(key, value[:24])
        # text_command() ecrit sur le transport sans attendre confirmation -
        # laisse une marge pour que les 6 envois partent reellement avant de
        # fermer la connexion juste apres.
        await asyncio.sleep(0.3)
    finally:
        await client.disconnect()

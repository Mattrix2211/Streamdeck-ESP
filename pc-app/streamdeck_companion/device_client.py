"""Connexion persistante et directe au Stream Deck : ecoute les boutons et
encodeurs, execute les actions configurees localement (aucun code a ecrire,
tout se regle depuis la page de configuration - voir dashboard.py), et
pousse la config du profil actif (16 emplacements + forme) vers l'ecran en
reutilisant CETTE MEME connexion (pas de reconnexion separee a chaque
changement). Le profil actif change automatiquement selon l'application
au premier plan sur le PC (voir profile_watcher.py) ou manuellement
(voir schedule_force_profile/schedule_clear_override).
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import yaml
from aioesphomeapi import (
    APIClient,
    Event,
    EventInfo,
    NumberInfo,
    NumberState,
    SelectInfo,
    SwitchInfo,
    SwitchState,
    TextInfo,
)

from . import actions as action_runner
from . import color_mode as color_mode_module
from . import ha_client
from . import ha_popup as ha_popup_module
from . import profiles as profile_utils

LOG = logging.getLogger("streamdeck_client")

SLOT_COUNT = 16
SLOT_LABEL_NAMES = [f"Slot {i} - libelle" for i in range(1, SLOT_COUNT + 1)]
SLOT_VALUE_NAMES = [f"Slot {i} - valeur" for i in range(1, SLOT_COUNT + 1)]
SLOT_ICON_NAMES = [f"Slot {i} - icone" for i in range(1, SLOT_COUNT + 1)]
SLOT_COLOR_NAMES = [f"Slot {i} - couleur" for i in range(1, SLOT_COUNT + 1)]
SLOT_TYPE_NAMES = [f"Slot {i} - type" for i in range(1, SLOT_COUNT + 1)]
SLOT_VISIBLE_NAMES = [f"Slot {i} - visible" for i in range(1, SLOT_COUNT + 1)]

SHAPE_ENTITY_NAME = "Forme des boutons"
ACTION_EVENT_ENTITY = "Bouton d'action ecran"
ENCODER_EVENT_ENTITIES = [f"Encodeur {i} - evenement" for i in range(1, 4)]
STATUS_ENTITY_NAME = "Statut PC"
# Prefixe (base URL de l'appli PC) pour les vraies icones d'appli/jeu -
# voir icon_server.py (port dedie, separe du dashboard) et
# firmware/slot_icons.yaml (entites online_image).
PC_BASE_URL_ENTITY_NAME = "PC - URL locale"
ICON_SERVER_PORT = 8081

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "dashboard_config.yaml"


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(path: Path, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


class DeviceClient:
    """Une instance = une connexion persistante a l'ecran, vivant dans son
    propre thread/boucle asyncio (voir tray.py). La page de configuration
    (thread Flask separe) et le sondeur Home Assistant (voir ha_poller.py)
    communiquent avec elle via schedule_push()/schedule_push_values(), qui
    passent par asyncio.run_coroutine_threadsafe pour rester thread-safe."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.config: dict = {}
        self.config_mtime: float | None = None
        self.client: APIClient | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.key_to_entity_name: dict[int, str] = {}
        self.entity_keys: dict[str, int] = {}  # nom d'entite -> key
        self.connected = False
        self.profiles: list[dict] = []
        self.active_profile_name: str | None = None
        # Nom de profil force manuellement (voir schedule_force_profile) -
        # None = bascule automatique selon l'appli au premier plan.
        self.manual_override: str | None = None
        # Mode reglage couleur/chaleur/intensite (appui long sur un
        # emplacement lie a une ampoule) - voir color_mode.py.
        self.color_mode = color_mode_module.ColorModeController(self)
        # Popup tactile adaptee (tap sur un emplacement lie a une ampoule ou
        # un lecteur multimedia) - voir ha_popup.py.
        self.ha_popup = ha_popup_module.HaPopupController(self)
        # LVGL envoie un "click" (action_N) juste apres un "long press"
        # (hold_N) au relachement du doigt - sans ca, un appui long
        # declenche AUSSI l'action normale du bouton (ex: eteint la lumiere
        # en plus d'ouvrir le mode couleur). On ignore ce click fantome.
        self._pending_hold_slot: int | None = None
        self._pending_hold_time = 0.0

    def _load_config(self) -> None:
        self.config = load_config(self.config_path)
        self.config_mtime = self.config_path.stat().st_mtime if self.config_path.exists() else None
        self.profiles = profile_utils.migrate_profiles(self.config)

    def _active_profile(self) -> dict:
        return (
            profile_utils.find_profile(self.profiles, self.active_profile_name)
            or (self.profiles[0] if self.profiles else profile_utils.default_profile())
        )

    def active_profile(self) -> dict:
        """Accesseur public du profil actif, pour les modules externes qui
        doivent lire ses emplacements (ex: ha_poller.py) sans acceder a
        l'attribut prefixe _active_profile()."""
        return self._active_profile()

    def reload_config_if_changed(self) -> None:
        if not self.config_path.exists():
            return
        mtime = self.config_path.stat().st_mtime
        if mtime != self.config_mtime:
            self._load_config()
            LOG.info("Configuration rechargee depuis %s", self.config_path)

    async def connect(self) -> None:
        self._load_config()
        conn = self.config.get("connection", {})
        self.client = APIClient(
            conn.get("host", ""),
            conn.get("port", 6053),
            "",
            noise_psk=conn.get("api_key") or None,
        )
        await self.client.connect(login=False)
        entities, _services = await self.client.list_entities_services()
        tracked_text_select = (
            *SLOT_LABEL_NAMES, *SLOT_VALUE_NAMES, *SLOT_ICON_NAMES, *SLOT_COLOR_NAMES, *SLOT_TYPE_NAMES,
            SHAPE_ENTITY_NAME, STATUS_ENTITY_NAME, PC_BASE_URL_ENTITY_NAME, ha_popup_module.TITLE_TEXT_NAME,
        )
        # Switches ecrits par le PC uniquement (visibilite d'un panneau/
        # emplacement) - contrairement a POWER_SWITCH_NAME plus bas, jamais
        # relus depuis l'ecran.
        write_only_switches = (
            *SLOT_VISIBLE_NAMES, color_mode_module.SWITCH_NAME, ha_popup_module.ACTIVE_SWITCH_NAME,
        )
        for ent in entities:
            if isinstance(ent, EventInfo) and ent.name in (ACTION_EVENT_ENTITY, *ENCODER_EVENT_ENTITIES):
                self.key_to_entity_name[ent.key] = ent.name
            if isinstance(ent, (TextInfo, SelectInfo)) and ent.name in tracked_text_select:
                self.entity_keys[ent.name] = ent.key
            if isinstance(ent, SwitchInfo) and ent.name in write_only_switches:
                self.entity_keys[ent.name] = ent.key
            if isinstance(ent, SwitchInfo) and ent.name == ha_popup_module.POWER_SWITCH_NAME:
                self.entity_keys[ent.name] = ent.key
                # Sens PC -> ecran (etat initial a l'ouverture) ET ecran -> PC
                # (bascule au tactile, voir on_state ci-dessous).
                self.key_to_entity_name[ent.key] = ent.name
            if isinstance(ent, NumberInfo) and ent.name in (
                *color_mode_module.NUMBER_NAMES.values(), ha_popup_module.VALUE_NUMBER_NAME,
            ):
                self.entity_keys[ent.name] = ent.key
                # Sens PC -> ecran (number_command) ET ecran -> PC (glissement
                # tactile sur un slider, voir on_state ci-dessous).
                self.key_to_entity_name[ent.key] = ent.name
        self.connected = True
        LOG.info("Connecte a %s (%d bouton/encodeur mappes)", conn.get("host"), len(self.key_to_entity_name))
        status_key = self.entity_keys.get(STATUS_ENTITY_NAME)
        if status_key is not None:
            self.client.text_command(status_key, "PC en ligne")
        base_url_key = self.entity_keys.get(PC_BASE_URL_ENTITY_NAME)
        if base_url_key is not None:
            self.client.text_command(base_url_key, self._local_base_url(conn.get("host", "")))
        # Repousse la config du profil actif a chaque (re)connexion - sinon
        # un redemarrage de l'ecran perd tout (entites optimistes, pas de
        # restore_value) tant que l'utilisateur ne resauvegarde pas a la main.
        if self.profiles:
            try:
                self.push_config()
            except Exception:
                LOG.exception("Echec du push de config initial apres connexion")

    def _local_base_url(self, esp_host: str) -> str:
        """URL locale de cette appli (pour icon_server.py), telle que
        joignable DEPUIS l'ecran - determine l'IP de sortie du PC vers
        l'ecran plutot que de deviner parmi plusieurs cartes reseau."""
        import socket

        ip = "127.0.0.1"
        if esp_host:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect((esp_host, 1))
                ip = sock.getsockname()[0]
            except OSError:
                pass
            finally:
                sock.close()
        return f"http://{ip}:{ICON_SERVER_PORT}"

    def _resolve_action(self, entity_name: str, event_type: str) -> dict | None:
        """Resout l'action configuree dans le profil ACTIF (celui
        actuellement affiche sur l'ecran) - pas necessairement le premier
        profil : si OBS a le focus, un clic sur l'ecran declenche l'action
        du profil "OBS", pas celle du profil "Defaut"."""
        active = self._active_profile()
        if entity_name == ACTION_EVENT_ENTITY:
            try:
                idx = int(event_type.rsplit("_", 1)[1]) - 1  # "action_16" -> 15
            except (IndexError, ValueError):
                return None
            slots = active.get("slots", [])
            slot = slots[idx] if 0 <= idx < len(slots) else None
            return (slot or {}).get("action")
        if entity_name in ENCODER_EVENT_ENTITIES:
            enc_idx = ENCODER_EVENT_ENTITIES.index(entity_name)
            encoders = active.get("encoders", [])
            return encoders[enc_idx].get(event_type) if enc_idx < len(encoders) else None
        return None

    def on_state(self, state) -> None:
        entity_name = self.key_to_entity_name.get(state.key)
        if entity_name is None:
            return

        if isinstance(state, NumberState):
            axis = color_mode_module.NUMBER_NAME_TO_AXIS.get(entity_name)
            if axis is not None:
                self.color_mode.handle_touch(axis, state.state)
            elif entity_name == ha_popup_module.VALUE_NUMBER_NAME:
                self.ha_popup.handle_value(state.state)
            return

        if isinstance(state, SwitchState):
            if entity_name == ha_popup_module.POWER_SWITCH_NAME:
                self.ha_popup.handle_power(state.state)
            return

        if not isinstance(state, Event):
            return

        if entity_name == ACTION_EVENT_ENTITY:
            event_type = state.event_type
            if event_type == "close_color_mode":
                self.color_mode.exit()
                return
            if event_type == "close_ha_popup":
                self.ha_popup.close()
                return
            if event_type in ("popup_next", "popup_prev"):
                self.ha_popup.handle_track("next" if event_type == "popup_next" else "prev")
                return
            if event_type.startswith("hold_"):
                try:
                    idx = int(event_type.split("_", 1)[1]) - 1
                except ValueError:
                    return
                self._pending_hold_slot = idx
                self._pending_hold_time = time.monotonic()
                self.color_mode.enter(idx)
                return
            if event_type.startswith("barre_inc_") or event_type.startswith("barre_dec_"):
                self._adjust_barre(event_type)
                return
            if event_type.startswith("action_"):
                try:
                    idx = int(event_type.rsplit("_", 1)[1]) - 1
                except (IndexError, ValueError):
                    idx = None
                if idx is not None and idx == self._pending_hold_slot and time.monotonic() - self._pending_hold_time < 2.0:
                    self._pending_hold_slot = None
                    return

        if self.color_mode.slot is not None and entity_name in ENCODER_EVENT_ENTITIES:
            self.color_mode.handle_encoder(ENCODER_EVENT_ENTITIES.index(entity_name), state.event_type)
            return

        action = self._resolve_action(entity_name, state.event_type)
        if not action or action.get("type", "none") == "none":
            return
        try:
            if action.get("type") == "home_assistant":
                target = action.get("target") or {}
                # Un tap (pas un encodeur) sur un emplacement lie a un
                # lecteur multimedia ouvre la popup adaptee au lieu d'appeler
                # le service configure directement - voir ha_popup.py. Les
                # ampoules restent en tap = bascule directe (reglage fin sur
                # l'appui long, voir color_mode.py).
                if (
                    entity_name == ACTION_EVENT_ENTITY
                    and state.event_type.startswith("action_")
                    and target.get("domain") in ha_popup_module.SUPPORTED_DOMAINS
                ):
                    idx = int(state.event_type.rsplit("_", 1)[1]) - 1
                    self.ha_popup.open(idx, action)
                else:
                    self._run_home_assistant_action(action)
            else:
                action_runner.run(action)
        except Exception:
            LOG.exception("Echec de l'action pour %s/%s : %r", entity_name, state.event_type, action)

    def _adjust_barre(self, event_type: str) -> None:
        """Tactile gauche/droite sur un widget barre (voir slot_widgets.yaml)
        - ajuste directement l'entite Home Assistant liee, pas besoin de
        passer par l'appli PC."""
        if event_type.startswith("barre_inc_"):
            direction, idx_str = 1, event_type[len("barre_inc_"):]
        else:
            direction, idx_str = -1, event_type[len("barre_dec_"):]
        try:
            idx = int(idx_str) - 1
        except ValueError:
            return
        active = self._active_profile()
        slots = active.get("slots", [])
        if not (0 <= idx < len(slots)):
            return
        slot = slots[idx] or {}
        if slot.get("type") != "barre":
            return
        entity_id = slot.get("ha_entity")
        if not entity_id:
            return
        ha_conf = self.config.get("home_assistant") or {}
        client = ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
        try:
            ha_client.adjust_entity_percent(client, entity_id, direction)
        except Exception:
            LOG.exception("Echec de l'ajustement tactile pour %s", entity_id)

    def _run_home_assistant_action(self, action: dict) -> None:
        ha_conf = self.config.get("home_assistant") or {}
        client = ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
        target = action.get("target") or {}
        domain = target.get("domain")
        service = target.get("service")
        if not domain or not service:
            raise ValueError("Action Home Assistant incomplete (domain/service manquant)")
        client.call_service(domain, service, entity_id=target.get("entity_id"), data=target.get("data") or {})

    def push_config(self) -> None:
        """Pousse la config des 16 emplacements (libelle/icone/type/
        visibilite) du profil ACTIF et la forme vers l'ecran, via la
        connexion deja ouverte. Doit etre appelee depuis le thread/la
        boucle de cette instance (voir schedule_push pour un appel
        cross-thread)."""
        if self.client is None or not self.connected:
            raise RuntimeError("Pas encore connecte a l'ecran")
        slots = self._active_profile().get("slots", [])
        names = zip(SLOT_LABEL_NAMES, SLOT_ICON_NAMES, SLOT_TYPE_NAMES, SLOT_VISIBLE_NAMES)
        for i, (label_name, icon_name, type_name, visible_name) in enumerate(names):
            slot = slots[i] if i < len(slots) else None
            label_key = self.entity_keys.get(label_name)
            if label_key is not None:
                self.client.text_command(label_key, ((slot or {}).get("label") or f"Slot {i + 1}")[:24])
            icon_key = self.entity_keys.get(icon_name)
            if icon_key is not None:
                self.client.text_command(icon_key, (slot or {}).get("icon_char") or "")
            type_key = self.entity_keys.get(type_name)
            if type_key is not None:
                self.client.select_command(type_key, (slot or {}).get("type") or "bouton")
            visible_key = self.entity_keys.get(visible_name)
            if visible_key is not None:
                self.client.switch_command(visible_key, bool((slot or {}).get("visible", i < 12)))
        shape = self.config.get("shape")
        shape_key = self.entity_keys.get(SHAPE_ENTITY_NAME)
        if shape and shape_key is not None:
            self.client.select_command(shape_key, shape)

    def push_slot_values(self, values: dict[int, str]) -> None:
        """Pousse uniquement les valeurs (widgets barre/texte) pour les
        index d'emplacement donnes (0-based). Appelee periodiquement par
        ha_poller.py - separee de push_config() pour ne pas re-pousser
        libelle/icone/type/visibilite a chaque rafraichissement."""
        if self.client is None or not self.connected:
            return
        for idx, value in values.items():
            if not (0 <= idx < SLOT_COUNT):
                continue
            key = self.entity_keys.get(SLOT_VALUE_NAMES[idx])
            if key is not None:
                self.client.text_command(key, str(value)[:24])

    def push_slot_colors(self, colors: dict[int, str]) -> None:
        """Pousse la couleur de fond (widgets/boutons lies a une ampoule,
        voir ha_poller.py::poll_once) pour les index d'emplacement donnes
        (0-based) - chaine vide pour revenir a la couleur par defaut du
        firmware (ampoule eteinte)."""
        if self.client is None or not self.connected:
            return
        for idx, color in colors.items():
            if not (0 <= idx < SLOT_COUNT):
                continue
            key = self.entity_keys.get(SLOT_COLOR_NAMES[idx])
            if key is not None:
                self.client.text_command(key, color)

    def schedule_push(self, timeout: float = 5.0) -> None:
        """Appelable depuis N'IMPORTE QUEL thread (ex: la page de config
        Flask) : programme push_config() sur la boucle asyncio de ce
        client et attend le resultat. Leve l'exception d'origine si ca
        echoue (connexion non etablie, etc.)."""
        self._run_threadsafe(self.push_config, timeout)

    def schedule_push_values(self, values: dict[int, str], timeout: float = 5.0) -> None:
        self._run_threadsafe(lambda: self.push_slot_values(values), timeout)

    def schedule_push_slot_colors(self, colors: dict[int, str], timeout: float = 5.0) -> None:
        self._run_threadsafe(lambda: self.push_slot_colors(colors), timeout)

    def set_active_profile(self, name: str) -> None:
        """Change le profil affiche/actif et pousse sa config vers l'ecran
        si elle a change. Appelee depuis la boucle de cette instance -
        voir schedule_set_active_profile pour un appel cross-thread
        (profile_watcher.py tourne dans son propre thread)."""
        if name == self.active_profile_name:
            return
        self.color_mode.exit()
        self.ha_popup.close()
        self.active_profile_name = name
        if self.connected:
            self.push_config()

    def schedule_set_active_profile(self, name: str, timeout: float = 5.0) -> None:
        self._run_threadsafe(lambda: self.set_active_profile(name), timeout)

    def schedule_force_profile(self, name: str, timeout: float = 5.0) -> None:
        """Fige le profil actif sur `name` (bouton "Forcer ce profil" de la
        page de config) - la bascule automatique (profile_watcher.py)
        n'y touchera plus tant que schedule_clear_override() n'est pas
        appelee."""
        self.manual_override = name
        self.schedule_set_active_profile(name, timeout)

    def schedule_clear_override(self) -> None:
        """Reprend la bascule automatique (bouton "Automatique")."""
        self.manual_override = None

    def _run_threadsafe(self, fn, timeout: float) -> None:
        if self.loop is None:
            raise RuntimeError("Le client n'a pas encore demarre sa boucle")
        future = asyncio.run_coroutine_threadsafe(self._call_sync(fn), self.loop)
        future.result(timeout=timeout)

    async def _call_sync(self, fn) -> None:
        fn()

    async def run_forever(self) -> None:
        self.loop = asyncio.get_running_loop()
        await self.connect()
        self.client.subscribe_states(self.on_state)
        try:
            tick = 0
            while True:
                await asyncio.sleep(2)
                self.reload_config_if_changed()
                self.color_mode.check_timeout()
                self.ha_popup.check_timeout()
                tick += 1
                if tick % 5 == 0:
                    # Sonde active toutes les ~10s : un reflash de l'ecran
                    # (reboot complet) ne fait pas forcement lever d'erreur
                    # immediate cote client - sans ca, la connexion reste
                    # "vivante" indefiniment sans plus jamais rien recevoir,
                    # et tray.py ne retente jamais de se reconnecter.
                    await self.client.device_info()
        finally:
            self.connected = False
            status_key = self.entity_keys.get(STATUS_ENTITY_NAME)
            if status_key is not None:
                try:
                    self.client.text_command(status_key, "PC hors ligne")
                except Exception:
                    pass
            await self.client.disconnect()

"""Page de configuration visuelle du Stream Deck, en plusieurs pages pour
eviter la surcharge (esprit "gerer ses pages d'applications sur son
iPhone") :

- **Accueil** (`/`) : uniquement la grille des 16 emplacements (glisser-
  deposer + popup par emplacement). C'est la page qu'on utilise au
  quotidien.
- **Reglages** (`/reglages`) : connexion a l'ecran, cle API, Home
  Assistant, forme des boutons - des reglages qu'on ne touche qu'une fois.
  Demandee automatiquement au tout premier lancement (connexion vide).
- **Encodeurs** (`/encodeurs`) : action des 3 encodeurs par sens/appui.

Chaque page sauvegarde uniquement SA partie de la config (pas de risque
d'ecraser les emplacements en modifiant les reglages, etc.) et pousse vers
l'ecran via device_client.DeviceClient (connexion deja ouverte, pas de
reconnexion).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from . import actions as action_runner
from . import icons
from .device_client import DEFAULT_CONFIG_PATH, SLOT_COUNT, DeviceClient, load_config, save_config

LOG = logging.getLogger("streamdeck_dashboard")

DASHBOARD_PORT = 8080

app = Flask(__name__)
_config_path: Path = DEFAULT_CONFIG_PATH
_device_client: DeviceClient | None = None

ACTION_TYPES = ["none", "keys", "launch", "url", "media", "home_assistant"]
SLOT_TYPES = ["bouton", "barre", "texte"]
DIRECTIONS = ["clockwise", "anticlockwise", "press"]


def field_to_target(action_type: str, field_value: str):
    """'keys' se stocke en liste (ex ["ctrl","shift","s"]) ; 'home_assistant'
    se stocke en dict (parse_ha_target) ; les autres restent une chaine."""
    if action_type == "keys":
        return [part.strip() for part in field_value.split("+") if part.strip()]
    if action_type == "home_assistant":
        return parse_ha_target(field_value)
    return field_value


def target_to_field(action_type: str, target) -> str:
    if action_type == "keys" and isinstance(target, list):
        return "+".join(target)
    if action_type == "home_assistant" and isinstance(target, dict):
        return format_ha_target(target)
    return target or ""


def parse_ha_target(field_value: str) -> dict:
    """Format compact 'domaine.service:entity_id', ex 'light.toggle:light.bureau'."""
    try:
        service_part, entity_id = field_value.split(":", 1)
        domain, service = service_part.split(".", 1)
        return {"domain": domain.strip(), "service": service.strip(), "entity_id": entity_id.strip()}
    except ValueError:
        return {"domain": "", "service": "", "entity_id": ""}


def format_ha_target(action: dict) -> str:
    domain, service, entity_id = action.get("domain", ""), action.get("service", ""), action.get("entity_id", "")
    return f"{domain}.{service}:{entity_id}" if domain and service else ""


def default_slot(i: int) -> dict:
    return {
        "label": f"Slot {i + 1}",
        "icon": "",
        "type": "bouton",
        "visible": i < 12,
        "action": {"type": "none", "target": ""},
        "ha_entity": "",
    }


def default_slots() -> list[dict]:
    return [default_slot(i) for i in range(SLOT_COUNT)]


def default_encoders() -> list[dict]:
    empty = {"type": "none", "target": ""}
    return [{"clockwise": dict(empty), "anticlockwise": dict(empty), "press": dict(empty)} for _ in range(3)]


def normalize_slots(raw_slots: list[dict] | None) -> list[dict]:
    """Complete a exactement SLOT_COUNT emplacements (tronque/complete avec
    des valeurs par defaut si la config sur disque en a moins/plus)."""
    slots = list(raw_slots or [])
    normalized = []
    for i in range(SLOT_COUNT):
        slot = {**default_slot(i), **(slots[i] if i < len(slots) else {})}
        action = {"type": "none", "target": ""} if slot["type"] != "bouton" else slot.get("action") or {"type": "none", "target": ""}
        slot["action"] = action
        normalized.append(slot)
    return normalized


def push_to_screen() -> str | None:
    """Tente de pousser la config vers l'ecran. Retourne un message d'erreur
    (ou None si tout va bien) - a chaque endpoint de decider quoi en faire."""
    if _device_client is None:
        return None
    try:
        _device_client.schedule_push()
        return None
    except Exception as exc:
        LOG.exception("Echec de l'envoi vers l'ecran")
        return str(exc)


@app.route("/", methods=["GET"])
def index():
    config = load_config(_config_path)
    if not (config.get("connection") or {}).get("host"):
        return redirect(url_for("settings", premiere_fois="1"))
    slots = normalize_slots(config.get("slots"))
    for slot in slots:
        slot["action_field"] = target_to_field(slot["action"].get("type", "none"), slot["action"].get("target"))
    return render_template(
        "home.html",
        active_page="home",
        slots=slots,
        action_types=ACTION_TYPES,
        slot_types=SLOT_TYPES,
        icon_choices=icons.icon_choices(),
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/save", methods=["POST"])
def save():
    config = load_config(_config_path)
    try:
        raw_slots = json.loads(request.form.get("slots_json", "[]"))
    except (TypeError, ValueError):
        raw_slots = []
    slots = normalize_slots(raw_slots)
    for slot in slots:
        action_type = slot.get("action", {}).get("type", "none")
        action_field = slot.pop("action_field", "")
        slot["action"] = {"type": action_type, "target": field_to_target(action_type, action_field)}
        slot["icon_char"] = icons.icon_char(slot.get("icon", ""))
        slot["label"] = (slot.get("label") or "").strip()[:24] or slot["label"]
    config["slots"] = slots
    save_config(_config_path, config)

    error = push_to_screen()
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index", saved="1"))


@app.route("/reglages", methods=["GET"])
def settings():
    config = load_config(_config_path)
    return render_template(
        "settings.html",
        active_page="settings",
        connection=config.get("connection") or {},
        shape=config.get("shape", "carre"),
        home_assistant=config.get("home_assistant") or {},
        premiere_fois=request.args.get("premiere_fois") == "1",
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/reglages/save", methods=["POST"])
def save_settings():
    config = load_config(_config_path)
    config["connection"] = {
        "host": request.form.get("conn_host", "").strip(),
        "port": int(request.form.get("conn_port") or 6053),
        "api_key": request.form.get("conn_key", "").strip(),
    }
    config["shape"] = request.form.get("shape", "carre")
    config["home_assistant"] = {
        "url": request.form.get("ha_url", "").strip(),
        "token": request.form.get("ha_token", "").strip(),
    }
    config.setdefault("slots", default_slots())
    config.setdefault("encoders", default_encoders())
    save_config(_config_path, config)

    error = push_to_screen()
    if error:
        return redirect(url_for("settings", error=error))
    return redirect(url_for("index" if request.form.get("premiere_fois") == "1" else "settings", saved="1"))


@app.route("/encodeurs", methods=["GET"])
def encoders_page():
    config = load_config(_config_path)
    encoders = config.get("encoders") or default_encoders()
    encoders = [
        {
            direction: {**enc.get(direction, {}), "target": target_to_field(
                enc.get(direction, {}).get("type", "none"), enc.get(direction, {}).get("target")
            )}
            for direction in DIRECTIONS
        }
        for enc in encoders
    ]
    return render_template(
        "encoders.html",
        active_page="encoders",
        encoders=encoders,
        action_types=ACTION_TYPES,
        directions=DIRECTIONS,
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/encodeurs/save", methods=["POST"])
def save_encoders():
    config = load_config(_config_path)
    config["encoders"] = [
        {
            direction: {
                "type": (t := request.form.get(f"enc_{enc_i}_{direction}_type", "none")),
                "target": field_to_target(t, request.form.get(f"enc_{enc_i}_{direction}_target", "").strip()),
            }
            for direction in DIRECTIONS
        }
        for enc_i in range(3)
    ]
    save_config(_config_path, config)

    error = push_to_screen()
    if error:
        return redirect(url_for("encoders_page", error=error))
    return redirect(url_for("encoders_page", saved="1"))


@app.route("/run", methods=["POST"])
def run_action():
    """Endpoint optionnel : permet a Home Assistant (ou tout autre outil) de
    declencher une action locale en plus du fonctionnement direct (voir
    receiver.token dans dashboard_config.yaml)."""
    config = load_config(_config_path)
    token = (config.get("receiver") or {}).get("token")
    if not token or request.headers.get("X-Auth-Token") != token:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True, silent=True) or {}
    action_type = data.get("type")
    if not action_type:
        return jsonify({"error": "champ 'type' manquant"}), 400
    try:
        action_runner.run({"type": action_type, "target": data.get("target")})
    except Exception as exc:
        LOG.exception("Echec de l'action %r", data)
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def run_server(config_path: Path, device_client: DeviceClient | None = None, port: int = DASHBOARD_PORT) -> None:
    global _config_path, _device_client  # noqa: PLW0603
    _config_path = config_path
    _device_client = device_client
    LOG.info("Page de configuration sur http://127.0.0.1:%d", port)
    app.run(host="127.0.0.1", port=port, debug=False)

"""Petit serveur qui recoit des ordres d'action depuis Home Assistant et les
execute localement sur ce PC (raccourci clavier, lancement d'appli, url,
media). Contrairement a l'ancienne appli compagnon, ce serveur ne se
connecte pas lui-meme au Stream Deck : c'est Home Assistant qui garde cette
connexion (deja en place via l'integration ESPHome native) et qui decide,
via ses automatisations - configurables entierement dans son interface web,
sans toucher a un fichier YAML pour chaque bouton - quelle action envoyer
ici via un appel REST (voir home-assistant/example_automations.yaml).

Lancer :
    python -m streamdeck_companion.receiver
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml
from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from . import actions as action_runner
from . import screen_labels

LOG = logging.getLogger("streamdeck_receiver")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "receiver_config.yaml"

app = Flask(__name__)
_token: str | None = None
_config_path: Path = DEFAULT_CONFIG_PATH


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(path: Path, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


@app.route("/run", methods=["POST"])
def run_action():
    if not _token or request.headers.get("X-Auth-Token") != _token:
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


SCREEN_PAGE_TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Stream Deck - Personnaliser l'ecran</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #0B1929; --ocean: #0F2942; --slate: #1A3A52;
    --signal: #00B4D8; --mist: #8FAFC7; --fog: #6B8BA4; --green-tech: #16B84E; --red: #E63946;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--navy); color: #fff; font-family: 'Inter', sans-serif; padding: 32px 16px 80px; }
  h1 { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 26px; margin: 0 0 4px; }
  .sub { color: var(--mist); margin: 0 0 24px; font-size: 14px; }
  .page { max-width: 640px; margin: 0 auto; }
  .card { background: var(--ocean); border: 1px solid var(--slate); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .card h2 { font-family: 'Space Grotesk', sans-serif; font-size: 16px; margin: 0 0 12px; }
  label { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--mist); display: block; margin-top: 10px; }
  input[type=text] { background: var(--navy); border: 1px solid var(--slate); border-radius: 8px; color: #fff; padding: 8px 10px; font-family: 'Inter'; font-size: 14px; width: 100%; margin-top: 4px; }
  input:focus { outline: none; border-color: var(--signal); }
  button { background: var(--signal); color: var(--navy); border: none; border-radius: 8px; padding: 12px 24px; font-family: 'Space Grotesk'; font-weight: 700; font-size: 15px; cursor: pointer; margin-top: 8px; }
  button:hover { background: #48CAE4; }
  .banner-ok { background: rgba(22,184,78,.08); border: 1px solid rgba(22,184,78,.3); color: var(--green-tech); padding: 10px 16px; border-radius: 8px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .banner-err { background: rgba(230,57,70,.08); border: 1px solid rgba(230,57,70,.3); color: var(--red); padding: 10px 16px; border-radius: 8px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .hint { color: var(--fog); font-size: 12px; margin-top: 4px; }
</style>
</head>
<body>
<div class="page">
  <h1>PERSONNALISER L'ECRAN</h1>
  <p class="sub">Change les libelles des 6 boutons directement sur l'ecran (sans reflasher).</p>
  {% if error %}<div class="banner-err">Echec de l'envoi : {{ error }}</div>{% endif %}
  {% if saved %}<div class="banner-ok">Libelles envoyes a l'ecran.</div>{% endif %}
  <form method="post" action="{{ url_for('screen_save') }}">
    <div class="card">
      <h2>Connexion a l'ecran</h2>
      <label>Adresse (host ou IP)</label>
      <input type="text" name="device_host" value="{{ device.host or '' }}">
      <label>Port</label>
      <input type="text" name="device_port" value="{{ device.port or 6053 }}">
      <label>Cle API (meme valeur que firmware/secrets.yaml)</label>
      <input type="text" name="device_api_key" value="{{ device.api_key or '' }}">
    </div>
    <div class="card">
      <h2>Libelles des boutons</h2>
      {% for label in labels %}
      <label>Action {{ loop.index }}</label>
      <input type="text" name="label_{{ loop.index0 }}" value="{{ label }}" maxlength="24">
      {% endfor %}
      <p class="hint">24 caracteres max par bouton.</p>
    </div>
    <button type="submit">Envoyer a l'ecran</button>
  </form>
</div>
</body>
</html>
"""

DEFAULT_LABELS = [f"Action {i}" for i in range(1, 7)]


@app.route("/screen", methods=["GET"])
def screen_form():
    config = load_config(_config_path)
    return render_template_string(
        SCREEN_PAGE_TEMPLATE,
        device=config.get("device") or {},
        labels=config.get("labels") or DEFAULT_LABELS,
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/screen/save", methods=["POST"])
def screen_save():
    config = load_config(_config_path)
    device = {
        "host": request.form.get("device_host", "").strip(),
        "port": int(request.form.get("device_port") or 6053),
        "api_key": request.form.get("device_api_key", "").strip(),
    }
    labels = [request.form.get(f"label_{i}", "").strip() or f"Action {i + 1}" for i in range(6)]
    config["device"] = device
    config["labels"] = labels
    save_config(_config_path, config)

    try:
        asyncio.run(screen_labels.push_labels(device["host"], device["port"], device["api_key"], labels))
    except Exception as exc:
        LOG.exception("Echec de l'envoi des libelles a l'ecran")
        return redirect(url_for("screen_form", error=str(exc)))
    return redirect(url_for("screen_form", saved="1"))


def resolve_config(config_path: Path) -> dict:
    """Charge et valide receiver_config.yaml. Leve ValueError si invalide,
    plutot que d'appeler sys.exit() directement - permet d'etre appele
    depuis un contexte GUI (tray.py) qui veut afficher l'erreur autrement
    qu'en tuant tout le process."""
    if not config_path.exists():
        raise ValueError(f"Fichier de config introuvable: {config_path}")
    config = load_config(config_path)
    if not config.get("token"):
        raise ValueError(f"Aucun 'token' defini dans {config_path} - obligatoire")
    return config


def run_server(config: dict, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Demarre le serveur Flask (bloquant) - appelable directement depuis un
    thread (tray.py) ou depuis main() en CLI."""
    global _token, _config_path  # noqa: PLW0603
    _token = config["token"]
    _config_path = config_path
    port = config.get("port", 8765)
    LOG.info("Recepteur d'actions Stream Deck en ecoute sur le port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)  # noqa: S104 - ecoute LAN volontaire pour Home Assistant


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    try:
        config = resolve_config(config_path)
    except ValueError as exc:
        LOG.error("%s (copiez receiver_config.yaml.example)", exc)
        sys.exit(1)
    run_server(config, config_path)


if __name__ == "__main__":
    main()

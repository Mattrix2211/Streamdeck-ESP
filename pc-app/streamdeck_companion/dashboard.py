"""Page de configuration visuelle unique du Stream Deck : connexion, 12
boutons (libelle + action), 3 encodeurs (3 actions chacun), forme des
boutons - tout au meme endroit, sans toucher a un fichier a la main.

"Enregistrer et envoyer a l'ecran" sauvegarde dashboard_config.yaml ET
pousse immediatement les libelles/la forme vers l'ecran, via la connexion
deja ouverte par device_client.DeviceClient (aucune reconnexion).

Ouvert depuis le menu de l'icone de la barre des taches (tray.py) sur
http://127.0.0.1:8080 par defaut.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from . import actions as action_runner
from .device_client import DEFAULT_CONFIG_PATH, DeviceClient, load_config, save_config

LOG = logging.getLogger("streamdeck_dashboard")

DASHBOARD_PORT = 8080

app = Flask(__name__)
_config_path: Path = DEFAULT_CONFIG_PATH
_device_client: DeviceClient | None = None

ACTION_TYPES = ["none", "keys", "launch", "url", "media"]

PAGE_TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Stream Deck - Configuration</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #0B1929; --ocean: #0F2942; --slate: #1A3A52; --horizon: #1E4060;
    --signal: #00B4D8; --mist: #8FAFC7; --fog: #6B8BA4; --green-tech: #16B84E; --red: #E63946;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--navy); color: #fff; font-family: 'Inter', sans-serif; padding: 32px 16px 100px; }
  h1 { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 28px; margin: 0 0 4px; }
  h2 { font-family: 'Space Grotesk', sans-serif; font-size: 16px; margin: 0 0 12px; }
  .sub { color: var(--mist); margin: 0 0 24px; font-size: 14px; }
  .page { max-width: 980px; margin: 0 auto; }
  .card { background: var(--ocean); border: 1px solid var(--slate); border-radius: 12px; padding: 20px; margin-bottom: 16px; position: relative; overflow: hidden; }
  .card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--signal), transparent); }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid3 { display: grid; grid-template-columns: 1fr; gap: 12px; }
  label { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--mist); display: block; margin-top: 8px; }
  input[type=text], select { background: var(--navy); border: 1px solid var(--slate); border-radius: 8px; color: #fff; padding: 8px 10px; font-family: 'Inter'; font-size: 14px; width: 100%; margin-top: 4px; }
  input:focus, select:focus { outline: none; border-color: var(--signal); }
  button { background: var(--signal); color: var(--navy); border: none; border-radius: 8px; padding: 12px 24px; font-family: 'Space Grotesk'; font-weight: 700; font-size: 15px; cursor: pointer; margin-top: 8px; }
  button:hover { background: #48CAE4; }
  .banner-ok { background: rgba(22,184,78,.08); border: 1px solid rgba(22,184,78,.3); color: var(--green-tech); padding: 10px 16px; border-radius: 8px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .banner-err { background: rgba(230,57,70,.08); border: 1px solid rgba(230,57,70,.3); color: var(--red); padding: 10px 16px; border-radius: 8px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .hint { color: var(--fog); font-size: 12px; margin-top: 4px; }
  .buttons-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
  .button-slot { border-top: 1px solid var(--slate); padding-top: 10px; }
  .button-slot:first-child { border-top: none; padding-top: 0; }
  .encoder-block { border-top: 1px solid var(--slate); padding-top: 12px; margin-top: 12px; }
  .encoder-block:first-child { border-top: none; padding-top: 0; margin-top: 0; }
  .encoder-row { display: grid; grid-template-columns: 140px 1fr 1fr; gap: 10px; align-items: end; margin-top: 6px; }
</style>
</head>
<body>
<div class="page">
  <h1>STREAM DECK</h1>
  <p class="sub">Configuration complete - boutons, encodeurs, apparence. Un seul clic pour envoyer a l'ecran.</p>
  {% if error %}<div class="banner-err">Echec : {{ error }}</div>{% endif %}
  {% if saved %}<div class="banner-ok">Enregistre et envoye a l'ecran.</div>{% endif %}

  <form method="post" action="{{ url_for('save') }}">
    <div class="card">
      <h2>Connexion a l'ecran</h2>
      <div class="grid2">
        <div>
          <label>Adresse (IP du Stream Deck)</label>
          <input type="text" name="conn_host" value="{{ connection.host or '' }}">
        </div>
        <div>
          <label>Port</label>
          <input type="text" name="conn_port" value="{{ connection.port or 6053 }}">
        </div>
      </div>
      <label>Cle API (meme valeur que firmware/secrets.yaml)</label>
      <input type="text" name="conn_key" value="{{ connection.api_key or '' }}">
      <p class="hint">Un changement ici necessite de redemarrer l'icone de la barre des taches.</p>
    </div>

    <div class="card">
      <h2>Forme des boutons</h2>
      <select name="shape">
        <option value="carre" {% if shape != "rond" %}selected{% endif %}>Carre</option>
        <option value="rond" {% if shape == "rond" %}selected{% endif %}>Rond</option>
      </select>
    </div>

    <div class="card">
      <h2>Les 12 boutons</h2>
      <div class="buttons-grid">
        {% for b in buttons %}
        <div class="button-slot">
          <label>Bouton {{ loop.index }} - libelle</label>
          <input type="text" name="btn_label_{{ loop.index0 }}" value="{{ b.label }}" maxlength="24">
          <label>Action</label>
          <select name="btn_type_{{ loop.index0 }}">
            {% for t in action_types %}
            <option value="{{ t }}" {% if t == b.type %}selected{% endif %}>{{ t }}</option>
            {% endfor %}
          </select>
          <input type="text" name="btn_target_{{ loop.index0 }}" value="{{ b.target }}"
                 placeholder="ex: notepad.exe / ctrl+shift+s / https://... / vol_up">
        </div>
        {% endfor %}
      </div>
      <p class="hint">
        Types : <b>keys</b> (ex "ctrl+shift+s") &middot; <b>launch</b> (chemin/commande, arguments acceptes) &middot;
        <b>url</b> (site web ou URI comme steam://...) &middot;
        <b>media</b> (play_pause/next/previous/vol_up/vol_down/mute) &middot; <b>none</b> (rien).
      </p>
    </div>

    <div class="card">
      <h2>Les 3 encodeurs</h2>
      {% for e in encoders %}
      {% set enc_idx = loop.index0 %}
      <div class="encoder-block">
        <strong>Encodeur {{ loop.index }}</strong>
        {% for direction, dlabel in [("clockwise", "Sens horaire"), ("anticlockwise", "Sens antihoraire"), ("press", "Appui")] %}
        {% set d = e.get(direction, {}) %}
        <div class="encoder-row">
          <label style="margin-top:0">{{ dlabel }}</label>
          <select name="enc_{{ enc_idx }}_{{ direction }}_type">
            {% for t in action_types %}
            <option value="{{ t }}" {% if t == d.get("type", "none") %}selected{% endif %}>{{ t }}</option>
            {% endfor %}
          </select>
          <input type="text" name="enc_{{ enc_idx }}_{{ direction }}_target" value="{{ d.get('target', '') }}"
                 placeholder="ex: vol_up / ctrl+z / notepad.exe">
        </div>
        {% endfor %}
      </div>
      {% endfor %}
    </div>

    <button type="submit">Enregistrer et envoyer a l'ecran</button>
  </form>
</div>
</body>
</html>
"""


def field_to_target(action_type: str, field_value: str):
    """'keys' se stocke en liste (ex ["ctrl","shift","s"]) pour actions.py ;
    les autres types restent une simple chaine."""
    if action_type == "keys":
        return [part.strip() for part in field_value.split("+") if part.strip()]
    return field_value


def target_to_field(action_type: str, target) -> str:
    if action_type == "keys" and isinstance(target, list):
        return "+".join(target)
    return target or ""


def default_buttons() -> list[dict]:
    return [{"label": f"Action {i}", "type": "none", "target": ""} for i in range(1, 13)]


def default_encoders() -> list[dict]:
    empty = {"type": "none", "target": ""}
    return [{"clockwise": dict(empty), "anticlockwise": dict(empty), "press": dict(empty)} for _ in range(3)]


DIRECTIONS = ["clockwise", "anticlockwise", "press"]


@app.route("/", methods=["GET"])
def index():
    config = load_config(_config_path)
    buttons = config.get("buttons") or default_buttons()
    buttons = [{**b, "target": target_to_field(b.get("type", "none"), b.get("target"))} for b in buttons]
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
    return render_template_string(
        PAGE_TEMPLATE,
        connection=config.get("connection") or {},
        shape=config.get("shape", "carre"),
        buttons=buttons,
        encoders=encoders,
        action_types=ACTION_TYPES,
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/save", methods=["POST"])
def save():
    config = load_config(_config_path)
    config["connection"] = {
        "host": request.form.get("conn_host", "").strip(),
        "port": int(request.form.get("conn_port") or 6053),
        "api_key": request.form.get("conn_key", "").strip(),
    }
    config["shape"] = request.form.get("shape", "carre")
    config["buttons"] = [
        {
            "label": request.form.get(f"btn_label_{i}", "").strip() or f"Action {i + 1}",
            "type": (t := request.form.get(f"btn_type_{i}", "none")),
            "target": field_to_target(t, request.form.get(f"btn_target_{i}", "").strip()),
        }
        for i in range(12)
    ]
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

    if _device_client is not None:
        try:
            _device_client.schedule_push()
        except Exception as exc:
            LOG.exception("Echec de l'envoi vers l'ecran")
            return redirect(url_for("index", error=str(exc)))
    return redirect(url_for("index", saved="1"))


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

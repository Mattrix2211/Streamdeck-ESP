"""Interface web locale pour configurer visuellement les actions du Stream
Deck, sans editer config.yaml a la main. Lance avec :
    python -m streamdeck_companion.webui
puis ouvrez http://127.0.0.1:5000 dans un navigateur.

Note : sauvegarder depuis cette interface reecrit entierement config.yaml
(commentaires et mise en forme d'origine non conserves). Pour un fichier
annote a la main, editez-le directement plutot que via cette page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from flask import Flask, redirect, render_template_string, request, url_for

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
WEBUI_PORT = 5000

MEDIA_TARGETS = ["play_pause", "next", "previous", "vol_up", "vol_down", "mute"]

# Slots fixes correspondant aux entites definies dans firmware/package.yaml.
SLOTS = [
    ("Bouton d'action ecran", "action_1", "Action 1"),
    ("Bouton d'action ecran", "action_2", "Action 2"),
    ("Bouton d'action ecran", "action_3", "Action 3"),
    ("Bouton d'action ecran", "action_4", "Action 4"),
    ("Bouton d'action ecran", "action_5", "Action 5"),
    ("Bouton d'action ecran", "action_6", "Action 6"),
    ("Encodeur 1 - evenement", "clockwise", "Encodeur 1 - sens horaire"),
    ("Encodeur 1 - evenement", "anticlockwise", "Encodeur 1 - sens antihoraire"),
    ("Encodeur 1 - evenement", "press", "Encodeur 1 - appui"),
    ("Encodeur 2 - evenement", "clockwise", "Encodeur 2 - sens horaire"),
    ("Encodeur 2 - evenement", "anticlockwise", "Encodeur 2 - sens antihoraire"),
    ("Encodeur 2 - evenement", "press", "Encodeur 2 - appui"),
    ("Encodeur 3 - evenement", "clockwise", "Encodeur 3 - sens horaire"),
    ("Encodeur 3 - evenement", "anticlockwise", "Encodeur 3 - sens antihoraire"),
    ("Encodeur 3 - evenement", "press", "Encodeur 3 - appui"),
]

app = Flask(__name__)


def load_raw_config(path: Path) -> dict:
    if not path.exists():
        return {"connection": {"host": "streamdeck.local", "port": 6053, "api_encryption_key": ""}, "actions": {}}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_raw_config(path: Path, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def slot_action(config: dict, entity_name: str, event_type: str) -> dict:
    return (config.get("actions") or {}).get(entity_name, {}).get(event_type) or {}


def target_to_field(action: dict) -> str:
    """Convertit le target stocke (liste pour 'keys', chaine sinon) en texte pour le formulaire."""
    target = action.get("target")
    if isinstance(target, list):
        return "+".join(target)
    return target or ""


def field_to_target(action_type: str, field_value: str):
    if action_type == "keys":
        return [part.strip() for part in field_value.split("+") if part.strip()]
    return field_value.strip()


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
    --signal: #00B4D8; --mist: #8FAFC7; --fog: #6B8BA4; --green-tech: #16B84E;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--navy); color: #fff;
    font-family: 'Inter', sans-serif; padding: 32px 16px 80px;
  }
  h1 {
    font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 28px; margin: 0 0 4px;
  }
  .sub { color: var(--mist); margin: 0 0 24px; font-size: 14px; }
  .page { max-width: 900px; margin: 0 auto; }
  .card {
    background: var(--ocean); border: 1px solid var(--slate); border-radius: 12px;
    padding: 20px; margin-bottom: 16px; position: relative; overflow: hidden;
  }
  .card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--signal), transparent);
  }
  .card h2 {
    font-family: 'Space Grotesk', sans-serif; font-size: 16px; margin: 0 0 12px;
  }
  .slot {
    display: grid; grid-template-columns: 220px 140px 1fr; gap: 12px;
    align-items: center; padding: 10px 0; border-top: 1px solid var(--slate);
  }
  .slot:first-of-type { border-top: none; }
  label { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--mist); }
  select, input[type=text] {
    background: var(--navy); border: 1px solid var(--slate); border-radius: 8px;
    color: #fff; padding: 8px 10px; font-family: 'Inter', sans-serif; font-size: 14px;
    width: 100%;
  }
  select:focus, input:focus { outline: none; border-color: var(--signal); }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  button {
    background: var(--signal); color: var(--navy); border: none; border-radius: 8px;
    padding: 12px 24px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 15px; cursor: pointer; margin-top: 8px;
  }
  button:hover { background: #48CAE4; }
  .banner {
    background: rgba(22,184,78,.08); border: 1px solid rgba(22,184,78,.3);
    color: var(--green-tech); padding: 10px 16px; border-radius: 8px; margin-bottom: 20px;
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
  }
  .hint { color: var(--fog); font-size: 12px; margin-top: 4px; }
</style>
</head>
<body>
<div class="page">
  <h1>STREAM DECK</h1>
  <p class="sub">Configuration des actions - {{ config_path }}</p>
  {% if saved %}<div class="banner">Enregistre. L'appli compagnon applique le changement automatiquement (pas besoin de la redemarrer).</div>{% endif %}

  <form method="post" action="{{ url_for('save') }}">
    <div class="card">
      <h2>Connexion</h2>
      <div class="grid2">
        <div>
          <label>Adresse (host)</label>
          <input type="text" name="conn_host" value="{{ connection.host or '' }}">
        </div>
        <div>
          <label>Port du Stream Deck</label>
          <input type="text" name="conn_port" value="{{ connection.port or 6053 }}">
          <p class="hint">Port de l'API ESPHome sur le Stream Deck (6053 par defaut) -
            PAS le port de cette page web ({{ webui_port }}).</p>
        </div>
      </div>
      <label>Cle API (meme valeur que firmware/secrets.yaml)</label>
      <input type="text" name="conn_key" value="{{ connection.api_encryption_key or '' }}">
      <p class="hint">Un changement ici necessite de redemarrer l'appli compagnon.</p>
    </div>

    <div class="card">
      <h2>Boutons et encodeurs</h2>
      {% for entity_name, event_type, label, type_val, target_val in slots %}
      <div class="slot">
        <label>{{ label }}</label>
        <select name="type_{{ loop.index0 }}">
          {% for t in ["keys", "launch", "url", "media", "none"] %}
          <option value="{{ t }}" {% if t == type_val %}selected{% endif %}>{{ t }}</option>
          {% endfor %}
        </select>
        <input type="text" name="target_{{ loop.index0 }}" value="{{ target_val }}"
               placeholder="ex: ctrl+shift+s / notepad.exe / https://... / vol_up">
        <input type="hidden" name="entity_{{ loop.index0 }}" value="{{ entity_name }}">
        <input type="hidden" name="event_{{ loop.index0 }}" value="{{ event_type }}">
      </div>
      {% endfor %}
      <p class="hint">
        Types : <b>keys</b> (raccourci, ex "ctrl+shift+s") &middot;
        <b>launch</b> (chemin/commande) &middot; <b>url</b> (adresse web) &middot;
        <b>media</b> (une valeur parmi {{ media_targets }}) &middot;
        <b>none</b> (rien de configure).
      </p>
    </div>

    <button type="submit">Enregistrer</button>
  </form>
</div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    saved = request.args.get("saved") == "1"
    config = load_raw_config(DEFAULT_CONFIG_PATH)
    connection = config.get("connection") or {}
    slots = []
    for entity_name, event_type, label in SLOTS:
        action = slot_action(config, entity_name, event_type)
        slots.append((entity_name, event_type, label, action.get("type", "none"), target_to_field(action)))
    return render_template_string(
        PAGE_TEMPLATE,
        config_path=str(DEFAULT_CONFIG_PATH),
        connection=connection,
        slots=slots,
        media_targets=", ".join(MEDIA_TARGETS),
        saved=saved,
        webui_port=WEBUI_PORT,
    )


@app.route("/save", methods=["POST"])
def save():
    config = load_raw_config(DEFAULT_CONFIG_PATH)
    config["connection"] = {
        "host": request.form.get("conn_host", "").strip(),
        "port": int(request.form.get("conn_port") or 6053),
        "api_encryption_key": request.form.get("conn_key", "").strip(),
    }

    actions: dict = {}
    for i, (entity_name, event_type, _label) in enumerate(SLOTS):
        action_type = request.form.get(f"type_{i}", "none")
        target_field = request.form.get(f"target_{i}", "")
        if action_type == "none" or not target_field.strip():
            continue
        actions.setdefault(entity_name, {})[event_type] = {
            "type": action_type,
            "target": field_to_target(action_type, target_field),
        }
    config["actions"] = actions

    save_raw_config(DEFAULT_CONFIG_PATH, config)
    return redirect(url_for("index", saved="1"))


def main() -> None:
    global DEFAULT_CONFIG_PATH  # noqa: PLW0603
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    DEFAULT_CONFIG_PATH = config_path
    print(f"Interface de configuration sur http://127.0.0.1:{WEBUI_PORT}  (fichier: {config_path})")
    app.run(host="127.0.0.1", port=WEBUI_PORT, debug=False)


if __name__ == "__main__":
    main()

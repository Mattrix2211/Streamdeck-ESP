# Appli compagnon PC

Se connecte au Stream Deck via l'API native ESPHome chiffree (le meme
protocole que celui utilise par Home Assistant - `aioesphomeapi`), ecoute les
boutons et encodeurs, execute des actions locales, et pousse un statut texte
affiche sur l'ecran.

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Editez `config.yaml` :
- `connection.host` : IP ou nom mDNS du Stream Deck (`streamdeck.local`)
- `connection.api_encryption_key` : **la meme cle** que `api_encryption_key`
  dans `firmware/secrets.yaml`
- `actions` : mapping evenement -> action locale (voir les exemples fournis)

## Lancer

```bash
python -m streamdeck_companion.app
```

## Interface web de configuration

Plutot que d'editer `config.yaml` a la main, une petite page web locale
permet de choisir visuellement l'action de chaque bouton/encodeur :

```bash
python -m streamdeck_companion.webui
```

Puis ouvrez http://127.0.0.1:5000 dans un navigateur. Les changements sont
appliques par l'appli compagnon (`app.py`) **sans redemarrage** (elle relit
`config.yaml` toutes les 2 secondes). Seuls les identifiants de connexion
(host/cle API) necessitent un vrai redemarrage de `app.py` pour prendre effet.

Note : sauvegarder depuis cette page reecrit entierement `config.yaml` (les
commentaires eventuels sont perdus). Si vous preferez un fichier annote a la
main, editez-le directement plutot que via cette interface.

## Types d'actions disponibles dans `config.yaml`

| type     | target                          | effet                                    |
|----------|----------------------------------|-------------------------------------------|
| `keys`   | liste de touches (ex `["ctrl","c"]`) | envoie une combinaison clavier         |
| `launch` | chemin ou commande               | lance une application                     |
| `url`    | URL                               | ouvre l'URL dans le navigateur par defaut  |
| `media`  | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |

## Limitations connues

- Les combinaisons clavier et touches multimedia passent par le module
  `keyboard`, qui necessite les droits administrateur/root sur certaines
  plateformes (et ne fonctionne pas sous Wayland).
- Sur macOS, `keyboard` n'emule pas les touches multimedia : seul le volume
  systeme est gere nativement (`osascript`). Pour play/pause/next sur macOS,
  il faudra integrer un outil tiers (ex. `nowplaying-cli`) dans
  `streamdeck_companion/actions.py::_media_macos`.
- Le "statut PC" pousse vers l'ecran (`Companion.push_status`) n'est branche
  ici que sur connexion/deconnexion ("PC connecte"/"PC hors ligne") a titre
  d'exemple. Pour afficher le titre de la fenetre active, la piste en cours,
  etc., appelez `push_status(...)` depuis votre propre logique.

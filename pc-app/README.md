# Appli compagnon PC

Petit programme qui tourne en fond sur votre PC (icone dans la barre des
taches, pas de fenetre de terminal), et execute des actions locales
(raccourci clavier, lancement d'appli/jeu, media, url) quand Home Assistant
le lui demande.

**Toute la configuration se fait dans Home Assistant** (automatisations
visuelles, menus deroulants) : quel bouton/encodeur declenche quelle action.
Ce programme ne fait qu'executer ce que Home Assistant lui envoie - il ne se
connecte pas lui-meme au Stream Deck (c'est Home Assistant qui garde cette
connexion, deja en place).

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
cp receiver_config.yaml.example receiver_config.yaml
```

Editez `receiver_config.yaml` :
- `token` : generez-en un avec `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`
  (protege ce PC : sans lui, n'importe qui sur le reseau local pourrait
  demander l'execution d'une action)
- `port` : 8765 par defaut, changez si deja utilise

## Lancer au quotidien (recommande)

Icone de barre des taches, pas de terminal a garder ouvert :

```powershell
pythonw -m streamdeck_companion.tray
```

Pour qu'elle demarre automatiquement a l'ouverture de session Windows :

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

Clic droit sur l'icone dans la barre des taches pour : personnaliser
l'ecran, ouvrir Home Assistant, ou quitter.

## Lancer manuellement (sans icone, avec logs dans le terminal)

```bash
python -m streamdeck_companion.receiver
```

## Cote Home Assistant

1. Collez `home-assistant/rest_command.yaml.snippet` dans `configuration.yaml`
   (une seule fois), en remplacant l'IP par celle de ce PC et le token par
   celui de `receiver_config.yaml`. Redemarrez Home Assistant.
2. Creez vos automatisations (menu **Parametres > Automatisations**, ou en
   YAML) : trigger = l'entite `event.streamdeck_...` du bouton/encodeur,
   action = service `rest_command.streamdeck_pc_action` avec `type`/`target`.
   Exemples complets dans `home-assistant/example_automations.yaml`.

## Personnaliser l'ecran (libelles des boutons)

Accessible depuis le menu de l'icone de la barre des taches ("Personnaliser
l'ecran"), ou directement `http://127.0.0.1:8765/screen` dans un navigateur.
Change le texte affiche sur les 6 boutons de l'ecran, sans reflasher le
firmware. Necessite l'adresse et la cle API du Stream Deck (memes valeurs
que `firmware/secrets.yaml`).

## Types d'actions (`type`/`target` envoyes par Home Assistant)

| type     | target                          | effet                                    |
|----------|----------------------------------|-------------------------------------------|
| `keys`   | liste de touches (ex `["ctrl","c"]`) | envoie une combinaison clavier         |
| `launch` | chemin ou commande (arguments acceptes) | lance une application/un jeu (ex: `"steam://rungameid/570"` en type `url`, ou une commande complete en `launch`) |
| `url`    | URL ou URI (`steam://...`, `discord://...`) | ouverte via le gestionnaire par defaut du systeme |
| `media`  | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |

## Limitations connues

- Les combinaisons clavier et touches multimedia passent par le module
  `keyboard`, qui necessite les droits administrateur/root sur certaines
  plateformes (et ne fonctionne pas sous Wayland).
- Sur macOS, `keyboard` n'emule pas les touches multimedia : seul le volume
  systeme est gere nativement (`osascript`). Pour play/pause/next sur macOS,
  il faudra integrer un outil tiers (ex. `nowplaying-cli`) dans
  `streamdeck_companion/actions.py::_media_macos`.
- `tray.py` n'a pu etre teste que hors environnement graphique Windows reel
  (logique de routes/menu verifiee ; le rendu de l'icone lui-meme necessite
  un vrai bureau Windows pour etre confirme).
- Le serveur ecoute sur toutes les interfaces (0.0.0.0) pour etre joignable
  par Home Assistant : gardez le `token` secret, c'est la seule protection.

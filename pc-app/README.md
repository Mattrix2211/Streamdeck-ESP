# Appli compagnon PC

Tout se configure ici, visuellement, sans toucher a un fichier a la main :
la disposition (quel bouton/encodeur fait quoi), les libelles affiches sur
l'ecran, et leur forme (carre/rond). Un clic envoie tout vers l'ecran.

Tourne en icone dans la barre des taches (pas de fenetre de terminal), se
connecte directement au Stream Deck (pas besoin de Home Assistant pour que
ca fonctionne - meme si HA continue de voir l'appareil nativement en
parallele).

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
cp dashboard_config.yaml.example dashboard_config.yaml
```

Editez au moins `connection.host` et `connection.api_key` dans
`dashboard_config.yaml` (l'IP se trouve dans Home Assistant : l'appareil
"Stream Deck" > Adresse IP ; la cle API est la meme que dans
`firmware/secrets.yaml`). Le reste (boutons, encodeurs, forme) se regle
ensuite depuis la page de configuration.

## Lancer au quotidien (recommande)

Icone de barre des taches, pas de terminal a garder ouvert :

```powershell
pythonw -m streamdeck_companion.tray
```

Pour qu'elle demarre automatiquement a l'ouverture de session Windows :

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

Clic sur l'icone (ou "Configurer le Stream Deck" dans son menu) pour
ouvrir la page de configuration - `http://127.0.0.1:8080`.

## Lancer manuellement (sans icone, avec logs dans le terminal)

```bash
python -c "from streamdeck_companion.tray import main; main()"
```

## La page de configuration

- **Connexion** : IP/port/cle API de l'ecran.
- **Forme des boutons** : carre ou rond.
- **12 boutons** : pour chacun, un libelle et une action (type + cible).
- **3 encodeurs** : pour chacun, une action par sens de rotation et une pour
  l'appui.
- **"Enregistrer et envoyer a l'ecran"** : sauvegarde tout dans
  `dashboard_config.yaml` et pousse immediatement les libelles/la forme
  vers l'ecran (les actions des boutons/encodeurs, elles, sont deja actives
  des l'enregistrement - pas besoin de rien pousser de plus, l'appli les
  applique directement quand vous appuyez).

## Types d'actions (`type` / cible)

| type     | cible                             | effet                                    |
|----------|------------------------------------|-------------------------------------------|
| `none`   | -                                  | rien configure                             |
| `keys`   | ex `ctrl+shift+s`                 | envoie une combinaison clavier             |
| `launch` | chemin ou commande (arguments acceptes) | lance une application/un jeu (ex: la commande de lancement de Discord) |
| `url`    | URL ou URI (`steam://...`, `discord://...`) | ouverte via le gestionnaire par defaut du systeme |
| `media`  | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |

## Integration Home Assistant (optionnelle, en plus)

Comme l'ecran expose ses entites nativement (integration ESPHome), Home
Assistant les voit et peut declencher ses propres automatisations en
parallele de cette appli (aucune configuration necessaire cote HA pour ca).

Si vous voulez en plus que Home Assistant puisse demander une action a ce
PC (ex: depuis une automation HA sans rapport avec le Stream Deck), activez
`receiver.token` dans `dashboard_config.yaml` et utilisez
`home-assistant/rest_command.yaml.snippet` + les exemples dans
`home-assistant/example_automations.yaml`. Ce n'est **pas necessaire** pour
que les boutons/encodeurs du Stream Deck fonctionnent - c'est un bonus.

## Limitations connues

- Les combinaisons clavier et touches multimedia passent par le module
  `keyboard`, qui necessite les droits administrateur/root sur certaines
  plateformes (et ne fonctionne pas sous Wayland).
- Sur macOS, `keyboard` n'emule pas les touches multimedia : seul le volume
  systeme est gere nativement (`osascript`). Pour play/pause/next sur macOS,
  il faudra integrer un outil tiers (ex. `nowplaying-cli`) dans
  `streamdeck_companion/actions.py::_media_macos`.
- `tray.py` n'a pu etre teste que hors environnement graphique Windows reel
  (logique de connexion/config verifiee en detail ; le rendu de l'icone
  lui-meme necessite un vrai bureau Windows pour etre confirme).
- Un changement d'IP/port/cle API necessite de redemarrer l'icone de la
  barre des taches (la reconnexion automatique gere les coupures reseau,
  pas un changement de configuration de connexion).

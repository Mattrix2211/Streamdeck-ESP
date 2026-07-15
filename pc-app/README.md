# Appli compagnon PC

Trois pages, comme gerer les pages d'applications sur un telephone :

- **Accueil** : uniquement la grille des 16 emplacements - glisser-deposer
  pour reordonner, cliquer une tuile pour la configurer (popup). C'est la
  seule page dont vous avez besoin au quotidien.
- **Encodeurs** : l'action des 3 encodeurs (rarement modifiee).
- **Reglages** (icone &#9881;) : connexion a l'ecran, cle API, Home
  Assistant, forme des boutons - demandee automatiquement au tout premier
  lancement, puis on n'y revient quasiment plus.

Tourne en icone dans la barre des taches (pas de fenetre de terminal), se
connecte directement au Stream Deck (pas besoin de Home Assistant pour que
ca fonctionne - meme si HA continue de voir l'appareil nativement en
parallele, et peut en plus alimenter des widgets en temps reel, voir plus
bas).

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

Pas de fichier a copier a la main : au tout premier lancement, l'appli
cree `dashboard_config.yaml` automatiquement (vide) et vous redirige vers
la page **Reglages** pour renseigner l'IP de l'ecran et la cle API (meme
valeur que `firmware/secrets.yaml` ; l'IP se trouve dans Home Assistant :
l'appareil "Stream Deck" > Adresse IP). Une fois valide, vous arrivez sur
l'accueil et n'avez plus besoin d'y retoucher.

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

## Les 3 pages

### Accueil (`/`)

La grille des 16 emplacements : cliquez une tuile pour ouvrir sa popup de
reglages (visibilite, libelle, icone, type, action) ; glissez-deposez une
tuile sur une autre pour les echanger. 12 emplacements sont visibles par
defaut (comme l'ancien systeme a 12 boutons), les 4 derniers sont
desactives - activez-les dans leur popup ("Visible sur l'ecran") des que
vous en avez besoin, sans reflasher. "Enregistrer et envoyer a l'ecran"
sauvegarde et pousse immediatement la grille vers l'ecran.

### Encodeurs (`/encodeurs`)

Pour chacun des 3 encodeurs, une action par sens de rotation et une pour
l'appui. Chaque encodeur affiche sur l'ecran une barre 0-100% (type "barre
de son") au lieu d'un simple compteur qui s'incremente sans limite -
pratique pour un encodeur de volume par exemple. La valeur repart de 0
a chaque redemarrage de l'ecran (pas de memorisation du dernier niveau).

### Reglages (`/reglages`)

Connexion (IP/port/cle API), forme des boutons (carre/rond, s'applique aux
16 emplacements), Home Assistant (URL + jeton). Des reglages qu'on ne
touche presque jamais une fois l'ecran configure - a l'ecart de la page
qu'on utilise au quotidien.

### Type d'emplacement (`bouton` / `barre` / `texte`)

- **bouton** : declenche une action au clic (voir tableau ci-dessous).
- **barre** : jauge 0-100, alimentee par l'etat d'une entite Home
  Assistant numerique (volume, luminosite, batterie...) - reglee via
  "Source Home Assistant (entity_id)" dans la popup.
- **texte** : affiche la valeur brute d'une entite HA + son unite (ex
  "21.5°C") - meme reglage de source.

Les widgets (`barre`/`texte`) sont rafraichis toutes les ~15 secondes par
`streamdeck_companion/ha_poller.py`, qui interroge l'API REST de Home
Assistant en arriere-plan (pas de websocket, suffisant pour quelques
entites).

## Types d'actions (`type` / cible)

| type              | cible                             | effet                                    |
|-------------------|------------------------------------|-------------------------------------------|
| `none`            | -                                  | rien configure                             |
| `keys`            | ex `ctrl+shift+s`                 | envoie une combinaison clavier             |
| `launch`          | chemin ou commande (arguments acceptes) | lance une application/un jeu (ex: la commande de lancement de Discord) |
| `url`             | URL ou URI (`steam://...`, `discord://...`) | ouverte via le gestionnaire par defaut du systeme |
| `media`           | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |
| `home_assistant`  | dans la popup : domaine/service/entite (encodeurs : format compact `domaine.service:entite`, ex `light.toggle:light.bureau`) | appelle un service Home Assistant (bascule une lumiere/prise/scene...) |

## Icones

Le selecteur d'icone (popup d'un emplacement) propose un catalogue curate
de glyphes Material Icons (`streamdeck_companion/icons.py`) - meme police
chargee dans le navigateur et sur l'ecran (`gfonts://Material Icons` dans
`firmware/package.yaml`), donc l'apercu correspond a ce qui s'affiche
reellement. Pas d'upload d'image personnalisee (voir Limitations).

## Integration Home Assistant

Comme l'ecran expose ses entites nativement (integration ESPHome), Home
Assistant les voit et peut declencher ses propres automatisations en
parallele de cette appli (aucune configuration necessaire cote HA pour ca).

En renseignant l'URL et un jeton d'acces longue duree dans la page de
configuration, vous debloquez en plus :
- les emplacements type **barre**/**texte** (etat en direct d'une entite HA)
- le type d'action **home_assistant** (un bouton qui appelle un service HA)

Independamment, si vous voulez que Home Assistant puisse demander une
action a ce PC (ex: depuis une automation HA sans rapport avec le Stream
Deck), activez `receiver.token` dans `dashboard_config.yaml` et utilisez
`home-assistant/rest_command.yaml.snippet` + les exemples dans
`home-assistant/example_automations.yaml`. Rien de tout ceci n'est
necessaire pour que les emplacements/encodeurs du Stream Deck fonctionnent
- c'est un bonus.

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
- Le bouton "media" (`play_pause` etc.) envoie une touche multimedia - il
  n'affiche pas l'etat de lecture reel (recuperer l'etat "en cours de
  lecture" de facon fiable et multi-plateforme demanderait une integration
  bien plus lourde). Pour un vrai indicateur en direct, utilisez un
  emplacement type `texte`/`barre` avec une source Home Assistant (ex un
  media_player HA) a la place.
- Le glisser-deposer **echange** deux emplacements (pas d'insertion avec
  decalage des autres) - comportement simple et previsible plutot qu'un
  reordonnancement complet.
- Pas d'upload d'icone personnalisee : le catalogue est un jeu curate de
  glyphes Material Icons (`streamdeck_companion/icons.py`). Pour en
  ajouter, il faut aussi ajouter le point de code correspondant au
  `glyphs:` de `font_icons` dans `firmware/package.yaml`, sinon il
  s'affiche comme une case vide sur l'ecran.
- Les widgets Home Assistant (`barre`/`texte`) sont sondes par polling
  REST toutes les ~15s (`ha_poller.py`), pas en temps reel instantane.
- La page de configuration a ete testee de bout en bout avec un navigateur
  headless (rendu de la grille, popup, glisser-deposer, sauvegarde) mais
  pas visuellement sur l'ecran physique - verifiez apres un push que les
  icones/couleurs/tailles vous conviennent et signalez tout ce qui parait
  cassé (ex une icone qui s'affiche comme une case vide).

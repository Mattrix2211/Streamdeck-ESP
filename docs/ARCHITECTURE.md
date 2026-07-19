# Architecture

```
                         +-------------------------+
                         |  Stream Deck (ESP32-P4)  |
                         |  ESPHome + LVGL          |
                         |  - ecran tactile 1024x600|
                         |  - 16 emplacements + 3 encodeurs|
                         |  - Wi-Fi via ESP32-C6     |
                         +------------+-------------+
                                      |
                         API native ESPHome (chiffree,
                         Noise Protocol, port 6053)
                                      |
                +---------------------+---------------------+
                |                                           |
     +----------v-----------+                    +----------v-----------+
     |   Home Assistant       |                    |   Appli PC (Python)    |
     |   (integration ESPHome  |                    |   streamdeck_companion/|
     |    native - facultatif   |                    |   device_client.py     |
     |    pour ses propres      |                    |   (connexion directe   |
     |    automations)          |                    |    et permanente)       |
     +------------+-------------+                    +------------+------------+
                  |                                                |
                  | API REST HA (facultatif)          dashboard.py (config
                  | (etat live + services)             visuelle, port 8080)
                  |                                    + tray.py (icone barre
                  v                                    des taches)
     +------------+-------------+                                  |
     |  ha_client.py / ha_poller.py (sondage ~15s) -----------------+
     |  widgets barre/texte + action 'home_assistant'               |
     +--------------------------------------------------------------+
                                                                    |
                                                       actions locales :
                                                       raccourcis clavier,
                                                       lancement d'appli/jeu,
                                                       media, url
```

## L'appli PC comme point de configuration unique

Tout se regle dans l'appli PC (`http://127.0.0.1:8080`), en 2 pages pour
eviter la surcharge (esprit "gerer ses pages d'applications sur un
telephone") :
- **Accueil** (`/`) : un ou plusieurs **profils** (onglets), chacun une
  maquette fidele de l'ecran (memes proportions et disposition que le
  firmware) avec ses propres 16 emplacements (bouton/barre/texte, icone,
  action) et 3 encodeurs, configurables via popup - les emplacements
  masques sont a part sous la maquette, glisser-deposer pour
  reordonner/echanger dans les deux sections - la seule page du quotidien.
  L'ecran bascule automatiquement sur le profil dont le declencheur
  correspond a l'application au premier plan sur le PC (voir "Profils par
  application" plus bas). Le type d'action `launch` propose une
  bibliotheque d'applications (grille avec recherche, applications
  detectees + personnalisees) plutot que de taper un chemin.
- **Reglages** (`/reglages`) : connexion, forme carre/rond, Home
  Assistant - demandee automatiquement au tout premier lancement
  (`dashboard_config.yaml` est cree vide par `tray.py`, plus besoin de
  copier un fichier `.example` a la main), puis rarement revisitee.

Un seul clic ("Enregistrer et envoyer a l'ecran") sauvegarde et pousse les
changements de la page courante (chaque page ne touche que sa portion de
`dashboard_config.yaml`, jamais les autres).

- `device_client.py` maintient une connexion permanente et directe a
  l'ecran (IP configuree une fois, pas de mDNS) : elle ecoute les
  emplacements/encodeurs ET sert a pousser la config du **profil actif**
  (libelle, icone, type, visibilite, valeur des widgets) - meme connexion,
  pas de reconnexion a chaque changement (de config comme de profil).
- `dashboard.py` (+ `templates/base.html`+`home.html`+`settings.html`,
  `static/dashboard.js`) sont les 2 pages web (thread Flask separe), qui
  communiquent avec `device_client.py` via `asyncio.run_coroutine_threadsafe`
  pour rester thread-safe.
- `profiles.py` : modele des profils (migration de l'ancien format,
  correspondance declencheur -> profil) - partage par `dashboard.py` et
  `device_client.py`.
- `profile_watcher.py` : sonde la fenetre au premier plan sur le PC toutes
  les ~1.5s (Windows uniquement) et bascule le profil actif en consequence.
- `ha_client.py`/`ha_poller.py` sondent l'API REST de Home Assistant
  (facultatif) toutes les ~15s pour rafraichir les emplacements type
  widget, et executent le type d'action `home_assistant` (appel de
  service). `ha_client.py::list_entities()` alimente aussi le picker
  d'entites recherchable de la popup d'emplacement (source d'un widget,
  cible d'une action `home_assistant`), avec des services courants
  curates par domaine (`COMMON_SERVICES`). Pour un bouton cible une
  ampoule (domaine `light`) avec "Afficher la couleur de l'ampoule"
  coche, le meme sondage pousse aussi une couleur de fond
  (`ha_client.py::light_color_hex()` - RGB reel, ou approxime depuis la
  temperature de couleur, ou blanc chaud generique) vers une 5e entite
  par emplacement (`Slot N - couleur`, voir `firmware/slots_*.yaml`). Un
  appui long sur ce meme bouton (evenement `hold_N`) ouvre un mode
  reglage en direct via les 3 encodeurs (teinte/chaleur/intensite,
  limite en frequence - `color_mode.py::ColorModeController`, extrait de
  `device_client.py` pour rester sous la limite de lignes par fichier),
  affichant un panneau a l'ecran avec une barre par axe (entites `number`
  `Mode couleur - */valeur`, voir `firmware/package.yaml`), ferme par
  timeout ou par le bouton "X" flottant (`close_color_mode`). Un
  emplacement `barre` avec une source HA accepte aussi le tactile
  gauche/droite pour l'augmenter/diminuer directement
  (`ha_client.py::adjust_entity_percent()`, evenements
  `barre_inc_N`/`barre_dec_N`).
- `icons.py` : catalogue d'icones (glyphes Material Icons, memes
  points de code que la police `font_icons` du firmware).
- `app_library.py`/`custom_apps.py`/`browse.py` : bibliotheque
  d'applications du picker "launch" - detection des raccourcis du menu
  Demarrer, applications personnalisees persistees dans
  `dashboard_config.yaml`, selecteur de fichier natif pour les ajouter.
- `tray.py` orchestre le tout (connexion, dashboard, sondeur HA, sondeur de
  profil) dans une icone de barre des taches, sans fenetre de terminal - le
  menu affiche le profil actuellement actif.
- Home Assistant continue de voir l'appareil nativement (integration
  ESPHome auto-decouverte) et peut faire ses propres automations en
  parallele, mais ce n'est **pas necessaire** pour que le Stream Deck
  fonctionne avec le PC.

## Les 16 emplacements (au lieu de boutons fixes)

LVGL/ESPHome fige la disposition a la compilation - impossible de changer
le nombre de widgets sans reflasher. Le compromis retenu : 16 emplacements
sont toujours presents dans le firmware (`firmware/slots_*.yaml` +
`slot_widgets.yaml`), chacun montrable/masquable et reconfigurable a chaud
(sans reflasher) via 5 entites :

- `text` libelle, `text` valeur (widgets), `text` icone (glyphe brut)
- `select` type (`bouton`/`barre`/`texte`)
- `switch` visible

12 sont visibles par defaut (comportement identique a l'ancien systeme a
12 boutons), 4 desactives - a activer depuis la popup d'un emplacement
("Visible sur l'ecran") quand besoin.

## Profils par application

Un Stream Deck du commerce change de grille selon l'application active -
c'est le principal ecart avec une solution maison basique, comble ici par
un systeme de profils :

- Chaque profil (`dashboard_config.yaml`, cle `profiles`) a un `name`, un
  `trigger` optionnel (`{process: "nom.exe"}` ou `null`) et sa propre paire
  `slots`/`encoders`. Le premier profil sans `trigger` sert de repli.
- `profile_watcher.py::run_forever()` tourne dans son propre thread
  (Windows uniquement) : toutes les ~1.5s, il identifie le processus de la
  fenetre au premier plan (`win32gui.GetForegroundWindow()` +
  `win32process.GetWindowThreadProcessId()` + `psutil`), le compare aux
  declencheurs via `profiles.match_profile()`, et appelle
  `device_client.schedule_set_active_profile()` si le profil correspondant
  a change - qui pousse alors sa config vers l'ecran (meme mecanisme que
  `push_config()`) et redirige la resolution des actions (`_resolve_action`)
  vers ce nouveau profil, pour que les boutons physiques declenchent bien
  les actions du profil affiche.
- **Bascule manuelle** : `device_client.manual_override` (nom de profil ou
  `None`) est mis a jour par les boutons "Forcer ce profil"/"Automatique"
  de la page web (`/profiles/force`, `/profiles/auto`) ; quand il est
  renseigne, `profile_watcher.py` n'y touche plus jusqu'a "Automatique".
- La page web sonde `/profiles/status` toutes les ~3s pour afficher (point
  vert sur l'onglet, texte de statut) quel profil est reellement actif sur
  l'ecran, independamment de l'onglet en cours d'edition.
- Migration transparente : `profiles.migrate_profiles()` convertit une
  config pre-profils (`slots`/`encoders` a la racine, format d'avant ce
  chantier) en un unique profil "Defaut" au premier chargement.

## Flux "emplacement -> PC"

1. L'utilisateur touche un emplacement de type `bouton` sur l'ecran (LVGL)
   ou tourne un encodeur.
2. Le firmware declenche une entite `event:` (`event.trigger`).
3. `device_client.py` recoit l'etat via sa connexion permanente
   (`subscribe_states`), retrouve l'action configuree (emplacement ou
   sens/appui d'encodeur) dans `dashboard_config.yaml` et l'execute soit
   localement (`actions.py` : raccourcis/lancement/media/url), soit via
   Home Assistant (`ha_client.py::call_service` pour le type d'action
   `home_assistant`).
4. En bonus, Home Assistant peut aussi ecouter la meme entite `event:`
   pour ses propres automations, independamment (voir
   `home-assistant/example_automations.yaml`).

## Flux "PC -> ecran"

- **Config des emplacements + forme** : `dashboard.py` (page "Enregistrer
  et envoyer a l'ecran") appelle `device_client.schedule_push()`, qui
  pousse libelle/icone/type/visibilite de chaque emplacement du **profil
  actif** + la forme (voir "Profils par application").
- **Valeur des widgets** (`barre`/`texte`) : `ha_poller.py` sonde Home
  Assistant toutes les ~15s et appelle
  `device_client.schedule_push_values()` pour ne rafraichir que les
  entites `text.slot_N_valeur` concernees (sans re-pousser tout le reste).
- **Statut / info generique depuis Home Assistant** : HA peut aussi
  appeler directement le service `text.set_value` sur
  `text.streamdeck_statut_pc` (voir `home-assistant/example_automations.yaml`).

## Design

L'interface LVGL reprend la palette et les typographies du design system
perso (`mattrix2211/design-system`) : fond navy `#0B1929`, cartes ocean
`#0F2942`/bordures slate `#1A3A52`, accent signal unique `#00B4D8`,
Space Grotesk pour les titres, Inter pour le corps, JetBrains Mono pour les
valeurs numeriques (volts, valeurs d'encodeurs...), Material Icons pour
les icones d'emplacement. Contexte "Outils perso" : pas de couleur ember
(reservee au sport), statuts en green-tech.

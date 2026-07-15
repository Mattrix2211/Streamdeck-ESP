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

Tout se regle dans l'appli PC (`http://127.0.0.1:8080`), en 3 pages pour
eviter la surcharge (esprit "gerer ses pages d'applications sur un
telephone") :
- **Accueil** (`/`) : maquette fidele de l'ecran (memes proportions et
  disposition que le firmware) avec les 16 emplacements
  (bouton/barre/texte, icone, action) - les emplacements masques sont a
  part sous la maquette, glisser-deposer pour reordonner/echanger dans les
  deux sections - la seule page du quotidien.
- **Encodeurs** (`/encodeurs`) : action des 3 encodeurs.
- **Reglages** (`/reglages`) : connexion, forme carre/rond, Home
  Assistant - demandee automatiquement au tout premier lancement
  (`dashboard_config.yaml` est cree vide par `tray.py`, plus besoin de
  copier un fichier `.example` a la main), puis rarement revisitee.

Un seul clic ("Enregistrer et envoyer a l'ecran") sauvegarde et pousse les
changements de la page courante (chaque page ne touche que sa portion de
`dashboard_config.yaml`, jamais les autres).

- `device_client.py` maintient une connexion permanente et directe a
  l'ecran (IP configuree une fois, pas de mDNS) : elle ecoute les
  emplacements/encodeurs ET sert a pousser leur config (libelle, icone,
  type, visibilite, valeur des widgets) - meme connexion, pas de
  reconnexion a chaque changement.
- `dashboard.py` (+ `templates/base.html`+`home.html`+`settings.html`+
  `encoders.html`, `static/dashboard.js`) sont les 3 pages web (thread
  Flask separe), qui communiquent avec `device_client.py` via
  `asyncio.run_coroutine_threadsafe` pour
  rester thread-safe.
- `ha_client.py`/`ha_poller.py` sondent l'API REST de Home Assistant
  (facultatif) toutes les ~15s pour rafraichir les emplacements type
  widget, et executent le type d'action `home_assistant` (appel de
  service).
- `icons.py` : catalogue d'icones (glyphes Material Icons, memes
  points de code que la police `font_icons` du firmware).
- `tray.py` orchestre le tout (connexion, dashboard, sondeur HA) dans une
  icone de barre des taches, sans fenetre de terminal.
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
  pousse libelle/icone/type/visibilite de chaque emplacement + la forme.
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

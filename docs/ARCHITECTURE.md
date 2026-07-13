# Architecture

```
                         +-------------------------+
                         |  Stream Deck (ESP32-P4)  |
                         |  ESPHome + LVGL          |
                         |  - ecran tactile 1024x600|
                         |  - 3 encodeurs rotatifs   |
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
     |   (aioesphomeapi,       |                    |   (aioesphomeapi,      |
     |    integration native)  |                    |    streamdeck_companion)|
     +--------------------------+                    +-------------------------+
                                                                 |
                                                        actions locales :
                                                        raccourcis clavier,
                                                        lancement d'applis,
                                                        media/volume
```

## Pourquoi une seule API pour PC et Home Assistant

Home Assistant et l'appli PC parlent tous les deux le meme protocole natif
ESPHome (chiffre via une cle Noise partagee, `firmware/secrets.yaml` /
`pc-app/config.yaml`). Consequences :

- Un seul port a ouvrir/securiser (6053), pas de serveur HTTP additionnel
  sur l'appareil.
- Les entites (boutons, encodeurs, statut) sont definies une seule fois
  dans `firmware/streamdeck.yaml` et vues de la meme facon des deux cotes.
- L'appli PC peut evoluer independamment de Home Assistant (elle n'a pas
  besoin d'un serveur HA pour fonctionner - connexion directe au Stream Deck).

## Flux "bouton -> PC"

1. L'utilisateur touche un bouton sur l'ecran (LVGL) ou tourne un encodeur.
2. Le firmware declenche une entite `event:` (`event.trigger`).
3. L'appli PC recoit l'etat via `subscribe_states()`, retrouve l'action
   mappee dans `pc-app/config.yaml` et l'execute localement
   (`streamdeck_companion/actions.py`).
4. En parallele, Home Assistant peut ecouter la meme entite `event:` pour
   declencher ses propres automations (`home-assistant/example_automations.yaml`).

## Flux "PC -> ecran"

1. L'appli PC appelle `client.text_command(key, texte)` sur l'entite `text:`
   `pc_status_text`.
2. Le firmware met a jour le label LVGL correspondant (`on_value` de
   `text.pc_status_text`).
3. Home Assistant peut faire la meme chose via le service
   `text.set_value` (voir `home-assistant/example_automations.yaml`), pour
   afficher n'importe quelle information HA sur l'ecran.

## Design

L'interface LVGL reprend la palette et les typographies du design system
perso (`mattrix2211/design-system`) : fond navy `#0B1929`, cartes ocean
`#0F2942`/bordures slate `#1A3A52`, accent signal unique `#00B4D8`,
Space Grotesk pour les titres, Inter pour le corps, JetBrains Mono pour les
valeurs numeriques (volts, valeurs d'encodeurs...). Contexte "Outils perso" :
pas de couleur ember (reservee au sport), statuts en green-tech.

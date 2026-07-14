# Architecture

```
                         +-------------------------+
                         |  Stream Deck (ESP32-P4)  |
                         |  ESPHome + LVGL          |
                         |  - ecran tactile 1024x600|
                         |  - 12 boutons + 3 encodeurs|
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
     +--------------------------+                    +------------+------------+
                                                                    |
                                                       dashboard.py (page de
                                                       config visuelle,
                                                       port 8080) + tray.py
                                                       (icone barre des taches)
                                                                    |
                                                       actions locales :
                                                       raccourcis clavier,
                                                       lancement d'appli/jeu,
                                                       media, url
```

## L'appli PC comme point de configuration unique

Tout se regle dans l'appli PC (page de configuration visuelle,
`http://127.0.0.1:8080`) : disposition des 12 boutons et 3 encodeurs, leurs
actions, leur apparence (libelles, forme carre/rond). Un seul clic
("Enregistrer et envoyer a l'ecran") sauvegarde et pousse les changements.

- `device_client.py` maintient une connexion permanente et directe a
  l'ecran (IP configuree une fois, pas de mDNS) : elle ecoute les
  boutons/encodeurs ET sert a pousser les libelles/la forme (meme
  connexion, pas de reconnexion a chaque changement).
- `dashboard.py` est la page web de configuration (thread Flask separe),
  qui communique avec `device_client.py` via `asyncio.run_coroutine_threadsafe`
  pour rester thread-safe.
- `tray.py` orchestre les deux dans une icone de barre des taches, sans
  fenetre de terminal.
- Home Assistant continue de voir l'appareil nativement (integration
  ESPHome auto-decouverte) et peut faire ses propres automations en
  parallele, mais ce n'est **pas necessaire** pour que le Stream Deck
  fonctionne avec le PC.

## Flux "bouton -> PC"

1. L'utilisateur touche un bouton sur l'ecran (LVGL) ou tourne un encodeur.
2. Le firmware declenche une entite `event:` (`event.trigger`).
3. `device_client.py` recoit l'etat via sa connexion permanente
   (`subscribe_states`), retrouve l'action configuree (bouton ou
   sens/appui d'encodeur) dans `dashboard_config.yaml` et l'execute
   localement (`streamdeck_companion/actions.py`).
4. En bonus, Home Assistant peut aussi ecouter la meme entite `event:`
   pour ses propres automations, independamment (voir
   `home-assistant/example_automations.yaml`).

## Flux "PC -> ecran"

- **Libelles des boutons + forme** : `dashboard.py` (page "Enregistrer et
  envoyer a l'ecran") appelle `device_client.schedule_push()`, qui pousse
  les nouveaux textes/la forme vers les entites `text.action_N_libelle` /
  `select.forme_des_boutons` en reutilisant la connexion deja ouverte.
- **Statut / info generique depuis Home Assistant** : HA peut aussi
  appeler directement le service `text.set_value` sur
  `text.streamdeck_statut_pc` (voir `home-assistant/example_automations.yaml`).

## Design

L'interface LVGL reprend la palette et les typographies du design system
perso (`mattrix2211/design-system`) : fond navy `#0B1929`, cartes ocean
`#0F2942`/bordures slate `#1A3A52`, accent signal unique `#00B4D8`,
Space Grotesk pour les titres, Inter pour le corps, JetBrains Mono pour les
valeurs numeriques (volts, valeurs d'encodeurs...). Contexte "Outils perso" :
pas de couleur ember (reservee au sport), statuts en green-tech.

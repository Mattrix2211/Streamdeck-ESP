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
                         +------------v-------------+
                         |     Home Assistant        |
                         |  (integration ESPHome      |
                         |   native + automatisations  |
                         |   visuelles)                |
                         +------------+---------------+
                                      |
                         appel REST (rest_command),
                         token partage
                                      |
                         +------------v-------------+
                         |  Recepteur PC (Python)    |
                         |  streamdeck_companion/     |
                         |  receiver.py + tray.py     |
                         +------------+---------------+
                                      |
                            actions locales : raccourcis
                            clavier, lancement d'appli/jeu,
                            media, url
```

## Home Assistant comme cerveau unique

Toute la configuration (quel bouton/encodeur declenche quelle action) se
fait dans Home Assistant : c'est lui qui garde la connexion a l'ecran
(integration ESPHome native, deja en place) et qui decide, via ses
automatisations - creables entierement dans son interface web, sans YAML a
ecrire pour chaque bouton - d'appeler le PC. Consequences :

- Le PC n'a plus besoin de se connecter au Stream Deck (fini les soucis
  d'IP/mDNS/port/cle API cote PC) : il attend juste que HA l'appelle.
- Un seul service `rest_command` a definir une fois dans `configuration.yaml`
  (`home-assistant/rest_command.yaml.snippet`) ; chaque automation
  (bouton/encodeur) l'appelle juste avec des donnees differentes.
- Le recepteur PC (`streamdeck_companion/receiver.py`) est minuscule :
  un seul endpoint HTTP protege par un token, qui execute l'action recue.

## Flux "bouton -> PC"

1. L'utilisateur touche un bouton sur l'ecran (LVGL) ou tourne un encodeur.
2. Le firmware declenche une entite `event:` (`event.trigger`).
3. Home Assistant recoit l'etat (entite `event.xxx`), une automation
   verifie le `event_type` et appelle `rest_command.streamdeck_pc_action`
   avec `{type, target}`.
4. Le recepteur PC recoit l'appel HTTP (`POST /run`, token verifie) et
   execute l'action localement (`streamdeck_companion/actions.py`).

## Flux "PC/HA -> ecran"

- **Statut / info generique** : Home Assistant appelle directement le
  service `text.set_value` sur l'entite `text.streamdeck_statut_pc` (voir
  `home-assistant/example_automations.yaml`) - aucun code PC necessaire.
- **Libelles des boutons** : la page "Personnaliser l'ecran" du recepteur PC
  (`streamdeck_companion/screen_labels.py`) se connecte ponctuellement a
  l'ecran (pas une connexion permanente) pour pousser les nouveaux textes
  vers les entites `text.action_N_libelle`, qui mettent a jour les boutons
  LVGL correspondants (`on_value` -> `lvgl.button.update`).

## Design

L'interface LVGL reprend la palette et les typographies du design system
perso (`mattrix2211/design-system`) : fond navy `#0B1929`, cartes ocean
`#0F2942`/bordures slate `#1A3A52`, accent signal unique `#00B4D8`,
Space Grotesk pour les titres, Inter pour le corps, JetBrains Mono pour les
valeurs numeriques (volts, valeurs d'encodeurs...). Contexte "Outils perso" :
pas de couleur ember (reservee au sport), statuts en green-tech.

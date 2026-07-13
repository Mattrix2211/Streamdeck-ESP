# Stream Deck maison (ESP32-P4/C6 + encodeurs)

Firmware et outils pour transformer un ecran tactile Guition JC1060P470C_I_W
(7", 1024x600, ESP32-P4 + ESP32-C6) et des encodeurs rotatifs en Stream Deck
maison, pilotable a la fois depuis un PC et depuis Home Assistant.

## Structure du repo

```
firmware/          Config ESPHome (ecran, tactile, encodeurs, API native)
pc-app/            Appli compagnon Python (raccourcis, media, lancement d'applis)
home-assistant/    Exemples d'automations
docs/              Architecture et guide de cablage des encodeurs
```

## Demarrage rapide

1. **Firmware**
   ```bash
   cd firmware
   cp secrets.yaml.example secrets.yaml   # remplir wifi + generer une cle API
   pip install esphome
   esphome run streamdeck.yaml
   ```
2. **Appli PC** : voir `pc-app/README.md`.
3. **Home Assistant** : l'appareil est decouvert automatiquement (integration
   ESPHome native, meme cle API que dans `firmware/secrets.yaml`). Exemples
   d'automations dans `home-assistant/example_automations.yaml`.

Details d'architecture : `docs/ARCHITECTURE.md`. Cablage des encodeurs et
mapping des GPIO : `docs/WIRING.md`.

## Materiel

- Ecran Guition JC1060P470C_I_W (ESP32-P4 + ESP32-C6, tactile GT911)
- 3 encodeurs rotatifs (type KY-040) par defaut, ajustable dans le firmware
  et `docs/WIRING.md`

## Design

L'interface reprend le design system personnel
[`mattrix2211/design-system`](https://github.com/mattrix2211/design-system) :
palette dark-first (fond navy, accent signal `#00B4D8`), Space Grotesk /
Inter / JetBrains Mono, logo requin-marteau sur l'ecran d'accueil.

## A propos de `ruflo`

Le meta-framework d'orchestration multi-agents
[`ruvnet/ruflo`](https://github.com/ruvnet/ruflo) a ete initialise dans ce
depot a la demande explicite du proprietaire (`npx ruflo init`, dossiers
`.claude/`, `.claude-flow/`, `CLAUDE.md`, `.mcp.json`). Le developpement de ce
projet a ete fait directement, sans passer par son systeme de swarm/agents
(inutile pour un firmware ESPHome + un script Python). Ses hooks
(`.claude/settings.json`) interceptent chaque appel Bash/Write/Edit d'un
futur assistant sur ce depot et injectent parfois une pub pour un service
tiers ("sponsored capacity") - a desactiver si non souhaite.

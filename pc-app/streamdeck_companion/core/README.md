# Streamdeck Core

This package is the framework-independent domain layer introduced for Streamdeck-ESP V2.

## Dependency rule

Code in `core/` must not import Flask, Windows APIs, Home Assistant clients, ESPHome/aioesphomeapi, MQTT, GUI frameworks, or hardware-specific modules.

## Current foundation

- `ActionDefinition`: metadata and validation contract for an action type.
- `ActionCommand`: configured action instance.
- `ActionRegistry`: extension point used to register action definitions.
- `Trigger`: generic button/encoder interaction vocabulary.
- `ActionState`: generic synchronized state vocabulary.
- `legacy`: reversible adapter for the current `{type, target}` configuration shape.

Concrete execution remains in the existing application modules for now. The V2 migration will move those implementations behind adapters/providers incrementally, keeping the current dashboard config and firmware compatible.

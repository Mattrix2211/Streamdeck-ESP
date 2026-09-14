# Streamdeck Core

This package is the framework-independent domain layer introduced for Streamdeck-ESP V2.

## Dependency rule

Code in `core/` must not import Flask, Windows APIs, Home Assistant clients, ESPHome/aioesphomeapi, MQTT, GUI frameworks, or hardware-specific modules.

## Current foundation

- `ActionDefinition`: metadata and validation contract for an action type.
- `ActionCommand`: configured action instance.
- `ActionRegistry`: extension point used to register action definitions.
- `ActionEngine`: validates commands and delegates concrete effects to injected executors.
- `Trigger`: generic button/encoder interaction vocabulary.
- `InputEvent` / `TriggerBindings`: generic event-to-action resolution independent from ESPHome event names.
- `ActionState` / `StateStore`: centralized state vocabulary and observable state storage.
- `Profile` / `Page` / `Folder`: stable navigation model for multi-page profiles and nested folders.
- `GridRect` / `Placement`: hardware-independent layout primitives compatible with the current grid approach.
- `ProtocolMessage` / `MessageType`: versioned, transport-neutral PC↔device message envelope.
- `RetryPolicy` / `RequestTracker`: ACK/ERROR correlation, timeout and retry tracking independent from the transport.
- `legacy`: reversible adapter for the current `{type, target}` configuration shape.

## Migration rule

Concrete integrations remain outside `core/`. Existing modules are migrated by registering adapters/executors rather than moving Windows, Home Assistant or hardware code into the domain layer.

The historical dashboard configuration and ESPHome transport remain compatible while this migration is in progress. `streamdeck_companion/actions.py` is the first runtime path routed through `ActionEngine`; Home Assistant and device-specific action paths will follow progressively.

`device_events.py` translates the current ESPHome event vocabulary to generic Core input events. `device_protocol.py` can then project those generic events into the V2 protocol without forcing an immediate firmware rewrite.

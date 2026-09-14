"""Tests for resolving existing profile actions from generic input events."""

import unittest

from streamdeck_companion.core import InputEvent, InputKind, Trigger
from streamdeck_companion.event_resolution import resolve_legacy_action


class EventResolutionTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "slots": [
                {"library_id": "one", "visible": True},
                {"library_id": None, "visible": False},
            ],
            "library": [
                {
                    "id": "one",
                    "type": "bouton",
                    "action": {"type": "url", "target": "https://example.com"},
                }
            ],
            "encoders": [
                {
                    "clockwise": {"type": "media", "target": "vol_up"},
                    "anticlockwise": {"type": "media", "target": "vol_down"},
                    "press": {"type": "media", "target": "mute"},
                }
            ],
        }

    def test_button_press_resolves_existing_slot_action(self):
        event = InputEvent(
            "button:1",
            InputKind.BUTTON,
            Trigger.PRESS,
            {"slot_index": 0},
        )
        self.assertEqual(
            resolve_legacy_action(self.profile, event),
            {"type": "url", "target": "https://example.com"},
        )

    def test_encoder_rotation_resolves_existing_direction(self):
        event = InputEvent(
            "encoder:1",
            InputKind.ENCODER,
            Trigger.ROTATE_CW,
            {"encoder_index": 0},
        )
        self.assertEqual(
            resolve_legacy_action(self.profile, event),
            {"type": "media", "target": "vol_up"},
        )

    def test_encoder_press_resolves_existing_press_action(self):
        event = InputEvent(
            "encoder:1",
            InputKind.ENCODER,
            Trigger.PRESS,
            {"encoder_index": 0},
        )
        self.assertEqual(
            resolve_legacy_action(self.profile, event),
            {"type": "media", "target": "mute"},
        )

    def test_invalid_metadata_is_ignored(self):
        event = InputEvent("button:x", InputKind.BUTTON, Trigger.PRESS, {})
        self.assertIsNone(resolve_legacy_action(self.profile, event))

    def test_touch_event_has_no_legacy_action_yet(self):
        event = InputEvent("touch:1", InputKind.TOUCH, Trigger.PRESS, {})
        self.assertIsNone(resolve_legacy_action(self.profile, event))


if __name__ == "__main__":
    unittest.main()

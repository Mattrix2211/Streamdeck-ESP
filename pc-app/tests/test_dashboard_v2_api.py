from __future__ import annotations

import unittest

from streamdeck_companion.dashboard_v2_api import (
    dashboard_action_catalog_payload,
    dashboard_action_context,
)


class DashboardV2ApiTests(unittest.TestCase):
    def test_context_is_derived_from_v2_catalog(self) -> None:
        context = dashboard_action_context()
        self.assertIn("navigation", context["action_types"])
        self.assertIn("multi_action", context["action_types"])
        self.assertIn("ha_adjust", context["encoder_action_types"])
        self.assertEqual(context["action_type_labels"]["none"], "Aucune")

    def test_payload_exposes_property_inspector_and_context_choices(self) -> None:
        payload = dashboard_action_catalog_payload()
        actions = {action["id"]: action for action in payload["actions"]}
        self.assertIn("navigation", actions)
        self.assertIn("multi_action", actions)
        self.assertIn("fields", actions["navigation"])
        self.assertTrue(payload["choices"]["button"])
        self.assertTrue(payload["choices"]["encoder"])


if __name__ == "__main__":
    unittest.main()

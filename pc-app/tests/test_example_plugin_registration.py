import unittest

from streamdeck_companion.core.plugins import PluginPermission, PluginRegistry
from streamdeck_companion.core.registry import ActionRegistry
from streamdeck_companion.example_plugins import home_assistant_plugin, obs_plugin, system_plugin


class ExamplePluginRegistrationTests(unittest.TestCase):
    def test_examples_register_together(self):
        registry = PluginRegistry(
            ActionRegistry(),
            granted_permissions=frozenset(
                {
                    PluginPermission.NETWORK,
                    PluginPermission.PROCESS,
                    PluginPermission.HOME_ASSISTANT,
                    PluginPermission.AUDIO,
                }
            ),
        )
        for factory in (system_plugin, home_assistant_plugin, obs_plugin):
            manifest, contribution = factory()
            registry.register(manifest, contribution)
        self.assertEqual(len(registry.list()), 3)
        self.assertEqual(registry.event_owner("obs.scene_changed"), "obs")
        self.assertEqual(registry.event_owner("home_assistant.state_changed"), "home_assistant")


if __name__ == "__main__":
    unittest.main()

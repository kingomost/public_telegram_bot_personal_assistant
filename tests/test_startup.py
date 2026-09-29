import importlib
import unittest


class StartupTests(unittest.TestCase):
    def test_application_modules_import(self) -> None:
        for module in (
            "main",
            "content",
            "keyboards",
            "endpoints",
            "endpoints.dashboard",
            "services.habits",
            "services.rituals",
            "services.heartbeat",
        ):
            with self.subTest(module=module):
                importlib.import_module(module)

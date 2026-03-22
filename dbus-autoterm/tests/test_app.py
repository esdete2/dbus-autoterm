import argparse
import tempfile
import unittest
from pathlib import Path

from app import (
    _build_runtime_config,
    _config_get,
    _config_getboolean,
    _config_getfloat,
    _config_getint,
    _load_config,
)


def _args(**overrides):
    values = {
        "backend": "dummy",
        "serial_device": None,
        "poll_interval": 1.0,
        "service_name": None,
        "device_instance": None,
        "product_name": None,
        "firmware_version": None,
        "hardware_version": None,
        "connection": None,
        "mock_dbus": False,
        "log_level": "INFO",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AppConfigTests(unittest.TestCase):
    def test_load_config_and_read_typed_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[driver]",
                        "backend = serial",
                        "poll_interval = 2.5",
                        "mock_dbus = true",
                        "",
                        "[dbus]",
                        "device_instance = 321",
                    ]
                ),
                encoding="utf-8",
            )
            config = _load_config(config_path)

        self.assertEqual(_config_get(config, "driver", "backend", "dummy"), "serial")
        self.assertEqual(_config_getfloat(config, "driver", "poll_interval", 1.0), 2.5)
        self.assertTrue(_config_getboolean(config, "driver", "mock_dbus", False))
        self.assertEqual(_config_getint(config, "dbus", "device_instance", 0), 321)

    def test_runtime_config_uses_file_values_when_cli_keeps_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[driver]",
                        "backend = serial",
                        "serial_device = /dev/ttyS1",
                        "poll_interval = 2.5",
                        "mock_dbus = true",
                        "log_level = DEBUG",
                        "",
                        "[dbus]",
                        "service_name = com.victronenergy.generator.autoterm_custom",
                        "device_instance = 321",
                        "product_name = Test Product",
                    ]
                ),
                encoding="utf-8",
            )
            config = _load_config(config_path)

        runtime = _build_runtime_config(_args(), [], config)
        self.assertEqual(runtime.backend, "serial")
        self.assertEqual(runtime.serial_device, "/dev/ttyS1")
        self.assertEqual(runtime.poll_interval, 2.5)
        self.assertTrue(runtime.mock_dbus)
        self.assertEqual(runtime.log_level, "DEBUG")
        self.assertEqual(runtime.driver_config.service_name, "com.victronenergy.generator.autoterm_custom")
        self.assertEqual(runtime.driver_config.device_instance, 321)
        self.assertEqual(runtime.driver_config.product_name, "Test Product")

    def test_runtime_config_prefers_explicit_cli_over_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[driver]",
                        "backend = serial",
                        "poll_interval = 5.0",
                        "",
                        "[dbus]",
                        "device_instance = 321",
                    ]
                ),
                encoding="utf-8",
            )
            config = _load_config(config_path)

        runtime = _build_runtime_config(
            _args(backend="dummy", poll_interval=1.25, log_level="WARNING", device_instance=42),
            ["--backend", "dummy", "--poll-interval", "1.25", "--log-level", "WARNING"],
            config,
        )
        self.assertEqual(runtime.backend, "dummy")
        self.assertEqual(runtime.poll_interval, 1.25)
        self.assertEqual(runtime.log_level, "WARNING")
        self.assertEqual(runtime.driver_config.device_instance, 42)


if __name__ == "__main__":
    unittest.main()

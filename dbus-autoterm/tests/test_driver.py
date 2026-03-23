import unittest

from app import HeaterDriverApp
from domain import OperatingMode
from gx_dbus import DriverConfig, GeneratorDbusAdapter, MockVeDbusService
from provider import DummyHeaterProvider


class DriverTests(unittest.TestCase):
    def _build_app(self):
        provider = DummyHeaterProvider()
        provider.connect()
        service = MockVeDbusService("com.victronenergy.genset.autoterm_air2d")
        adapter = GeneratorDbusAdapter(config=DriverConfig(), service=service)
        app = HeaterDriverApp(provider, adapter)
        adapter._on_startstop = app.startstop
        adapter._on_mode_change = app.update_mode
        adapter._on_target_temperature_change = app.update_target_temperature
        adapter._on_power_level_change = app.update_power_level
        return provider, service, app

    def test_dummy_provider_updates_mock_dbus(self):
        _, service, app = self._build_app()

        app.run_once()
        self.assertEqual(service["/Connected"], 1)
        self.assertEqual(service["/Alarms/Communication"], 0)
        self.assertEqual(service["/State"], 0)
        self.assertEqual(service["/StatusCode"], 0)
        self.assertEqual(service["/StatusCodeMajor"], 0)
        self.assertEqual(service["/StatusCodeMinor"], 1)
        self.assertEqual(service["/Role"], "genset")
        self.assertEqual(service["/NrOfPhases"], 1)

    def test_startstop_callback_updates_state(self):
        _, service, app = self._build_app()

        service.set_value("/StartStop", 1)
        self.assertEqual(service["/StartStop"], 1)
        self.assertGreater(service["/StatusCode"], 0)
        self.assertEqual(service["/Alarms/Communication"], 0)

        service.set_value("/StartStop", 0)
        self.assertEqual(service["/StartStop"], 0)

    def test_disconnected_provider_maps_to_communication_alarm(self):
        provider, service, app = self._build_app()
        provider.close()

        app.run_once()
        self.assertEqual(service["/Connected"], 0)
        self.assertEqual(service["/Alarms/Communication"], 2)

    def test_settings_callbacks_propagate_to_provider_snapshot(self):
        _, service, app = self._build_app()

        service.set_value("/Settings/Mode", int(OperatingMode.EXTERNAL_TEMPERATURE))
        service.set_value("/Settings/TargetTemperature", 21)
        service.set_value("/Settings/PowerLevel", 5)

        app.run_once()
        self.assertEqual(service["/Settings/Mode"], int(OperatingMode.EXTERNAL_TEMPERATURE))
        self.assertEqual(service["/Settings/TargetTemperature"], 21)
        self.assertEqual(service["/Settings/PowerLevel"], 5)

    def test_running_snapshot_exports_genset_ac_metrics(self):
        _, service, app = self._build_app()

        service.set_value("/StartStop", 1)
        app.run_once()

        self.assertEqual(service["/RemoteStartModeEnabled"], 1)
        self.assertEqual(service["/Ac/Frequency"], 50.0)
        self.assertGreater(service["/Ac/Power"], 0)
        self.assertGreater(service["/Ac/L1/Voltage"], 0.0)
        self.assertGreater(service["/Ac/L1/Current"], 0.0)


if __name__ == "__main__":
    unittest.main()

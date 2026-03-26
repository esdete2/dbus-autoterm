import unittest

from app import HeaterDriverApp
from domain import HeaterPhase
from gx_dbus import DriverConfig, HeaterDbusAdapter, MockVeDbusService
from protocol import CONTROLLER_PROFILE, Frame
from provider import DummyHeaterProvider, SerialHeaterProvider, SerialProviderConfig
from room_sensor import RoomTemperatureReading


class DriverTests(unittest.TestCase):
    def _build_app(self, room_temperature_reader=None):
        provider = DummyHeaterProvider()
        provider.connect()
        service = MockVeDbusService("com.victronenergy.heater.autoterm_air2d")
        adapter = HeaterDbusAdapter(config=DriverConfig(), service=service)
        app = HeaterDriverApp(provider, adapter, room_temperature_reader=room_temperature_reader)
        adapter._on_startstop = app.startstop
        adapter._on_mode_change = app.update_mode
        adapter._on_target_temperature_change = app.update_target_temperature
        adapter._on_power_level_change = app.update_power_level
        adapter._on_room_temperature_service_change = app.update_room_temperature_service
        return provider, service, app

    def test_dummy_provider_updates_mock_dbus(self):
        _, service, app = self._build_app()

        app.run_once()
        self.assertEqual(service["/Connected"], 1)
        self.assertEqual(service["/State"], 0)
        self.assertEqual(service["/StateText"], "off")
        self.assertEqual(service["/Role"], "heater")
        self.assertEqual(service["/ModeText"], "Power")
        self.assertEqual(service["/Capabilities/RoomTemperatureControl"], 0)
        self.assertIsNone(service["/Temperatures/Room"])
        self.assertEqual(service["/Timers/0/Enabled"], 0)
        self.assertEqual(service["/Timers/2/Mode"], 1)

    def test_startstop_callback_updates_state(self):
        _, service, _ = self._build_app()

        service.set_value("/StartStop", 1)
        self.assertEqual(service["/StartStop"], 1)
        self.assertIn(service["/State"], {1, 2, 3})
        self.assertEqual(service["/Alarms/Communication"], 0)

        service.set_value("/StartStop", 0)
        self.assertEqual(service["/StartStop"], 0)

    def test_disconnected_provider_maps_to_communication_alarm(self):
        provider, service, app = self._build_app()
        provider.close()

        app.run_once()
        self.assertEqual(service["/Connected"], 0)
        self.assertEqual(service["/Alarms/Communication"], 2)
        self.assertEqual(service["/ErrorText"], "Communication error")

    def test_settings_callbacks_propagate_to_provider_snapshot(self):
        _, service, app = self._build_app()

        service.set_value("/Settings/TargetTemperature", 21)
        service.set_value("/Settings/PowerLevel", 5)

        app.run_once()
        self.assertEqual(service["/Mode"], 0)
        self.assertEqual(service["/Settings/TargetTemperature"], 21)
        self.assertEqual(service["/Settings/PowerLevel"], 5)

    def test_runtime_exports_live_metrics(self):
        _, service, app = self._build_app()

        service.set_value("/StartStop", 1)
        app.run_once()

        self.assertGreaterEqual(service["/Status/FanRpmActual"], 0)
        self.assertIsNone(service["/Temperatures/Control"])
        self.assertGreater(service["/Dc/0/Voltage"], 0.0)

    def test_external_room_sensor_enables_temperature_control(self):
        provider, service, app = self._build_app()
        provider._snapshot.telemetry.external_temperature_c = 18

        app.run_once()
        service.set_value("/Mode", 1)
        app.run_once()

        self.assertEqual(service["/Capabilities/RoomTemperatureControl"], 1)
        self.assertEqual(service["/Temperatures/Room"], 18)
        self.assertEqual(service["/Temperatures/RoomSourceText"], "Heater external sensor")
        self.assertEqual(service["/Mode"], 1)

    def test_cerbo_room_sensor_enables_temperature_control(self):
        class _Reader:
            selected_service = "auto"

            def refresh(self):
                return RoomTemperatureReading(
                    temperature_c=20.5,
                    source_text="Salon",
                    service_name="com.victronenergy.temperature.ttyO1",
                )

            def available_services(self):
                return []

            def set_selected_service(self, service_name: str):
                self.selected_service = service_name

        _, service, app = self._build_app(room_temperature_reader=_Reader())

        app.run_once()
        service.set_value("/Mode", 1)
        app.run_once()

        self.assertEqual(service["/Capabilities/RoomTemperatureControl"], 1)
        self.assertEqual(service["/Capabilities/CerboRoomSensor"], 1)
        self.assertEqual(service["/Temperatures/Room"], 20.5)
        self.assertEqual(service["/Temperatures/RoomSourceText"], "Salon")
        self.assertEqual(service["/Mode"], 1)

    def test_room_temperature_service_selection_round_trips(self):
        class _Reader:
            def __init__(self):
                self.selected_service = "auto"

            def refresh(self):
                return RoomTemperatureReading()

            def available_services(self):
                from room_sensor import RoomTemperatureServiceInfo

                return [
                    RoomTemperatureServiceInfo(
                        service_name="com.victronenergy.temperature.ttyO1",
                        display_name="Salon",
                        temperature_c=21.0,
                    )
                ]

            def set_selected_service(self, service_name: str):
                self.selected_service = service_name

        reader = _Reader()
        _, service, app = self._build_app(room_temperature_reader=reader)

        app.run_once()
        service.set_value("/Settings/RoomTemperatureService", "com.victronenergy.temperature.ttyO1")

        self.assertEqual(reader.selected_service, "com.victronenergy.temperature.ttyO1")
        self.assertEqual(service["/Settings/RoomTemperatureService"], "com.victronenergy.temperature.ttyO1")
        self.assertEqual(service["/Settings/RoomTemperatureServiceText"], "Salon")

    def test_temperature_mode_is_rejected_without_room_sensor(self):
        _, service, app = self._build_app()

        app.run_once()
        service.set_value("/Mode", 1)

        self.assertEqual(service["/Mode"], 0)

    def test_ventilation_mode_uses_primary_heater_contract(self):
        _, service, app = self._build_app()

        service.set_value("/Mode", 2)
        service.set_value("/Settings/PowerLevel", 4)
        service.set_value("/StartStop", 1)
        app.run_once()

        self.assertEqual(service["/ModeText"], "Ventilation")
        self.assertIn(service["/StateText"], {"starting ventilation", "ventilation"})
        self.assertEqual(service["/Status/FuelPumpFrequency"], 0.0)

    def test_timer_paths_round_trip(self):
        _, service, _ = self._build_app()

        service.set_value("/Timers/1/Enabled", 1)
        service.set_value("/Timers/1/StartHour", 22)
        service.set_value("/Timers/1/DurationMinutes", 90)

        self.assertEqual(service["/Timers/1/Enabled"], 1)
        self.assertEqual(service["/Timers/1/StartHour"], 22)
        self.assertEqual(service["/Timers/1/DurationMinutes"], 90)

    def test_startstop_transitions_back_to_off(self):
        provider, service, app = self._build_app()

        service.set_value("/StartStop", 1)
        app.run_once()
        service.set_value("/StartStop", 0)
        provider._set_phase(HeaterPhase.OFF)
        app.run_once()

        self.assertEqual(service["/State"], 0)
        self.assertEqual(service["/StartStop"], 0)

    def test_serial_provider_ignores_echoed_settings_request_frame(self):
        provider = SerialHeaterProvider(SerialProviderConfig(device="/dev/null", profile=CONTROLLER_PROFILE), stream=object())
        request = Frame(device=CONTROLLER_PROFILE.controller_device, message_id2=0x02)
        echoed_request = Frame(device=CONTROLLER_PROFILE.controller_device, message_id2=0x02)
        heater_response = Frame(device=CONTROLLER_PROFILE.heater_device, message_id2=0x02, payload=b"\x01\x00\x04\x0f\x00\x02")

        self.assertFalse(provider._matches_response(request, echoed_request))
        self.assertTrue(provider._matches_response(request, heater_response))


if __name__ == "__main__":
    unittest.main()

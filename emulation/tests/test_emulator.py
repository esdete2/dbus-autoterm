import unittest

from controller import (
    MSG_SETTINGS,
    MSG_START,
    build_init_frame,
    build_serial_request_frame,
    build_start_frame,
    build_status_request_frame,
    build_stop_frame,
    build_ventilation_frame,
    build_version_request_frame,
)
from domain import HeaterPhase, HeaterSettings, OperatingMode
from emulator import EmulatorConfig, FakeAir2DHeater
from protocol import Frame


class EmulatorTests(unittest.TestCase):
    def test_start_and_status_round_trip(self):
        heater = FakeAir2DHeater()
        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=15,
            wait_mode=0,
            power_level=2,
        )
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        response = heater.handle_frame(build_start_frame(0x03, settings))[0]
        self.assertEqual(response.message_id2, 0x01)
        self.assertEqual(heater.snapshot.phase, HeaterPhase.STARTING)
        self.assertEqual(response.payload, bytes.fromhex("0100040F0002"))

        status = heater.handle_frame(build_status_request_frame(0x03))[0]
        self.assertEqual(status.message_id2, 0x0F)
        self.assertEqual(len(status.payload), 19)
        self.assertEqual(status.payload[0], 0x02)
        self.assertEqual(status.payload[1], 0x01)
        self.assertEqual(status.payload[8], heater.snapshot.telemetry.heater_temperature_c + 15)

    def test_shutdown_transitions_to_off(self):
        heater = FakeAir2DHeater(EmulatorConfig(shutdown_to_off_s=0))
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        heater.snapshot.phase = HeaterPhase.RUNNING
        heater.handle_frame(build_stop_frame(0x03))
        heater.tick()
        heater.tick()
        self.assertEqual(heater.snapshot.phase, HeaterPhase.OFF)

    def test_initial_fault_injection_is_reflected_in_status(self):
        heater = FakeAir2DHeater(
            EmulatorConfig(
                initial_error_code=30,
                initial_internal_temperature_c=24,
                initial_status_code_major=3,
                initial_status_code_minor=35,
            )
        )
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        status = heater.handle_frame(build_status_request_frame(0x03))[0]
        self.assertEqual(status.payload[0:3], bytes([3, 35, 30]))
        self.assertEqual(status.payload[3], 24)

    def test_start_is_ignored_until_startup_sequence_completed(self):
        heater = FakeAir2DHeater()
        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=15,
            wait_mode=0,
            power_level=2,
        )
        responses = heater.handle_frame(build_start_frame(0x03, settings))
        self.assertEqual(responses, [])
        self.assertEqual(heater.snapshot.phase, HeaterPhase.OFF)

    def test_background_status_is_emitted_after_startup(self):
        heater = FakeAir2DHeater(EmulatorConfig(status_broadcast_interval_s=0.5))
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        frames = heater.background_frames(now=heater._last_status_broadcast + 0.6)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].message_id2, 0x0F)
        self.assertEqual(len(frames[0].payload), 19)

    def test_startup_sequence_is_order_sensitive(self):
        heater = FakeAir2DHeater()
        self.assertEqual(heater.handle_frame(build_version_request_frame(0x03)), [])
        self.assertEqual(heater.handle_frame(build_init_frame(0x03))[0].message_id2, 0x1C)
        self.assertEqual(heater.handle_frame(build_version_request_frame(0x03)), [])
        self.assertEqual(heater.handle_frame(build_serial_request_frame(0x03))[0].message_id2, 0x04)
        self.assertEqual(heater.handle_frame(build_version_request_frame(0x03))[0].message_id2, 0x06)

    def test_malformed_start_payload_is_ignored(self):
        heater = FakeAir2DHeater()
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        responses = heater.handle_frame(Frame(device=0x03, message_id2=MSG_START, payload=b"\x01"))
        self.assertEqual(responses, [])
        self.assertEqual(heater.snapshot.phase, HeaterPhase.OFF)

    def test_malformed_settings_payload_is_ignored(self):
        heater = FakeAir2DHeater()
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        responses = heater.handle_frame(Frame(device=0x03, message_id2=MSG_SETTINGS, payload=b"\x01\x02"))
        self.assertEqual(responses, [])
        self.assertEqual(heater.snapshot.settings.power_level, 2)

    def test_runtime_progression_tracks_elapsed_time(self):
        heater = FakeAir2DHeater(
            EmulatorConfig(start_to_warmup_s=1.0, warmup_to_run_s=1.0, shutdown_to_off_s=1.0)
        )
        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=15,
            wait_mode=0,
            power_level=2,
        )
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        heater.handle_frame(build_start_frame(0x03, settings))

        start_anchor = heater._runtime_anchor
        self.assertIsNotNone(start_anchor)
        heater.tick(now=start_anchor + 0.5)
        self.assertEqual(heater.snapshot.runtime_seconds, 0)
        heater.tick(now=start_anchor + 2.2)
        self.assertGreaterEqual(heater.snapshot.runtime_seconds, 2)
        self.assertIn(heater.snapshot.phase, {HeaterPhase.WARMING_UP, HeaterPhase.RUNNING})
        self.assertLess(heater.snapshot.telemetry.fan_rpm_set, 100)

    def test_duplicate_start_does_not_restart_state_machine(self):
        heater = FakeAir2DHeater()
        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=15,
            wait_mode=0,
            power_level=2,
        )
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        first_response = heater.handle_frame(build_start_frame(0x03, settings))[0]
        first_anchor = heater._runtime_anchor
        second_response = heater.handle_frame(build_start_frame(0x03, settings))[0]
        self.assertEqual(first_response.payload, second_response.payload)
        self.assertEqual(heater.snapshot.phase, HeaterPhase.STARTING)
        self.assertEqual(heater._runtime_anchor, first_anchor)

    def test_ventilation_transitions_to_only_fan_status(self):
        heater = FakeAir2DHeater()
        heater.handle_frame(build_init_frame(0x03))
        heater.handle_frame(build_serial_request_frame(0x03))
        heater.handle_frame(build_version_request_frame(0x03))
        response = heater.handle_frame(build_ventilation_frame(0x03, 2))[0]
        self.assertEqual(response.payload, bytes.fromhex("ffff0243"))
        self.assertEqual(heater.snapshot.telemetry.status_code_major, 1)
        self.assertEqual(heater.snapshot.telemetry.status_code_minor, 1)
        phase_anchor = heater._phase_since
        heater.tick(now=phase_anchor + 2.1)
        self.assertEqual(heater.snapshot.phase, HeaterPhase.RUNNING)
        self.assertEqual(heater.snapshot.telemetry.status_code_major, 3)
        self.assertEqual(heater.snapshot.telemetry.status_code_minor, 35)
        self.assertEqual(heater.snapshot.telemetry.fuel_pump_frequency_hz, 0.0)


if __name__ == "__main__":
    unittest.main()

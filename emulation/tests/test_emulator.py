import unittest

from controller import (
    build_init_frame,
    build_serial_request_frame,
    build_start_frame,
    build_status_request_frame,
    build_stop_frame,
    build_version_request_frame,
)
from domain import HeaterPhase, HeaterSettings, OperatingMode
from emulator import EmulatorConfig, FakeAir2DHeater


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


if __name__ == "__main__":
    unittest.main()

import unittest

from controller import (
    MSG_STATUS,
    build_start_frame,
    parse_settings_payload,
    parse_status_payload,
)
from domain import HeaterSettings, OperatingMode
from protocol import Frame, FrameParser, decode_frame, encode_frame


class ProtocolTests(unittest.TestCase):
    def test_crc_and_decode_status_request(self):
        packet = bytes.fromhex("AA0300000F587C")
        frame = decode_frame(packet)
        self.assertEqual(frame.device, 0x03)
        self.assertEqual(frame.message_id2, MSG_STATUS)
        self.assertEqual(frame.payload, b"")

    def test_encode_known_shutdown_request(self):
        packet = encode_frame(Frame(device=0x03, message_id2=0x03))
        self.assertEqual(packet.hex().upper(), "AA030000035D7C")

    def test_parse_settings_payload(self):
        settings = parse_settings_payload(bytes.fromhex("010004100008"))
        self.assertEqual(settings.mode, OperatingMode.POWER)
        self.assertEqual(settings.setpoint_c, 0x10)
        self.assertFalse(settings.use_work_time)
        self.assertEqual(settings.wait_mode, 0x00)
        self.assertEqual(settings.power_level, 0x08)

    def test_parse_status_payload_air2d_variant(self):
        status = parse_status_payload(bytes.fromhex("000100137F0086012400000000000000000064"))
        self.assertEqual(int(status.phase), 0)
        self.assertEqual(status.status_code_major, 0)
        self.assertEqual(status.status_code_minor, 1)
        self.assertEqual(status.internal_temperature_c, 0x13)
        self.assertEqual(status.heater_temperature_c, 0x24 - 15)
        self.assertEqual(status.external_temperature_c, None)
        self.assertAlmostEqual(status.battery_voltage_v, 13.4)
        self.assertEqual(status.fan_rpm_set, 0)
        self.assertEqual(status.fuel_pump_frequency_hz, 0.0)

    def test_encode_start_frame(self):
        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=0x0F,
            wait_mode=0x00,
            power_level=0x02,
        )
        packet = encode_frame(build_start_frame(0x03, settings))
        self.assertEqual(packet.hex().upper(), "AA030600010100040F0002725F")

    def test_frame_parser_recovers_from_corrupt_packet(self):
        parser = FrameParser()
        corrupt = bytes.fromhex("AA0300000F587D")
        valid = bytes.fromhex("AA0300000F587C")
        frames = parser.feed(corrupt + valid)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].message_id2, MSG_STATUS)


if __name__ == "__main__":
    unittest.main()

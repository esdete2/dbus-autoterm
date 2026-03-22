import unittest

from emulator import FakeAir2DHeater
from domain import HeaterPhase, HeaterSettings, OperatingMode
from protocol import decode_frame, encode_frame
from provider import SerialHeaterProvider, SerialProviderConfig


class LoopbackHeaterStream:
    def __init__(self) -> None:
        self._heater = FakeAir2DHeater()
        self._buffer = bytearray()

    def read(self, size: int, timeout: float) -> bytes:
        del timeout
        if not self._buffer:
            return b""
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def write(self, data: bytes) -> int:
        frame = decode_frame(data)
        for response in self._heater.handle_frame(frame):
            self._buffer.extend(encode_frame(response))
        return len(data)

    def close(self) -> None:
        self._buffer.clear()


class SerialProviderTests(unittest.TestCase):
    def test_provider_can_drive_emulator(self):
        stream = LoopbackHeaterStream()
        provider = SerialHeaterProvider(SerialProviderConfig(device="loopback"), stream=stream)
        provider.connect()

        settings = HeaterSettings(
            use_work_time=False,
            work_time_minutes=0,
            mode=OperatingMode.POWER,
            setpoint_c=15,
            wait_mode=0,
            power_level=2,
        )
        snapshot = provider.start(settings)
        self.assertIn(snapshot.phase, {HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING})
        self.assertEqual(snapshot.settings.power_level, 2)
        self.assertEqual(snapshot.telemetry.status_code_major, 2)

        snapshot = provider.stop()
        self.assertEqual(snapshot.phase, HeaterPhase.SHUTTING_DOWN)


if __name__ == "__main__":
    unittest.main()

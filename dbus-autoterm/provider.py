from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from controller import (
    MSG_SETTINGS,
    build_get_settings_frame,
    build_init_frame,
    build_panel_temperature_frame,
    build_serial_request_frame,
    build_settings_frame,
    build_start_frame,
    build_status_request_frame,
    build_stop_frame,
    build_version_request_frame,
    parse_settings_payload,
    parse_status_payload,
)
from domain import HeaterPhase, HeaterSettings, HeaterSnapshot, TransportHealth
from protocol import CONTROLLER_PROFILE, Frame, FrameParser, ProtocolProfile, encode_frame
from transports import ByteStream, SerialByteStream


class HeaterProvider(Protocol):
    def connect(self) -> None:
        ...

    def close(self) -> None:
        ...

    def get_snapshot(self) -> HeaterSnapshot:
        ...

    def get_health(self) -> TransportHealth:
        ...

    def refresh(self) -> HeaterSnapshot:
        ...

    def start(self, settings: HeaterSettings) -> HeaterSnapshot:
        ...

    def stop(self) -> HeaterSnapshot:
        ...

    def update_settings(self, settings: HeaterSettings) -> HeaterSnapshot:
        ...

    def report_panel_temperature(self, temperature_c: int) -> HeaterSnapshot:
        ...


@dataclass
class SerialProviderConfig:
    device: str
    profile: ProtocolProfile = CONTROLLER_PROFILE
    timeout_s: float = 1.0


class DummyHeaterProvider:
    # Dummy provider used for Cerbo-side UI and service validation before real heater transport is enabled.
    def __init__(self) -> None:
        self._snapshot = HeaterSnapshot()
        self._health = TransportHealth(connected=False, profile_name="dummy")
        self._phase_started_monotonic = time.monotonic()
        self._runtime_anchor_monotonic = time.monotonic()
        self._set_phase(HeaterPhase.OFF)

    def connect(self) -> None:
        self._health.connected = True
        self._snapshot.connected = True
        self._snapshot.last_update_monotonic = time.monotonic()

    def close(self) -> None:
        self._health.connected = False
        self._snapshot.connected = False
        self._snapshot.last_update_monotonic = time.monotonic()

    def get_snapshot(self) -> HeaterSnapshot:
        return self._snapshot

    def get_health(self) -> TransportHealth:
        return self._health

    def refresh(self) -> HeaterSnapshot:
        now = time.monotonic()
        phase_elapsed = now - self._phase_started_monotonic

        if self._snapshot.phase == HeaterPhase.STARTING and phase_elapsed >= 2.0:
            self._set_phase(HeaterPhase.WARMING_UP)
        elif self._snapshot.phase == HeaterPhase.WARMING_UP and phase_elapsed >= 5.0:
            self._set_phase(HeaterPhase.RUNNING)
        elif self._snapshot.phase == HeaterPhase.SHUTTING_DOWN and phase_elapsed >= 4.0:
            self._set_phase(HeaterPhase.OFF)

        if self._snapshot.phase == HeaterPhase.RUNNING:
            self._snapshot.runtime_seconds = int(max(0.0, now - self._runtime_anchor_monotonic))
            self._snapshot.telemetry.heater_temperature_c = min(
                75,
                40 + (self._snapshot.settings.power_level * 6) + min(self._snapshot.runtime_seconds, 12),
            )
            self._snapshot.telemetry.fan_rpm_set = 48 + (self._snapshot.settings.power_level * 8)
            self._snapshot.telemetry.fan_rpm_actual = max(0, self._snapshot.telemetry.fan_rpm_set - 2)
            self._snapshot.telemetry.fuel_pump_frequency_hz = round(0.32 + (self._snapshot.settings.power_level * 0.08), 2)
        self._snapshot.connected = self._health.connected
        self._snapshot.last_update_monotonic = now
        return self._snapshot

    def start(self, settings: HeaterSettings) -> HeaterSnapshot:
        self._snapshot.settings = settings
        self._snapshot.runtime_seconds = 0
        self._runtime_anchor_monotonic = time.monotonic()
        self._snapshot.telemetry.error_code = 0
        self._set_phase(HeaterPhase.STARTING)
        return self.refresh()

    def stop(self) -> HeaterSnapshot:
        if self._snapshot.phase == HeaterPhase.OFF:
            return self.refresh()
        self._set_phase(HeaterPhase.SHUTTING_DOWN)
        return self.refresh()

    def update_settings(self, settings: HeaterSettings) -> HeaterSnapshot:
        self._snapshot.settings = settings
        return self.refresh()

    def report_panel_temperature(self, temperature_c: int) -> HeaterSnapshot:
        self._snapshot.telemetry.controller_temperature_c = temperature_c
        return self.refresh()

    def _set_phase(self, phase: HeaterPhase) -> None:
        self._snapshot.phase = phase
        self._phase_started_monotonic = time.monotonic()

        if phase == HeaterPhase.OFF:
            self._snapshot.runtime_seconds = 0
            self._snapshot.telemetry.status_code_major = 0
            self._snapshot.telemetry.status_code_minor = 1
            self._snapshot.telemetry.fan_rpm_set = 0
            self._snapshot.telemetry.fan_rpm_actual = 0
            self._snapshot.telemetry.fuel_pump_frequency_hz = 0.0
            self._snapshot.telemetry.heater_temperature_c = self._snapshot.telemetry.internal_temperature_c
            return

        if phase == HeaterPhase.STARTING:
            self._snapshot.telemetry.status_code_major = 2
            self._snapshot.telemetry.status_code_minor = 1
            self._snapshot.telemetry.fan_rpm_set = 18
            self._snapshot.telemetry.fan_rpm_actual = 16
            self._snapshot.telemetry.fuel_pump_frequency_hz = 0.12
            self._snapshot.telemetry.heater_temperature_c = 30
            return

        if phase == HeaterPhase.WARMING_UP:
            self._snapshot.telemetry.status_code_major = 2
            self._snapshot.telemetry.status_code_minor = 4
            self._snapshot.telemetry.fan_rpm_set = 34
            self._snapshot.telemetry.fan_rpm_actual = 32
            self._snapshot.telemetry.fuel_pump_frequency_hz = 0.24
            self._snapshot.telemetry.heater_temperature_c = 38
            return

        if phase == HeaterPhase.RUNNING:
            self._snapshot.telemetry.status_code_major = 3
            self._snapshot.telemetry.status_code_minor = 0
            return

        self._snapshot.telemetry.status_code_major = 3
        self._snapshot.telemetry.status_code_minor = 4
        self._snapshot.telemetry.fan_rpm_set = 20
        self._snapshot.telemetry.fan_rpm_actual = 18
        self._snapshot.telemetry.fuel_pump_frequency_hz = 0.0


class SerialHeaterProvider:
    # Serial provider for the real controller-replacement protocol over UART.
    def __init__(self, config: SerialProviderConfig, stream: ByteStream | None = None) -> None:
        self._config = config
        self._stream = stream
        self._parser = FrameParser(checksum_byteorder=config.profile.checksum_byteorder)
        self._snapshot = HeaterSnapshot(connected=False)
        self._health = TransportHealth(connected=False, profile_name=config.profile.name)

    def connect(self) -> None:
        if self._stream is None:
            self._stream = SerialByteStream(self._config.device, self._config.profile.baudrate)
        self._health.connected = True
        self._snapshot.connected = True
        self._exchange(build_init_frame(self._config.profile.controller_device))
        self._exchange(build_serial_request_frame(self._config.profile.controller_device))
        self._exchange(build_version_request_frame(self._config.profile.controller_device))
        self.refresh()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
        self._health.connected = False
        self._snapshot.connected = False

    def get_snapshot(self) -> HeaterSnapshot:
        return self._snapshot

    def get_health(self) -> TransportHealth:
        return self._health

    def _exchange(self, frame: Frame, expect_response: bool = True) -> Frame | None:
        assert self._stream is not None
        self._stream.write(encode_frame(frame, checksum_byteorder=self._config.profile.checksum_byteorder))
        if not expect_response:
            return None
        deadline = time.monotonic() + self._config.timeout_s
        while time.monotonic() < deadline:
            data = self._stream.read(256, timeout=0.1)
            if not data:
                continue
            for response in self._parser.feed(data):
                if response.message_id2 == frame.message_id2:
                    return response
        self._health.last_error = f"timeout waiting for response to 0x{frame.message_id2:02x}"
        raise TimeoutError(self._health.last_error)

    def refresh(self) -> HeaterSnapshot:
        settings_frame = self._exchange(build_get_settings_frame(self._config.profile.controller_device))
        if settings_frame and settings_frame.message_id2 == MSG_SETTINGS:
            self._snapshot.settings = parse_settings_payload(settings_frame.payload)
        status_frame = self._exchange(build_status_request_frame(self._config.profile.controller_device))
        if status_frame:
            status = parse_status_payload(status_frame.payload)
            from controller import apply_status

            self._snapshot = apply_status(self._snapshot, status)
        return self._snapshot

    def start(self, settings: HeaterSettings) -> HeaterSnapshot:
        self._snapshot.settings = settings
        self._exchange(build_start_frame(self._config.profile.controller_device, settings))
        self._exchange(build_start_frame(self._config.profile.controller_device, settings))
        return self.refresh()

    def stop(self) -> HeaterSnapshot:
        self._exchange(build_stop_frame(self._config.profile.controller_device))
        return self.refresh()

    def update_settings(self, settings: HeaterSettings) -> HeaterSnapshot:
        self._snapshot.settings = settings
        self._exchange(build_settings_frame(self._config.profile.controller_device, settings))
        self._exchange(build_settings_frame(self._config.profile.controller_device, settings))
        return self.refresh()

    def report_panel_temperature(self, temperature_c: int) -> HeaterSnapshot:
        self._exchange(build_panel_temperature_frame(self._config.profile.controller_device, temperature_c))
        return self.refresh()

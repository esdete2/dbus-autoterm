from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from controller import (
    MSG_DIAGNOSTIC,
    MSG_INIT,
    MSG_PANEL_TEMPERATURE,
    MSG_SERIAL,
    MSG_SETTINGS,
    MSG_START,
    MSG_STATUS,
    MSG_STOP,
    MSG_UNBLOCK,
    MSG_VENTILATION,
    MSG_VERSION,
    parse_settings_payload,
    settings_payload,
    ventilation_payload,
)
from domain import HeaterPhase, HeaterSettings, HeaterSnapshot, OperatingMode
from protocol import CONTROLLER_PROFILE, Frame, ProtocolProfile

LOG = logging.getLogger(__name__)
STARTUP_SEQUENCE = (MSG_INIT, MSG_SERIAL, MSG_VERSION)

PHASE_STATUS_CODES = {
    HeaterPhase.OFF: (0, 1),
    HeaterPhase.STARTING: (2, 1),
    HeaterPhase.WARMING_UP: (2, 4),
    HeaterPhase.RUNNING: (3, 0),
    HeaterPhase.SHUTTING_DOWN: (3, 4),
}


@dataclass
class EmulatorConfig:
    profile: ProtocolProfile = CONTROLLER_PROFILE
    initial_phase: HeaterPhase = HeaterPhase.OFF
    initial_external_temperature_c: int | None = None
    initial_internal_temperature_c: int = 26
    initial_battery_voltage_v: float = 12.6
    initial_error_code: int = 0
    initial_status_code_major: int | None = None
    initial_status_code_minor: int | None = None
    initial_fan_rpm_set: int = 0
    initial_fan_rpm_actual: int = 0
    initial_fuel_pump_frequency_hz: float = 0.0
    startup_sequence_required: bool = True
    response_delay_s: float = 0.02
    status_broadcast_interval_s: float = 0.0
    start_to_warmup_s: float = 4.0
    warmup_to_run_s: float = 12.0
    shutdown_to_off_s: float = 10.0
    duplicate_command_window_s: float = 0.75


class FakeAir2DHeater:
    def __init__(self, config: EmulatorConfig | None = None) -> None:
        self.config = config or EmulatorConfig()
        self.snapshot = HeaterSnapshot()
        self.snapshot.phase = self.config.initial_phase
        self.snapshot.telemetry.internal_temperature_c = self.config.initial_internal_temperature_c
        self.snapshot.telemetry.heater_temperature_c = max(20, self.config.initial_internal_temperature_c)
        self.snapshot.telemetry.external_temperature_c = self.config.initial_external_temperature_c
        self.snapshot.telemetry.battery_voltage_v = self.config.initial_battery_voltage_v
        self.snapshot.telemetry.error_code = self.config.initial_error_code
        self.snapshot.telemetry.fan_rpm_set = self.config.initial_fan_rpm_set
        self.snapshot.telemetry.fan_rpm_actual = self.config.initial_fan_rpm_actual
        self.snapshot.telemetry.fuel_pump_frequency_hz = self.config.initial_fuel_pump_frequency_hz
        now = time.monotonic()
        self._phase_since = now
        self._last_tick = now
        self._last_status_broadcast = now
        self._runtime_anchor = now if self.snapshot.phase in (HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING) else None
        self._serial_payload = bytes.fromhex("129E001580")
        self._version_payload = bytes([2, 1, 3, 4, 3])
        self._diagnostic_enabled = False
        self._startup_index = len(STARTUP_SEQUENCE) if not self.config.startup_sequence_required else 0
        self._ventilation_mode = False
        self._last_command: tuple[int, bytes, float] | None = None
        self._internal_temperature_model = float(self.snapshot.telemetry.internal_temperature_c)
        self._heater_temperature_model = float(self.snapshot.telemetry.heater_temperature_c)
        self._fan_rpm_set_model = float(self.snapshot.telemetry.fan_rpm_set)
        self._fan_rpm_actual_model = float(self.snapshot.telemetry.fan_rpm_actual)
        self._fuel_pump_frequency_model = float(self.snapshot.telemetry.fuel_pump_frequency_hz)
        self._battery_voltage_model = float(self.snapshot.telemetry.battery_voltage_v)
        self._apply_status_code_defaults()

    def _log_event(self, event: str, **fields: object) -> None:
        payload = " ".join(f"{key}={value}" for key, value in fields.items())
        LOG.info("event=%s %s", event, payload)

    def _apply_status_code_defaults(self) -> None:
        if self.config.initial_status_code_major is not None:
            self.snapshot.telemetry.status_code_major = self.config.initial_status_code_major
        else:
            self.snapshot.telemetry.status_code_major = PHASE_STATUS_CODES[self.snapshot.phase][0]
        if self.config.initial_status_code_minor is not None:
            self.snapshot.telemetry.status_code_minor = self.config.initial_status_code_minor
        else:
            self.snapshot.telemetry.status_code_minor = PHASE_STATUS_CODES[self.snapshot.phase][1]

    def _set_status_code(self, major: int, minor: int) -> None:
        if (
            self.snapshot.telemetry.status_code_major != major
            or self.snapshot.telemetry.status_code_minor != minor
        ):
            self.snapshot.telemetry.status_code_major = major
            self.snapshot.telemetry.status_code_minor = minor
            self._log_event("status_code", code=f"{major}.{minor}")

    def _set_phase(self, phase: HeaterPhase) -> None:
        self._set_phase_at(phase, time.monotonic())

    def _set_phase_at(self, phase: HeaterPhase, now: float) -> None:
        if self.snapshot.phase != phase:
            previous = self.snapshot.phase
            self.snapshot.phase = phase
            self._phase_since = now
            if phase == HeaterPhase.STARTING:
                self._runtime_anchor = now
            elif phase == HeaterPhase.OFF:
                self._runtime_anchor = None
                self.snapshot.runtime_seconds = 0
            self._set_status_code(*PHASE_STATUS_CODES[phase])
            self._log_event("phase_transition", frm=previous.name.lower(), to=phase.name.lower())

    def _startup_complete(self) -> bool:
        return self._startup_index >= len(STARTUP_SEQUENCE)

    def _requires_startup(self, frame: Frame) -> bool:
        if not self.config.startup_sequence_required:
            return False
        return frame.message_id2 not in {MSG_INIT, MSG_SERIAL, MSG_VERSION}

    def _expected_startup_message(self) -> int | None:
        if self._startup_complete():
            return None
        return STARTUP_SEQUENCE[self._startup_index]

    def _accept_startup_message(self, message_id2: int) -> bool:
        if not self.config.startup_sequence_required:
            return True
        expected = self._expected_startup_message()
        if expected is None:
            return True
        return message_id2 == expected

    def _mark_startup_message(self, message_id2: int) -> None:
        if self.config.startup_sequence_required and self._expected_startup_message() == message_id2:
            self._startup_index += 1

    def _ignore_malformed_payload(self, frame: Frame, exc: Exception) -> list[Frame]:
        self._log_event(
            "frame_ignored",
            reason="malformed_payload",
            msg=f"0x{frame.message_id2:02X}",
            error=str(exc),
        )
        return []

    def _is_duplicate_command(self, frame: Frame, now: float) -> bool:
        if self._last_command is None:
            return False
        last_id, last_payload, last_time = self._last_command
        return (
            frame.message_id2 == last_id
            and frame.payload == last_payload
            and now - last_time <= self.config.duplicate_command_window_s
        )

    def _remember_command(self, frame: Frame, now: float) -> None:
        self._last_command = (frame.message_id2, frame.payload, now)

    def _build_settings_response(self, device: int, message_id2: int) -> list[Frame]:
        payload = settings_payload(self.snapshot.settings)
        return [Frame(device=device, message_id2=message_id2, payload=payload)]

    def _ambient_temperature(self) -> float:
        if self.snapshot.telemetry.external_temperature_c is not None:
            return float(self.snapshot.telemetry.external_temperature_c)
        return float(self.config.initial_internal_temperature_c)

    def _control_temperature(self) -> float | None:
        if self.snapshot.settings.mode == OperatingMode.CONTROLLER_TEMPERATURE:
            value = self.snapshot.telemetry.controller_temperature_c
            return None if value is None else float(value)
        if self.snapshot.settings.mode == OperatingMode.EXTERNAL_TEMPERATURE:
            value = self.snapshot.telemetry.external_temperature_c
            return None if value is None else float(value)
        return float(self.snapshot.telemetry.internal_temperature_c)

    def _effective_power_level(self) -> float:
        base_power = float(max(1, self.snapshot.settings.power_level))
        if self._ventilation_mode or self.snapshot.settings.mode == OperatingMode.POWER:
            return base_power
        control_temperature = self._control_temperature()
        if control_temperature is None:
            return base_power
        gap = float(self.snapshot.settings.setpoint_c) - control_temperature
        if gap <= -1.5:
            return 0.5
        if gap <= 0.5:
            return min(base_power, 1.0)
        if gap <= 2.0:
            return min(base_power, 2.0)
        if gap <= 4.0:
            return min(base_power, 4.0)
        if gap <= 7.0:
            return min(base_power, 6.0)
        return base_power

    def _apply_model(self, delta: float, now: float) -> None:
        ambient_temperature = self._ambient_temperature()
        effective_power_level = self._effective_power_level()
        power_level = max(1.0, effective_power_level)
        if self.snapshot.settings.mode == OperatingMode.POWER or self._ventilation_mode:
            requested_cabin_temperature = min(58.0, ambient_temperature + 7.0 + (power_level * 2.5))
        else:
            requested_cabin_temperature = max(
                ambient_temperature,
                min(58.0, float(self.snapshot.settings.setpoint_c)),
            )
        if self._ventilation_mode:
            elapsed = now - self._phase_since
            if elapsed < 2.0:
                self._set_status_code(1, 1)
            else:
                self._set_status_code(3, 35)
            target_internal = ambient_temperature
            target_heater = max(ambient_temperature + 2.0, self._heater_temperature_model - 1.5)
            target_fan_set = 22.0 + (power_level * 5.0)
            target_fan_actual = max(0.0, target_fan_set - 2.0)
            target_pump = 0.0
            heat_rate = 0.5
            blower_rate = 12.0
            pump_rate = 1.0
        elif self.snapshot.phase == HeaterPhase.OFF:
            target_internal = ambient_temperature
            target_heater = max(20.0, ambient_temperature)
            target_fan_set = 0.0
            target_fan_actual = 0.0
            target_pump = 0.0
            heat_rate = 0.35
            blower_rate = 12.0
            pump_rate = 0.6
        elif self.snapshot.phase == HeaterPhase.STARTING:
            target_internal = min(requested_cabin_temperature, ambient_temperature + 4.0 + (power_level * 1.2))
            target_heater = min(45.0, ambient_temperature + 10.0 + (power_level * 2.5))
            target_fan_set = 20.0 + (power_level * 2.0)
            target_fan_actual = max(0.0, target_fan_set - 2.0)
            target_pump = 0.10 + (power_level * 0.03)
            heat_rate = 1.2
            blower_rate = 10.0
            pump_rate = 0.15
        elif self.snapshot.phase == HeaterPhase.WARMING_UP:
            target_internal = min(requested_cabin_temperature, ambient_temperature + 8.0 + (power_level * 1.8))
            target_heater = min(72.0, ambient_temperature + 24.0 + (power_level * 4.0))
            target_fan_set = 34.0 + (power_level * 4.0)
            target_fan_actual = max(0.0, target_fan_set - 2.0)
            target_pump = 0.24 + (power_level * 0.06)
            heat_rate = 1.8
            blower_rate = 14.0
            pump_rate = 0.22
        elif self.snapshot.phase == HeaterPhase.RUNNING:
            target_internal = requested_cabin_temperature
            target_heater = min(85.0, target_internal + 22.0 + (power_level * 2.5))
            target_fan_set = 46.0 + (power_level * 6.0)
            target_fan_actual = max(0.0, target_fan_set - 2.0)
            target_pump = 0.32 + (power_level * 0.08)
            heat_rate = 0.9
            blower_rate = 8.0
            pump_rate = 0.10
        else:
            target_internal = ambient_temperature
            target_heater = max(25.0, self._internal_temperature_model)
            target_fan_set = 12.0
            target_fan_actual = 10.0
            target_pump = 0.0
            heat_rate = 0.8
            blower_rate = 16.0
            pump_rate = 0.35

        def approach(current: float, target: float, rate_per_second: float) -> float:
            if current < target:
                return min(target, current + (rate_per_second * delta))
            return max(target, current - (rate_per_second * delta))

        self._internal_temperature_model = approach(self._internal_temperature_model, target_internal, heat_rate)
        self._heater_temperature_model = approach(self._heater_temperature_model, target_heater, heat_rate * 1.6)
        self._fan_rpm_set_model = approach(self._fan_rpm_set_model, target_fan_set, blower_rate)
        self._fan_rpm_actual_model = approach(self._fan_rpm_actual_model, target_fan_actual, blower_rate)
        self._fuel_pump_frequency_model = approach(self._fuel_pump_frequency_model, target_pump, pump_rate)

        self.snapshot.telemetry.internal_temperature_c = int(round(self._internal_temperature_model))
        self.snapshot.telemetry.heater_temperature_c = int(round(self._heater_temperature_model))
        self.snapshot.telemetry.fan_rpm_set = max(0, int(round(self._fan_rpm_set_model)))
        self.snapshot.telemetry.fan_rpm_actual = max(0, int(round(self._fan_rpm_actual_model)))
        self.snapshot.telemetry.fuel_pump_frequency_hz = round(max(0.0, self._fuel_pump_frequency_model), 2)
        active_load = power_level if self.snapshot.phase != HeaterPhase.OFF or self._ventilation_mode else 0.0
        target_voltage = self.config.initial_battery_voltage_v - min(1.2, active_load * 0.08)
        if self.snapshot.phase == HeaterPhase.OFF and not self._ventilation_mode:
            target_voltage = self.config.initial_battery_voltage_v
        self._battery_voltage_model = approach(self._battery_voltage_model, target_voltage, 0.15)
        self.snapshot.telemetry.battery_voltage_v = round(max(10.0, self._battery_voltage_model), 1)

        if self._runtime_anchor is not None:
            self.snapshot.runtime_seconds = int(max(0.0, now - self._runtime_anchor))

    def _build_status_payload(self) -> bytes:
        external = (
            0x7F
            if self.snapshot.telemetry.external_temperature_c is None
            else self.snapshot.telemetry.external_temperature_c & 0xFF
        )
        heater_sensor = max(0, min(255, self.snapshot.telemetry.heater_temperature_c + 15))
        return bytes(
            [
                self.snapshot.telemetry.status_code_major & 0xFF,
                self.snapshot.telemetry.status_code_minor & 0xFF,
                self.snapshot.telemetry.error_code & 0xFF,
                self.snapshot.telemetry.internal_temperature_c & 0xFF,
                external,
                0x00,
                int(self.snapshot.telemetry.battery_voltage_v * 10) & 0xFF,
                0x01,
                heater_sensor & 0xFF,
                0x00,
                0x00,
                self.snapshot.telemetry.fan_rpm_set & 0xFF,
                self.snapshot.telemetry.fan_rpm_actual & 0xFF,
                0x00,
                int(self.snapshot.telemetry.fuel_pump_frequency_hz * 100) & 0xFF,
                0x00,
                0x00,
                0x00,
                0x64,
            ]
        )

    def tick(self, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        delta = max(0.0, now - self._last_tick)
        self._last_tick = now
        elapsed = now - self._phase_since
        if self.snapshot.phase == HeaterPhase.STARTING:
            if elapsed >= self.config.start_to_warmup_s:
                self._set_phase_at(HeaterPhase.WARMING_UP, now)
            elif elapsed >= self.config.start_to_warmup_s * (2.0 / 3.0):
                self._set_status_code(2, 3)
            elif elapsed >= self.config.start_to_warmup_s / 3.0:
                self._set_status_code(2, 2)
        elif self.snapshot.phase == HeaterPhase.WARMING_UP and elapsed >= self.config.warmup_to_run_s:
            self._set_phase_at(HeaterPhase.RUNNING, now)
        elif self.snapshot.phase == HeaterPhase.SHUTTING_DOWN:
            if elapsed >= self.config.shutdown_to_off_s:
                self._set_phase_at(HeaterPhase.OFF, now)
            elif elapsed >= self.config.shutdown_to_off_s / 2.0:
                self._set_status_code(4, 0)
        self._apply_model(delta, now)

    def background_frames(self, now: float | None = None) -> list[Frame]:
        now = now if now is not None else time.monotonic()
        self.tick(now)
        if not self._startup_complete():
            return []
        if self.config.status_broadcast_interval_s <= 0:
            return []
        if now - self._last_status_broadcast < self.config.status_broadcast_interval_s:
            return []
        self._last_status_broadcast = now
        frame = Frame(
            device=self.config.profile.heater_device,
            message_id2=MSG_STATUS,
            payload=self._build_status_payload(),
        )
        self._log_event("frame_out", msg=f"0x{frame.message_id2:02X}", payload=frame.payload.hex(), unsolicited=True)
        return [frame]

    def handle_frame(self, frame: Frame) -> list[Frame]:
        self.tick()
        self._log_event("frame_in", msg=f"0x{frame.message_id2:02X}", payload=frame.payload.hex())
        device = self.config.profile.heater_device
        now = time.monotonic()
        if frame.message_id2 == MSG_INIT:
            if not self._accept_startup_message(MSG_INIT):
                self._log_event(
                    "frame_ignored",
                    reason="startup_order",
                    msg=f"0x{frame.message_id2:02X}",
                    expected=f"0x{self._expected_startup_message():02X}",
                )
                return []
            self._mark_startup_message(MSG_INIT)
            responses = [Frame(device=self.config.profile.init_device, message_id2=MSG_INIT)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_SERIAL:
            if not self._accept_startup_message(MSG_SERIAL):
                self._log_event(
                    "frame_ignored",
                    reason="startup_order",
                    msg=f"0x{frame.message_id2:02X}",
                    expected=f"0x{self._expected_startup_message():02X}",
                )
                return []
            self._mark_startup_message(MSG_SERIAL)
            responses = [Frame(device=device, message_id2=MSG_SERIAL, payload=self._serial_payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_VERSION:
            if not self._accept_startup_message(MSG_VERSION):
                self._log_event(
                    "frame_ignored",
                    reason="startup_order",
                    msg=f"0x{frame.message_id2:02X}",
                    expected=f"0x{self._expected_startup_message():02X}",
                )
                return []
            self._mark_startup_message(MSG_VERSION)
            responses = [Frame(device=device, message_id2=MSG_VERSION, payload=self._version_payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if self._requires_startup(frame) and not self._startup_complete():
            self._log_event("frame_ignored", reason="startup_incomplete", msg=f"0x{frame.message_id2:02X}")
            return []
        if frame.message_id2 == MSG_SETTINGS:
            if frame.payload and self._is_duplicate_command(frame, now):
                responses = self._build_settings_response(device, MSG_SETTINGS)
                for response in responses:
                    self._log_event(
                        "frame_out",
                        msg=f"0x{response.message_id2:02X}",
                        payload=response.payload.hex(),
                        duplicate=True,
                    )
                return responses
            if frame.payload:
                try:
                    self.snapshot.settings = parse_settings_payload(frame.payload)
                except Exception as exc:
                    return self._ignore_malformed_payload(frame, exc)
                self._remember_command(frame, now)
            responses = self._build_settings_response(device, MSG_SETTINGS)
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_START:
            if self._is_duplicate_command(frame, now):
                responses = self._build_settings_response(device, MSG_START)
                for response in responses:
                    self._log_event(
                        "frame_out",
                        msg=f"0x{response.message_id2:02X}",
                        payload=response.payload.hex(),
                        duplicate=True,
                    )
                return responses
            try:
                self.snapshot.settings = parse_settings_payload(frame.payload)
            except Exception as exc:
                return self._ignore_malformed_payload(frame, exc)
            self._remember_command(frame, now)
            self._ventilation_mode = False
            self.snapshot.runtime_seconds = 0
            self._set_phase(HeaterPhase.STARTING)
            self._set_status_code(2, 1)
            responses = self._build_settings_response(device, MSG_START)
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_STOP:
            self._ventilation_mode = False
            self._set_phase(HeaterPhase.SHUTTING_DOWN)
            responses = [Frame(device=device, message_id2=MSG_STOP)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_STATUS:
            payload = self._build_status_payload()
            responses = [Frame(device=device, message_id2=MSG_STATUS, payload=payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_PANEL_TEMPERATURE and frame.payload:
            self.snapshot.telemetry.controller_temperature_c = frame.payload[0]
            responses = [Frame(device=device, message_id2=MSG_PANEL_TEMPERATURE, payload=frame.payload[:1])]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_DIAGNOSTIC:
            self._diagnostic_enabled = bool(frame.payload[:1] == b"\x01")
            responses = [Frame(device=device, message_id2=MSG_DIAGNOSTIC, payload=frame.payload[:1])]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_UNBLOCK:
            self.snapshot.telemetry.error_code = 0
            if self._ventilation_mode:
                self._set_status_code(1, 1)
            else:
                self._set_status_code(*PHASE_STATUS_CODES[self.snapshot.phase])
            responses = [Frame(device=self.config.profile.init_device, message_id2=MSG_UNBLOCK)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_VENTILATION and frame.payload:
            if self._is_duplicate_command(frame, now):
                power_level = frame.payload[2] if len(frame.payload) >= 3 else self.snapshot.settings.power_level
                payload = ventilation_payload(power_level, response=True)
                responses = [Frame(device=device, message_id2=MSG_VENTILATION, payload=payload)]
                for response in responses:
                    self._log_event(
                        "frame_out",
                        msg=f"0x{response.message_id2:02X}",
                        payload=response.payload.hex(),
                        duplicate=True,
                    )
                return responses
            if len(frame.payload) < 3:
                return self._ignore_malformed_payload(frame, ValueError("ventilation payload too short"))
            power_level = frame.payload[2]
            self._remember_command(frame, now)
            self.snapshot.settings = HeaterSettings(
                use_work_time=self.snapshot.settings.use_work_time,
                work_time_minutes=self.snapshot.settings.work_time_minutes,
                mode=self.snapshot.settings.mode,
                setpoint_c=self.snapshot.settings.setpoint_c,
                wait_mode=self.snapshot.settings.wait_mode,
                power_level=power_level,
            )
            self._ventilation_mode = True
            self._set_phase(HeaterPhase.RUNNING)
            self._set_status_code(1, 1)
            payload = ventilation_payload(power_level, response=True)
            responses = [Frame(device=device, message_id2=MSG_VENTILATION, payload=payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        LOG.warning("ignoring unsupported frame %s", frame)
        return []

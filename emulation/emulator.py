from __future__ import annotations

import argparse
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
from domain import HeaterPhase, HeaterSettings, HeaterSnapshot
from protocol import CONTROLLER_PROFILE, Frame, FrameParser, ProtocolProfile, encode_frame
from transports import ByteStream, SerialByteStream, open_pty_endpoint

LOG = logging.getLogger(__name__)

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
    status_broadcast_interval_s: float = 1.0
    start_to_warmup_s: float = 4.0
    warmup_to_run_s: float = 12.0
    shutdown_to_off_s: float = 10.0


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
        self._serial_payload = bytes.fromhex("129E001580")
        self._version_payload = bytes([2, 1, 3, 4, 3])
        self._diagnostic_enabled = False
        self._init_seen = False
        self._serial_seen = False
        self._version_seen = False
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
        if self.snapshot.phase != phase:
            previous = self.snapshot.phase
            self.snapshot.phase = phase
            self._phase_since = time.monotonic()
            self._set_status_code(*PHASE_STATUS_CODES[phase])
            self._log_event("phase_transition", frm=previous.name.lower(), to=phase.name.lower())

    def _startup_complete(self) -> bool:
        return self._init_seen and self._serial_seen and self._version_seen

    def _requires_startup(self, frame: Frame) -> bool:
        if not self.config.startup_sequence_required:
            return False
        return frame.message_id2 not in {MSG_INIT, MSG_SERIAL, MSG_VERSION}

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
                self._set_phase(HeaterPhase.WARMING_UP)
            elif elapsed >= self.config.start_to_warmup_s * (2.0 / 3.0):
                self._set_status_code(2, 3)
            elif elapsed >= self.config.start_to_warmup_s / 3.0:
                self._set_status_code(2, 2)
        elif self.snapshot.phase == HeaterPhase.WARMING_UP and elapsed >= self.config.warmup_to_run_s:
            self._set_phase(HeaterPhase.RUNNING)
        elif self.snapshot.phase == HeaterPhase.SHUTTING_DOWN:
            if elapsed >= self.config.shutdown_to_off_s:
                self._set_phase(HeaterPhase.OFF)
            elif elapsed >= self.config.shutdown_to_off_s / 2.0:
                self._set_status_code(4, 0)

        if self.snapshot.phase in (HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING):
            self.snapshot.runtime_seconds += int(delta)
            self.snapshot.telemetry.internal_temperature_c = min(
                85, self.snapshot.telemetry.internal_temperature_c + max(1, int(delta * 2))
            )
            self.snapshot.telemetry.heater_temperature_c = min(
                85, self.snapshot.telemetry.heater_temperature_c + max(1, int(delta * 3))
            )
            self.snapshot.telemetry.fan_rpm_set = min(255, self.snapshot.telemetry.fan_rpm_set + 5)
            self.snapshot.telemetry.fan_rpm_actual = min(255, self.snapshot.telemetry.fan_rpm_actual + 4)
            self.snapshot.telemetry.fuel_pump_frequency_hz = min(
                5.0, self.snapshot.telemetry.fuel_pump_frequency_hz + max(0.1, round(delta * 0.5, 2))
            )
        elif self.snapshot.phase == HeaterPhase.SHUTTING_DOWN:
            self.snapshot.telemetry.fan_rpm_set = max(0, self.snapshot.telemetry.fan_rpm_set - 5)
            self.snapshot.telemetry.fan_rpm_actual = max(0, self.snapshot.telemetry.fan_rpm_actual - 5)
            self.snapshot.telemetry.fuel_pump_frequency_hz = max(
                0.0, self.snapshot.telemetry.fuel_pump_frequency_hz - max(0.2, round(delta * 0.6, 2))
            )
            self.snapshot.telemetry.heater_temperature_c = max(
                20, self.snapshot.telemetry.heater_temperature_c - max(1, int(delta * 2))
            )
            self.snapshot.telemetry.internal_temperature_c = max(
                20, self.snapshot.telemetry.internal_temperature_c - max(1, int(delta))
            )

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
        if frame.message_id2 == MSG_INIT:
            self._init_seen = True
            responses = [Frame(device=self.config.profile.init_device, message_id2=MSG_INIT)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_SERIAL:
            self._serial_seen = True
            responses = [Frame(device=device, message_id2=MSG_SERIAL, payload=self._serial_payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_VERSION:
            self._version_seen = True
            responses = [Frame(device=device, message_id2=MSG_VERSION, payload=self._version_payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if self._requires_startup(frame) and not self._startup_complete():
            self._log_event("frame_ignored", reason="startup_incomplete", msg=f"0x{frame.message_id2:02X}")
            return []
        if frame.message_id2 == MSG_SETTINGS:
            if frame.payload:
                self.snapshot.settings = parse_settings_payload(frame.payload)
            payload = settings_payload(self.snapshot.settings)
            responses = [Frame(device=device, message_id2=MSG_SETTINGS, payload=payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_START:
            self.snapshot.settings = parse_settings_payload(frame.payload)
            self.snapshot.runtime_seconds = 0
            self._set_phase(HeaterPhase.STARTING)
            self._set_status_code(2, 1)
            payload = settings_payload(self.snapshot.settings)
            responses = [Frame(device=device, message_id2=MSG_START, payload=payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_STOP:
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
            responses = [Frame(device=self.config.profile.init_device, message_id2=MSG_UNBLOCK)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        if frame.message_id2 == MSG_VENTILATION and frame.payload:
            power_level = frame.payload[2]
            self.snapshot.settings = HeaterSettings(
                use_work_time=self.snapshot.settings.use_work_time,
                work_time_minutes=self.snapshot.settings.work_time_minutes,
                mode=self.snapshot.settings.mode,
                setpoint_c=self.snapshot.settings.setpoint_c,
                wait_mode=self.snapshot.settings.wait_mode,
                power_level=power_level,
            )
            self._set_phase(HeaterPhase.RUNNING)
            self._set_status_code(3, 35)
            payload = ventilation_payload(power_level, response=True)
            responses = [Frame(device=device, message_id2=MSG_VENTILATION, payload=payload)]
            for response in responses:
                self._log_event("frame_out", msg=f"0x{response.message_id2:02X}", payload=response.payload.hex())
            return responses
        LOG.warning("ignoring unsupported frame %s", frame)
        return []


def _run_loop(heater: FakeAir2DHeater, stream: ByteStream, profile: ProtocolProfile) -> None:
    parser = FrameParser(checksum_byteorder=profile.checksum_byteorder)
    while True:
        data = stream.read(256, timeout=0.2)
        now = time.monotonic()
        for frame in heater.background_frames(now):
            if heater.config.response_delay_s > 0:
                time.sleep(heater.config.response_delay_s)
            stream.write(encode_frame(frame, checksum_byteorder=profile.checksum_byteorder))
        if not data:
            continue
        for frame in parser.feed(data):
            for response in heater.handle_frame(frame):
                if heater.config.response_delay_s > 0:
                    time.sleep(heater.config.response_delay_s)
                stream.write(encode_frame(response, checksum_byteorder=profile.checksum_byteorder))


def _build_transport(args: argparse.Namespace, profile: ProtocolProfile) -> ByteStream:
    if args.transport == "serial":
        device = args.device or "/dev/serial0"
        LOG.info(
            "event=startup transport=serial device=%s baudrate=%s profile=%s",
            device,
            args.baudrate or profile.baudrate,
            profile.name,
        )
        return SerialByteStream(device, args.baudrate or profile.baudrate)
    endpoint = open_pty_endpoint()
    LOG.info("event=startup transport=pty slave_path=%s profile=%s", endpoint.slave_path, profile.name)
    print(endpoint.slave_path, flush=True)
    return endpoint.stream


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dbus-autoterm emulation")
    parser.add_argument("--transport", choices=["serial", "pty"], default="serial")
    parser.add_argument("--device", help="serial device when --transport=serial, default: /dev/serial0")
    parser.add_argument("--baudrate", type=int, default=None)
    parser.add_argument(
        "--initial-phase",
        choices=["off", "starting", "warming_up", "running", "shutting_down"],
        default="off",
    )
    parser.add_argument("--internal-temperature", type=int, default=26)
    parser.add_argument("--external-temperature", type=int, default=None)
    parser.add_argument("--battery-voltage", type=float, default=12.6)
    parser.add_argument("--error-code", type=int, default=0)
    parser.add_argument("--fan-rpm-set", type=int, default=0)
    parser.add_argument("--fan-rpm-actual", type=int, default=0)
    parser.add_argument("--fuel-pump-frequency", type=float, default=0.0)
    parser.add_argument("--response-delay", type=float, default=0.02)
    parser.add_argument("--status-broadcast-interval", type=float, default=1.0)
    parser.add_argument("--startup-sequence-required", action="store_true", default=True)
    parser.add_argument("--no-startup-sequence-required", dest="startup_sequence_required", action="store_false")
    parser.add_argument("--status-code", default=None, help="override initial status code, for example 2.3")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    profile = CONTROLLER_PROFILE
    status_major = None
    status_minor = None
    if args.status_code:
        major_str, minor_str = args.status_code.split(".", 1)
        status_major = int(major_str)
        status_minor = int(minor_str)
    phase_map = {
        "off": HeaterPhase.OFF,
        "starting": HeaterPhase.STARTING,
        "warming_up": HeaterPhase.WARMING_UP,
        "running": HeaterPhase.RUNNING,
        "shutting_down": HeaterPhase.SHUTTING_DOWN,
    }
    heater = FakeAir2DHeater(
        EmulatorConfig(
            profile=profile,
            initial_phase=phase_map[args.initial_phase],
            initial_internal_temperature_c=args.internal_temperature,
            initial_external_temperature_c=args.external_temperature,
            initial_battery_voltage_v=args.battery_voltage,
            initial_error_code=args.error_code,
            initial_status_code_major=status_major,
            initial_status_code_minor=status_minor,
            initial_fan_rpm_set=args.fan_rpm_set,
            initial_fan_rpm_actual=args.fan_rpm_actual,
            initial_fuel_pump_frequency_hz=args.fuel_pump_frequency,
            startup_sequence_required=args.startup_sequence_required,
            response_delay_s=args.response_delay,
            status_broadcast_interval_s=args.status_broadcast_interval,
        )
    )
    LOG.info(
        "event=heater_state phase=%s status_code=%s.%s internal_temp=%s external_temp=%s battery_voltage=%.1f error_code=%s startup_sequence_required=%s response_delay_s=%.3f status_broadcast_interval_s=%.3f",
        heater.snapshot.phase.name.lower(),
        heater.snapshot.telemetry.status_code_major,
        heater.snapshot.telemetry.status_code_minor,
        heater.snapshot.telemetry.internal_temperature_c,
        heater.snapshot.telemetry.external_temperature_c,
        heater.snapshot.telemetry.battery_voltage_v,
        heater.snapshot.telemetry.error_code,
        heater.config.startup_sequence_required,
        heater.config.response_delay_s,
        heater.config.status_broadcast_interval_s,
    )
    stream = _build_transport(args, profile)
    try:
        try:
            _run_loop(heater, stream, profile)
        except KeyboardInterrupt:
            LOG.info("event=shutdown reason=keyboard_interrupt")
            return 130
    finally:
        stream.close()
    return 0

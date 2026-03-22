from __future__ import annotations

from dataclasses import dataclass

from domain import HeaterPhase, HeaterSettings, HeaterSnapshot, OperatingMode
from protocol import Frame, ProtocolError

MSG_START = 0x01
MSG_SETTINGS = 0x02
MSG_STOP = 0x03
MSG_SERIAL = 0x04
MSG_VERSION = 0x06
MSG_DIAGNOSTIC = 0x07
MSG_STATUS = 0x0F
MSG_PANEL_TEMPERATURE = 0x11
MSG_INIT = 0x1C
MSG_VENTILATION = 0x23
MSG_UNBLOCK = 0x0D

STATUS_TEXT = {
    HeaterPhase.OFF: "off",
    HeaterPhase.STARTING: "starting",
    HeaterPhase.WARMING_UP: "warming up",
    HeaterPhase.RUNNING: "running",
    HeaterPhase.SHUTTING_DOWN: "shutting down",
}


@dataclass(frozen=True)
class StatusPayload:
    phase: HeaterPhase
    status_code_major: int
    status_code_minor: int
    error_code: int
    internal_temperature_c: int
    heater_temperature_c: int
    external_temperature_c: int | None
    battery_voltage_v: float
    fan_rpm_set: int
    fan_rpm_actual: int
    fuel_pump_frequency_hz: float
    unknown_fields: bytes


def settings_payload(settings: HeaterSettings) -> bytes:
    return bytes(
        [
            0x00 if settings.use_work_time else 0x01,
            settings.work_time_minutes & 0xFF,
            int(settings.mode),
            settings.setpoint_c & 0xFF,
            settings.wait_mode & 0xFF,
            settings.power_level & 0xFF,
        ]
    )


def ventilation_payload(power_level: int, response: bool = False) -> bytes:
    return bytes([0xFF, 0xFF, power_level & 0xFF, 0x43 if response else 0xFF])


def _signed_byte(value: int) -> int:
    return value if value < 0x80 else value - 0x100


def _phase_from_status_code(major: int, minor: int) -> HeaterPhase:
    if major == 0:
        return HeaterPhase.OFF
    if major == 1:
        return HeaterPhase.STARTING
    if major == 2:
        return HeaterPhase.WARMING_UP
    if major == 3:
        if minor == 4:
            return HeaterPhase.SHUTTING_DOWN
        return HeaterPhase.RUNNING
    if major == 4:
        return HeaterPhase.SHUTTING_DOWN
    return HeaterPhase.OFF


def build_start_frame(device: int, settings: HeaterSettings) -> Frame:
    return Frame(device=device, message_id2=MSG_START, payload=settings_payload(settings))


def build_settings_frame(device: int, settings: HeaterSettings) -> Frame:
    return Frame(device=device, message_id2=MSG_SETTINGS, payload=settings_payload(settings))


def build_get_settings_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_SETTINGS)


def build_stop_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_STOP)


def build_status_request_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_STATUS)


def build_version_request_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_VERSION)


def build_serial_request_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_SERIAL)


def build_panel_temperature_frame(device: int, temperature_c: int) -> Frame:
    return Frame(device=device, message_id2=MSG_PANEL_TEMPERATURE, payload=bytes([temperature_c & 0xFF]))


def build_init_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_INIT)


def build_diagnostic_toggle_frame(device: int, enabled: bool) -> Frame:
    return Frame(device=device, message_id2=MSG_DIAGNOSTIC, payload=bytes([1 if enabled else 0]))


def build_unblock_frame(device: int) -> Frame:
    return Frame(device=device, message_id2=MSG_UNBLOCK)


def build_ventilation_frame(device: int, power_level: int) -> Frame:
    return Frame(device=device, message_id2=MSG_VENTILATION, payload=ventilation_payload(power_level))


def parse_settings_payload(payload: bytes) -> HeaterSettings:
    if len(payload) < 6:
        raise ProtocolError(f"settings payload too short: {payload.hex()}")
    return HeaterSettings(
        use_work_time=payload[0] == 0x00,
        work_time_minutes=payload[1],
        mode=OperatingMode(payload[2]),
        setpoint_c=payload[3],
        wait_mode=payload[4],
        power_level=payload[5],
    )


def parse_status_payload(payload: bytes) -> StatusPayload:
    if len(payload) == 10:
        external = None if payload[4] == 0x7F else payload[4]
        major = payload[0]
        minor = payload[1]
        return StatusPayload(
            phase=_phase_from_status_code(major, minor),
            status_code_major=major,
            status_code_minor=minor,
            error_code=payload[2],
            internal_temperature_c=payload[3],
            heater_temperature_c=payload[3],
            external_temperature_c=external,
            battery_voltage_v=payload[6] / 10.0,
            fan_rpm_set=0,
            fan_rpm_actual=0,
            fuel_pump_frequency_hz=0.0,
            unknown_fields=payload[5:6] + payload[7:10],
        )
    if len(payload) == 19:
        major = payload[0]
        minor = payload[1]
        external = payload[4]
        external = None if external == 0x7F else _signed_byte(external)
        return StatusPayload(
            phase=_phase_from_status_code(major, minor),
            status_code_major=major,
            status_code_minor=minor,
            error_code=payload[2],
            internal_temperature_c=_signed_byte(payload[3]),
            heater_temperature_c=payload[8] - 15,
            external_temperature_c=external,
            battery_voltage_v=payload[6] / 10.0,
            fan_rpm_set=payload[11],
            fan_rpm_actual=payload[12],
            fuel_pump_frequency_hz=payload[14] / 100.0,
            unknown_fields=bytes([payload[5], payload[7], payload[9], payload[10], payload[13], payload[15], payload[16], payload[17], payload[18]]),
        )
    raise ProtocolError(f"unsupported status payload length {len(payload)}: {payload.hex()}")


def apply_status(snapshot: HeaterSnapshot, status: StatusPayload) -> HeaterSnapshot:
    snapshot.phase = status.phase
    snapshot.telemetry.status_code_major = status.status_code_major
    snapshot.telemetry.status_code_minor = status.status_code_minor
    snapshot.telemetry.error_code = status.error_code
    snapshot.telemetry.internal_temperature_c = status.internal_temperature_c
    snapshot.telemetry.heater_temperature_c = status.heater_temperature_c
    snapshot.telemetry.external_temperature_c = status.external_temperature_c
    snapshot.telemetry.battery_voltage_v = status.battery_voltage_v
    snapshot.telemetry.fan_rpm_set = status.fan_rpm_set
    snapshot.telemetry.fan_rpm_actual = status.fan_rpm_actual
    snapshot.telemetry.fuel_pump_frequency_hz = status.fuel_pump_frequency_hz
    snapshot.telemetry.unknown_fields = status.unknown_fields
    return snapshot

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from time import time


class OperatingMode(IntEnum):
    HEATER_TEMPERATURE = 0x01
    CONTROLLER_TEMPERATURE = 0x02
    EXTERNAL_TEMPERATURE = 0x03
    POWER = 0x04


class HeaterPhase(IntEnum):
    OFF = 0x00
    STARTING = 0x01
    WARMING_UP = 0x02
    RUNNING = 0x03
    SHUTTING_DOWN = 0x04


@dataclass
class HeaterSettings:
    use_work_time: bool = False
    work_time_minutes: int = 0
    mode: OperatingMode = OperatingMode.POWER
    setpoint_c: int = 15
    wait_mode: int = 0
    power_level: int = 2


@dataclass
class HeaterTelemetry:
    status_code_major: int = 0
    status_code_minor: int = 1
    internal_temperature_c: int = 26
    heater_temperature_c: int = 26
    external_temperature_c: int | None = None
    battery_voltage_v: float = 12.6
    controller_temperature_c: int | None = None
    error_code: int = 0
    fan_rpm_set: int = 0
    fan_rpm_actual: int = 0
    fuel_pump_frequency_hz: float = 0.0
    unknown_fields: bytes = b""


@dataclass
class HeaterSnapshot:
    phase: HeaterPhase = HeaterPhase.OFF
    settings: HeaterSettings = field(default_factory=HeaterSettings)
    telemetry: HeaterTelemetry = field(default_factory=HeaterTelemetry)
    runtime_seconds: int = 0
    connected: bool = True
    last_update_monotonic: float = field(default_factory=time)


@dataclass
class TransportHealth:
    connected: bool = False
    profile_name: str = ""
    last_error: str = ""

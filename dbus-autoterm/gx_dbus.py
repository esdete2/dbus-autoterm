from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from controller import STATUS_TEXT
from domain import HeaterPhase, HeaterSnapshot


class MockVeDbusService:
    def __init__(self, servicename: str) -> None:
        self._paths: dict[str, object] = {}
        self._callbacks: dict[str, Callable[[str, object], bool]] = {}
        self.name = servicename

    def add_path(
        self,
        path: str,
        value: object,
        description: str = "",
        writeable: bool = False,
        onchangecallback: Callable[[str, object], bool] | None = None,
        gettextcallback=None,
        valuetype=None,
        itemtype=None,
    ) -> None:
        del description, writeable, gettextcallback, valuetype, itemtype
        self._paths[path] = value
        if onchangecallback:
            self._callbacks[path] = onchangecallback

    def add_mandatory_paths(
        self,
        processname: str,
        processversion: str,
        connection: str,
        deviceinstance: int,
        productid: int,
        productname: str,
        firmwareversion: str,
        hardwareversion: str,
        connected: int,
    ) -> None:
        self.add_path("/Mgmt/ProcessName", processname)
        self.add_path("/Mgmt/ProcessVersion", processversion)
        self.add_path("/Mgmt/Connection", connection)
        self.add_path("/DeviceInstance", deviceinstance)
        self.add_path("/ProductId", productid)
        self.add_path("/ProductName", productname)
        self.add_path("/FirmwareVersion", firmwareversion)
        self.add_path("/HardwareVersion", hardwareversion)
        self.add_path("/Connected", connected)

    def register(self) -> None:
        return None

    def set_value(self, path: str, value: object) -> None:
        callback = self._callbacks.get(path)
        if callback is None or callback(path, value):
            self._paths[path] = value

    def __getitem__(self, path: str) -> object:
        return self._paths[path]

    def __setitem__(self, path: str, value: object) -> None:
        self._paths[path] = value


def _prime_vedbus_import_path() -> None:
    # dbus-autoterm carries velib_python locally so vedbus is available without system-wide packaging.
    app_root = Path(__file__).resolve().parent
    candidate = app_root / "ext" / "velib_python"
    if candidate.exists():
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(1, candidate_str)


def build_vedbus_service(service_name: str):
    _prime_vedbus_import_path()
    try:
        from vedbus import VeDbusService

        return VeDbusService(service_name, register=False)
    except Exception as exc:
        raise RuntimeError("VeDbusService is not available. Provide velib_python under ext/velib_python.") from exc


@dataclass
class DriverConfig:
    service_name: str = "com.victronenergy.generator.autoterm_air2d"
    device_instance: int = 287
    product_id: int = 0
    product_name: str = "Autoterm Integration for Victron GX"
    firmware_version: str = "0.1.0"
    hardware_version: str = "AIR2D"
    connection: str = "UART"


class GeneratorDbusAdapter:
    # Maps HeaterSnapshot state into a Venus generator-style D-Bus service shape.
    def __init__(
        self,
        config: DriverConfig | None = None,
        service=None,
        on_startstop: Callable[[bool], bool] | None = None,
    ) -> None:
        self.config = config or DriverConfig()
        self.service = service or build_vedbus_service(self.config.service_name)
        self._on_startstop = on_startstop
        self._on_mode_change: Callable[[int], bool] | None = None
        self._on_target_temperature_change: Callable[[int], bool] | None = None
        self._on_power_level_change: Callable[[int], bool] | None = None
        self._init_service()

    def _init_service(self) -> None:
        self.service.add_mandatory_paths(
            processname=__file__,
            processversion=self.config.firmware_version,
            connection=self.config.connection,
            deviceinstance=self.config.device_instance,
            productid=self.config.product_id,
            productname=self.config.product_name,
            firmwareversion=self.config.firmware_version,
            hardwareversion=self.config.hardware_version,
            connected=1,
        )
        self.service.add_path("/CustomName", self.config.product_name)
        self.service.add_path("/State", int(HeaterPhase.OFF))
        self.service.add_path("/StatusCode", 1)
        self.service.add_path("/StatusCodeMajor", 0)
        self.service.add_path("/StatusCodeMinor", 1)
        self.service.add_path("/StatusText", "off")
        self.service.add_path("/StartStop", 0, writeable=True, onchangecallback=self._handle_startstop)
        self.service.add_path("/ErrorCode", 0)
        self.service.add_path("/Runtime", 0)
        self.service.add_path("/Alarms/Communication", 0)
        self.service.add_path("/Dc/0/Voltage", 0.0)
        self.service.add_path("/Temperatures/Heater", None)
        self.service.add_path("/Temperatures/External", None)
        self.service.add_path("/Settings/Mode", 4, writeable=True, onchangecallback=self._handle_mode_change)
        self.service.add_path(
            "/Settings/TargetTemperature",
            15,
            writeable=True,
            onchangecallback=self._handle_target_temperature_change,
        )
        self.service.add_path(
            "/Settings/PowerLevel",
            2,
            writeable=True,
            onchangecallback=self._handle_power_level_change,
        )
        self.service.register()

    def _handle_startstop(self, path: str, value: object) -> bool:
        del path
        if self._on_startstop is None:
            return False
        return self._on_startstop(bool(value))

    def _handle_mode_change(self, path: str, value: object) -> bool:
        del path
        if self._on_mode_change is None:
            return False
        return self._on_mode_change(int(value))

    def _handle_target_temperature_change(self, path: str, value: object) -> bool:
        del path
        if self._on_target_temperature_change is None:
            return False
        return self._on_target_temperature_change(int(value))

    def _handle_power_level_change(self, path: str, value: object) -> bool:
        del path
        if self._on_power_level_change is None:
            return False
        return self._on_power_level_change(int(value))

    def publish_snapshot(self, snapshot: HeaterSnapshot, connected: bool) -> None:
        is_connected = bool(connected and snapshot.connected)
        status_code = (snapshot.telemetry.status_code_major * 100) + snapshot.telemetry.status_code_minor
        self.service["/Connected"] = 1 if is_connected else 0
        self.service["/State"] = int(snapshot.phase)
        self.service["/StatusCode"] = status_code
        self.service["/StatusCodeMajor"] = snapshot.telemetry.status_code_major
        self.service["/StatusCodeMinor"] = snapshot.telemetry.status_code_minor
        self.service["/StatusText"] = STATUS_TEXT.get(snapshot.phase, "unknown")
        self.service["/StartStop"] = 1 if snapshot.phase in {HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING} else 0
        self.service["/ErrorCode"] = snapshot.telemetry.error_code
        self.service["/Runtime"] = snapshot.runtime_seconds
        self.service["/Alarms/Communication"] = 0 if is_connected else 2
        self.service["/Dc/0/Voltage"] = snapshot.telemetry.battery_voltage_v
        self.service["/Temperatures/Heater"] = snapshot.telemetry.heater_temperature_c
        self.service["/Temperatures/External"] = snapshot.telemetry.external_temperature_c
        self.service["/Settings/Mode"] = int(snapshot.settings.mode)
        self.service["/Settings/TargetTemperature"] = snapshot.settings.setpoint_c
        self.service["/Settings/PowerLevel"] = snapshot.settings.power_level

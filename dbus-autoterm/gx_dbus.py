from __future__ import annotations

import os
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
        import dbus
        from vedbus import VeDbusService
    except Exception as exc:
        raise RuntimeError("VeDbusService is not available. Provide velib_python under ext/velib_python.") from exc

    try:
        if "DBUS_SESSION_BUS_ADDRESS" in os.environ:
            try:
                bus = dbus.SessionBus(private=True)
            except TypeError:
                bus = dbus.SessionBus()
        else:
            try:
                bus = dbus.SystemBus(private=True)
            except TypeError:
                bus = dbus.SystemBus()
        return VeDbusService(service_name, bus=bus, register=False)
    except Exception as exc:
        raise RuntimeError(f"Failed to create VeDbusService for {service_name}: {exc}") from exc


@dataclass
class DriverConfig:
    service_name: str = "com.victronenergy.genset.autoterm_air2d"
    startstop_service_name: str = "com.victronenergy.generator.startstop1"
    device_instance: int = 287
    startstop_device_instance: int = 1
    product_id: int = 0xC06B
    product_name: str = "Autoterm Integration for Victron GX"
    startstop_product_name: str = "Generator start/stop"
    firmware_version: str = "0.1.0"
    hardware_version: str = "AIR2D"
    connection: str = "UART"


class GeneratorDbusAdapter:
    # Maps HeaterSnapshot state into a temporary Venus genset service shape.
    def __init__(
        self,
        config: DriverConfig | None = None,
        service=None,
        startstop_service=None,
        on_startstop: Callable[[bool], bool] | None = None,
    ) -> None:
        self.config = config or DriverConfig()
        self.service = service or build_vedbus_service(self.config.service_name)
        self.startstop_service = startstop_service or build_vedbus_service(self.config.startstop_service_name)
        self._on_startstop = on_startstop
        self._on_mode_change: Callable[[int], bool] | None = None
        self._on_target_temperature_change: Callable[[int], bool] | None = None
        self._on_power_level_change: Callable[[int], bool] | None = None
        self._auto_start_enabled = 0
        self._manual_start_requested = 0
        self._manual_running_latch = 0
        self._manual_start_timer = 0
        self._init_service()
        self._init_startstop_service()

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
        self.service.add_path("/Role", "genset")
        self.service.add_path("/NrOfPhases", 1)
        self.service.add_path("/RemoteStartModeEnabled", 1)
        self.service.add_path("/Start", 0)
        self.service.add_path("/AutoStart", 0)
        self.service.add_path("/State", int(HeaterPhase.OFF))
        self.service.add_path("/StatusCode", 0)
        self.service.add_path("/StatusCodeMajor", 0)
        self.service.add_path("/StatusCodeMinor", 1)
        self.service.add_path("/StatusText", "off")
        self.service.add_path("/StartStop", 0, writeable=True, onchangecallback=self._handle_startstop)
        self.service.add_path("/ErrorCode", 0)
        self.service.add_path("/Error/0/Id", "")
        self.service.add_path("/Runtime", 0)
        self.service.add_path("/Alarms/Communication", 0)
        self.service.add_path("/Ac/Frequency", 0.0)
        self.service.add_path("/Ac/Power", 0)
        self.service.add_path("/Ac/L1/Voltage", 0.0)
        self.service.add_path("/Ac/L1/Current", 0.0)
        self.service.add_path("/Ac/L1/Power", 0)
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

    def _init_startstop_service(self) -> None:
        self.startstop_service.add_mandatory_paths(
            processname=__file__,
            processversion=self.config.firmware_version,
            connection="generator",
            deviceinstance=self.config.startstop_device_instance,
            productid=0,
            productname=self.config.startstop_product_name,
            firmwareversion=self.config.firmware_version,
            hardwareversion=self.config.hardware_version,
            connected=1,
        )
        self.startstop_service.add_path("/Enabled", 1)
        self.startstop_service.add_path(
            "/AutoStartEnabled",
            0,
            writeable=True,
            onchangecallback=self._handle_autostart_enabled,
        )
        self.startstop_service.add_path(
            "/ManualStart",
            0,
            writeable=True,
            onchangecallback=self._handle_manual_start,
        )
        self.startstop_service.add_path(
            "/ManualStartTimer",
            0,
            writeable=True,
            onchangecallback=self._handle_manual_start_timer,
        )
        self.startstop_service.add_path("/State", 0)
        self.startstop_service.add_path("/RunningByConditionCode", 0)
        self.startstop_service.add_path("/Runtime", 0)
        self.startstop_service.add_path("/Error", 0)
        self.startstop_service.add_path("/GensetInstance", self.config.device_instance)
        self.startstop_service.add_path("/GensetService", self.config.service_name)
        self.startstop_service.add_path("/GensetServiceType", "genset")
        self.startstop_service.add_path("/Capabilities", 0)
        self.startstop_service.add_path("/Type", 1)
        self.startstop_service.register()

    def _handle_startstop(self, path: str, value: object) -> bool:
        del path
        if self._on_startstop is None:
            return False
        enabled = bool(value)
        if not self._on_startstop(enabled):
            return False
        self._manual_start_requested = 1 if enabled else 0
        if enabled:
            self._manual_running_latch = 1
        return True

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

    def _handle_autostart_enabled(self, path: str, value: object) -> bool:
        del path
        self._auto_start_enabled = 1 if bool(value) else 0
        return True

    def _handle_manual_start_timer(self, path: str, value: object) -> bool:
        del path
        self._manual_start_timer = max(0, int(value))
        return True

    def _handle_manual_start(self, path: str, value: object) -> bool:
        del path
        if self._on_startstop is None:
            return False
        enabled = bool(value)
        if not self._on_startstop(enabled):
            return False
        self._manual_start_requested = 1 if enabled else 0
        if enabled:
            self._manual_running_latch = 1
        return True

    def _genset_status_code(self, snapshot: HeaterSnapshot, is_connected: bool) -> int:
        if not is_connected or snapshot.telemetry.error_code:
            return 10
        if snapshot.phase == HeaterPhase.OFF:
            return 0
        if snapshot.phase == HeaterPhase.STARTING:
            return 1
        if snapshot.phase == HeaterPhase.WARMING_UP:
            return 4
        if snapshot.phase == HeaterPhase.RUNNING:
            return 8
        return 9

    def _generator_state(self, snapshot: HeaterSnapshot, is_connected: bool) -> int:
        if not is_connected or snapshot.telemetry.error_code:
            return 10
        if snapshot.phase == HeaterPhase.OFF:
            return 0
        if snapshot.phase in {HeaterPhase.STARTING, HeaterPhase.WARMING_UP}:
            return 2
        if snapshot.phase == HeaterPhase.RUNNING:
            return 1
        return 3

    def _running_by_condition(self, snapshot: HeaterSnapshot, is_connected: bool) -> int:
        if not is_connected or snapshot.telemetry.error_code or snapshot.phase == HeaterPhase.OFF:
            return 0
        return 1 if self._manual_running_latch else 0

    def _ac_metrics(self, snapshot: HeaterSnapshot) -> tuple[float, float, int]:
        if snapshot.phase not in {HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING, HeaterPhase.SHUTTING_DOWN}:
            return 0.0, 0.0, 0
        if snapshot.phase == HeaterPhase.RUNNING:
            voltage = 230.0
            power = 900 + (snapshot.settings.power_level * 350)
        elif snapshot.phase == HeaterPhase.SHUTTING_DOWN:
            voltage = 230.0
            power = 250
        else:
            voltage = 230.0
            power = 500
        current = round(power / voltage, 2)
        return voltage, current, power

    def publish_snapshot(self, snapshot: HeaterSnapshot, connected: bool) -> None:
        is_connected = bool(connected and snapshot.connected)
        if snapshot.phase == HeaterPhase.OFF:
            self._manual_running_latch = 0
        genset_status_code = self._genset_status_code(snapshot, is_connected)
        ac_voltage, ac_current, ac_power = self._ac_metrics(snapshot)
        generator_state = self._generator_state(snapshot, is_connected)
        running_by_condition = self._running_by_condition(snapshot, is_connected)

        self.service["/Connected"] = 1 if is_connected else 0
        self.service["/State"] = generator_state
        self.service["/StatusCode"] = genset_status_code
        self.service["/StatusCodeMajor"] = snapshot.telemetry.status_code_major
        self.service["/StatusCodeMinor"] = snapshot.telemetry.status_code_minor
        self.service["/StatusText"] = STATUS_TEXT.get(snapshot.phase, "unknown")
        self.service["/StartStop"] = 1 if snapshot.phase in {HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING} else 0
        self.service["/Start"] = self.service["/StartStop"]
        self.service["/AutoStart"] = self._auto_start_enabled
        self.service["/ErrorCode"] = snapshot.telemetry.error_code
        self.service["/Error/0/Id"] = "" if snapshot.telemetry.error_code == 0 else str(snapshot.telemetry.error_code)
        self.service["/Runtime"] = snapshot.runtime_seconds
        self.service["/Alarms/Communication"] = 0 if is_connected else 2
        self.service["/Ac/Frequency"] = 50.0 if ac_power else 0.0
        self.service["/Ac/Power"] = ac_power
        self.service["/Ac/L1/Voltage"] = ac_voltage
        self.service["/Ac/L1/Current"] = ac_current
        self.service["/Ac/L1/Power"] = ac_power
        self.service["/Dc/0/Voltage"] = snapshot.telemetry.battery_voltage_v
        self.service["/Temperatures/Heater"] = snapshot.telemetry.heater_temperature_c
        self.service["/Temperatures/External"] = snapshot.telemetry.external_temperature_c
        self.service["/Settings/Mode"] = int(snapshot.settings.mode)
        self.service["/Settings/TargetTemperature"] = snapshot.settings.setpoint_c
        self.service["/Settings/PowerLevel"] = snapshot.settings.power_level
        self.startstop_service["/Connected"] = 1 if is_connected else 0
        self.startstop_service["/AutoStartEnabled"] = self._auto_start_enabled
        self.startstop_service["/ManualStart"] = self._manual_start_requested
        self.startstop_service["/ManualStartTimer"] = self._manual_start_timer
        self.startstop_service["/State"] = generator_state
        self.startstop_service["/RunningByConditionCode"] = running_by_condition
        self.startstop_service["/Runtime"] = snapshot.runtime_seconds
        self.startstop_service["/Error"] = snapshot.telemetry.error_code if snapshot.telemetry.error_code else (1 if not is_connected else 0)

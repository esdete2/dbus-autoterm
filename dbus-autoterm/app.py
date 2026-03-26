from __future__ import annotations

import argparse
import logging
import sys
from configparser import ConfigParser
from dataclasses import dataclass, field, replace
from pathlib import Path

from domain import HeaterPhase, OperatingMode
from gx_dbus import DriverConfig, HeaterDbusAdapter, HeaterUiMode, MockVeDbusService
from provider import DummyHeaterProvider, SerialHeaterProvider, SerialProviderConfig
from room_sensor import DbusRoomTemperatureReader, NullRoomTemperatureReader

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    backend: str = "dummy"
    serial_device: str | None = None
    room_temperature_service: str = "auto"
    poll_interval: float = 1.0
    log_level: str = "INFO"
    mock_dbus: bool = False
    driver_config: DriverConfig = field(default_factory=DriverConfig)


class HeaterDriverApp:
    def __init__(
        self,
        provider,
        dbus_adapter: HeaterDbusAdapter,
        room_temperature_reader=None,
        config_path: Path | None = None,
    ) -> None:
        self.provider = provider
        self.dbus_adapter = dbus_adapter
        self.room_temperature_reader = room_temperature_reader or NullRoomTemperatureReader()
        self.config_path = config_path

    def startstop(self, enabled: bool) -> bool:
        if enabled:
            if self.dbus_adapter.current_heater_mode == HeaterUiMode.VENTILATION:
                snapshot = self.provider.start_ventilation(self.provider.get_snapshot().settings.power_level)
            else:
                snapshot = self.provider.start(self.provider.get_snapshot().settings)
        else:
            snapshot = self.provider.stop()
        self.dbus_adapter.publish_snapshot(snapshot, self.provider.get_health().connected)
        return True

    def run_once(self) -> None:
        snapshot = self.provider.refresh()
        room_temperature = self.room_temperature_reader.refresh()
        self.dbus_adapter.publish_snapshot(snapshot, self.provider.get_health().connected, room_temperature)
        self.dbus_adapter.publish_room_temperature_services(
            self.room_temperature_reader.available_services(),
            self.room_temperature_reader.selected_service,
        )

    def poll(self) -> bool:
        self.run_once()
        return True

    def update_mode(self, mode: int) -> bool:
        return self._update_settings(mode=OperatingMode(int(mode)))

    def update_target_temperature(self, setpoint_c: int) -> bool:
        return self._update_settings(setpoint_c=int(setpoint_c))

    def update_power_level(self, power_level: int) -> bool:
        return self._update_settings(power_level=int(power_level))

    def update_room_temperature_service(self, service_name: str) -> bool:
        normalized = service_name or "auto"
        self.room_temperature_reader.set_selected_service(normalized)
        self._persist_room_temperature_service(normalized)
        self.run_once()
        return True

    def _update_settings(self, **changes) -> bool:
        current_snapshot = self.provider.get_snapshot()
        settings = replace(current_snapshot.settings, **changes)
        active = current_snapshot.phase in {HeaterPhase.STARTING, HeaterPhase.WARMING_UP, HeaterPhase.RUNNING}
        if self.dbus_adapter.current_heater_mode == HeaterUiMode.VENTILATION:
            current_snapshot.settings = settings
            snapshot = self.provider.start_ventilation(settings.power_level) if active else current_snapshot
        else:
            snapshot = self.provider.update_settings(settings)
        self.dbus_adapter.publish_snapshot(snapshot, self.provider.get_health().connected)
        return True

    def _persist_room_temperature_service(self, service_name: str) -> None:
        if self.config_path is None:
            return
        config = ConfigParser()
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as handle:
                config.read_file(handle)
        if not config.has_section("driver"):
            config.add_section("driver")
        config.set("driver", "room_temperature_service", service_name)
        with self.config_path.open("w", encoding="utf-8") as handle:
            config.write(handle)


def _load_config(path: Path | None) -> ConfigParser | None:
    if path is None:
        return None
    config = ConfigParser()
    with path.open("r", encoding="utf-8") as handle:
        config.read_file(handle)
    return config


def _config_get(config: ConfigParser | None, section: str, option: str, fallback):
    if config is None or not config.has_option(section, option):
        return fallback
    return config.get(section, option, fallback=fallback)


def _config_getint(config: ConfigParser | None, section: str, option: str, fallback: int) -> int:
    if config is None or not config.has_option(section, option):
        return fallback
    return config.getint(section, option, fallback=fallback)


def _config_getfloat(config: ConfigParser | None, section: str, option: str, fallback: float) -> float:
    if config is None or not config.has_option(section, option):
        return fallback
    return config.getfloat(section, option, fallback=fallback)


def _config_getboolean(config: ConfigParser | None, section: str, option: str, fallback: bool) -> bool:
    if config is None or not config.has_option(section, option):
        return fallback
    return config.getboolean(section, option, fallback=fallback)


def _build_runtime_config(args: argparse.Namespace, arg_list: list[str], config: ConfigParser | None) -> RuntimeConfig:
    backend = args.backend if "--backend" in arg_list else _config_get(config, "driver", "backend", args.backend)
    serial_device = (
        args.serial_device
        if args.serial_device is not None
        else _config_get(config, "driver", "serial_device", None)
    )
    room_temperature_service = (
        args.room_temperature_service
        if "--room-temperature-service" in arg_list and args.room_temperature_service is not None
        else _config_get(config, "driver", "room_temperature_service", "auto")
    )
    poll_interval = (
        args.poll_interval
        if "--poll-interval" in arg_list
        else _config_getfloat(config, "driver", "poll_interval", args.poll_interval)
    )
    log_level = (
        args.log_level if "--log-level" in arg_list else _config_get(config, "driver", "log_level", args.log_level)
    )
    mock_dbus = args.mock_dbus or _config_getboolean(config, "driver", "mock_dbus", False)
    driver_config = DriverConfig(
        service_name=args.service_name or _config_get(config, "dbus", "service_name", DriverConfig.service_name),
        device_instance=(
            args.device_instance
            if args.device_instance is not None
            else _config_getint(config, "dbus", "device_instance", DriverConfig.device_instance)
        ),
        product_name=args.product_name or _config_get(config, "dbus", "product_name", DriverConfig.product_name),
        firmware_version=(
            args.firmware_version or _config_get(config, "dbus", "firmware_version", DriverConfig.firmware_version)
        ),
        hardware_version=(
            args.hardware_version or _config_get(config, "dbus", "hardware_version", DriverConfig.hardware_version)
        ),
        connection=args.connection or _config_get(config, "dbus", "connection", DriverConfig.connection),
    )
    return RuntimeConfig(
        backend=backend,
        serial_device=serial_device,
        room_temperature_service=room_temperature_service,
        poll_interval=poll_interval,
        log_level=log_level,
        mock_dbus=mock_dbus,
        driver_config=driver_config,
    )


def _run_with_glib(app: HeaterDriverApp, poll_interval: float) -> None:
    from gi.repository import GLib

    interval_ms = max(100, int(poll_interval * 1000))
    loop = GLib.MainLoop()

    def _poll() -> bool:
        try:
            return app.poll()
        except Exception:
            LOG.exception("poll cycle failed")
            return True

    GLib.timeout_add(interval_ms, _poll)
    loop.run()


def _configure_venus_dbus_runtime(mock_dbus: bool) -> bool:
    try:
        from gi.repository import GLib
    except ImportError as exc:
        raise RuntimeError("GLib is required for the dbus-autoterm runtime") from exc

    if not mock_dbus:
        try:
            from dbus.mainloop.glib import DBusGMainLoop
        except ImportError as exc:
            raise RuntimeError("dbus.mainloop.glib is required for the real D-Bus runtime") from exc
        DBusGMainLoop(set_as_default=True)

    del GLib
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dbus-autoterm driver")
    parser.add_argument("-c", "--config", type=Path, help="configuration file")
    parser.add_argument("--backend", choices=["dummy", "serial"], default="dummy")
    parser.add_argument("--serial-device")
    parser.add_argument("--room-temperature-service")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--service-name")
    parser.add_argument("--device-instance", type=int)
    parser.add_argument("--product-name")
    parser.add_argument("--firmware-version")
    parser.add_argument("--hardware-version")
    parser.add_argument("--connection")
    parser.add_argument("--mock-dbus", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    arg_list = argv if argv is not None else sys.argv[1:]
    config = _load_config(args.config)
    runtime = _build_runtime_config(args, arg_list, config)

    logging.basicConfig(level=getattr(logging, str(runtime.log_level).upper(), logging.INFO))
    _configure_venus_dbus_runtime(runtime.mock_dbus)

    if runtime.backend == "dummy":
        provider = DummyHeaterProvider()
    else:
        if not runtime.serial_device:
            raise SystemExit("--serial-device is required for --backend=serial")
        provider = SerialHeaterProvider(SerialProviderConfig(device=runtime.serial_device))

    try:
        provider.connect()
    except Exception:
        LOG.exception("initial provider connect failed; continuing in disconnected mode")
    service = MockVeDbusService(runtime.driver_config.service_name) if runtime.mock_dbus else None
    dbus_adapter = HeaterDbusAdapter(
        config=runtime.driver_config,
        service=service,
    )
    if runtime.mock_dbus:
        room_temperature_reader = NullRoomTemperatureReader()
    else:
        room_temperature_reader = DbusRoomTemperatureReader(selected_service=runtime.room_temperature_service)
    app = HeaterDriverApp(
        provider,
        dbus_adapter,
        room_temperature_reader=room_temperature_reader,
        config_path=args.config,
    )

    # Wire writable D-Bus paths to provider-backed state transitions.
    dbus_adapter._on_startstop = app.startstop
    dbus_adapter._on_mode_change = app.update_mode
    dbus_adapter._on_target_temperature_change = app.update_target_temperature
    dbus_adapter._on_power_level_change = app.update_power_level
    dbus_adapter._on_room_temperature_service_change = app.update_room_temperature_service

    try:
        try:
            app.run_once()
        except Exception:
            LOG.exception("initial refresh failed; continuing into poll loop")
        _run_with_glib(app, runtime.poll_interval)
    except KeyboardInterrupt:
        LOG.info("shutdown requested")
    finally:
        provider.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

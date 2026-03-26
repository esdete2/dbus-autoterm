from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RoomTemperatureReading:
    temperature_c: float | None = None
    source_text: str = "Unavailable"
    service_name: str | None = None


@dataclass(frozen=True)
class RoomTemperatureServiceInfo:
    service_name: str
    display_name: str
    temperature_c: float | None = None


class NullRoomTemperatureReader:
    selected_service = "auto"

    def refresh(self) -> RoomTemperatureReading:
        return RoomTemperatureReading()

    def available_services(self) -> list[RoomTemperatureServiceInfo]:
        return []

    def set_selected_service(self, service_name: str) -> None:
        self.selected_service = service_name or "auto"


class DbusRoomTemperatureReader:
    def __init__(self, selected_service: str = "auto", bus=None) -> None:
        self._selected_service = selected_service or "auto"
        self._bus = bus

    @property
    def selected_service(self) -> str:
        return self._selected_service

    def set_selected_service(self, service_name: str) -> None:
        self._selected_service = service_name or "auto"

    def refresh(self) -> RoomTemperatureReading:
        services = self._candidate_services()
        for service_name in services:
            reading = self._read_service(service_name)
            if reading is not None:
                return reading

        if self._selected_service not in {"", "auto"}:
            return RoomTemperatureReading(
                temperature_c=None,
                source_text="Configured Cerbo temperature sensor unavailable",
                service_name=self._selected_service,
            )
        return RoomTemperatureReading()

    def available_services(self) -> list[RoomTemperatureServiceInfo]:
        services: list[RoomTemperatureServiceInfo] = []
        for service_name in sorted(
            name for name in self._get_bus().list_names() if name.startswith("com.victronenergy.temperature.")
        ):
            info = self._service_info(service_name)
            if info is not None:
                services.append(info)
        return services

    def _candidate_services(self) -> list[str]:
        if self._selected_service not in {"", "auto"}:
            return [self._selected_service]
        names = [name for name in self._get_bus().list_names() if name.startswith("com.victronenergy.temperature.")]
        return sorted(names)

    def _service_info(self, service_name: str) -> RoomTemperatureServiceInfo | None:
        connected = self._get_value(service_name, "/Connected", 1)
        if connected in {0, "0", False}:
            return None
        temperature = self._get_value(service_name, "/Temperature", None)
        temperature_c = None
        if temperature is not None:
            try:
                temperature_c = float(temperature)
            except (TypeError, ValueError):
                temperature_c = None
        name = self._get_value(service_name, "/CustomName", None) or self._get_value(service_name, "/ProductName", None)
        return RoomTemperatureServiceInfo(
            service_name=service_name,
            display_name=str(name or service_name),
            temperature_c=temperature_c,
        )

    def _read_service(self, service_name: str) -> RoomTemperatureReading | None:
        info = self._service_info(service_name)
        if info is None or info.temperature_c is None:
            return None
        return RoomTemperatureReading(
            temperature_c=info.temperature_c,
            source_text=info.display_name,
            service_name=service_name,
        )

    def _get_value(self, service_name: str, path: str, default):
        try:
            value = self._get_bus().get_object(service_name, path).GetValue(dbus_interface="com.victronenergy.BusItem")
        except Exception:
            return default
        if value == []:
            return default
        return value

    def _get_bus(self):
        if self._bus is not None:
            return self._bus

        import dbus

        if "DBUS_SESSION_BUS_ADDRESS" in os.environ:
            self._bus = dbus.SessionBus()
        else:
            self._bus = dbus.SystemBus()
        return self._bus

import unittest

from room_sensor import DbusRoomTemperatureReader


class _FakeObject:
    def __init__(self, value):
        self._value = value

    def GetValue(self, dbus_interface=None):
        del dbus_interface
        return self._value


class _FakeBus:
    def __init__(self, values):
        self._values = values

    def list_names(self):
        return sorted({service for service, _path in self._values.keys()})

    def get_object(self, service_name, path):
        if (service_name, path) not in self._values:
            raise KeyError(path)
        return _FakeObject(self._values[(service_name, path)])


class RoomSensorTests(unittest.TestCase):
    def test_auto_selects_first_connected_temperature_service(self):
        bus = _FakeBus(
            {
                ("com.victronenergy.temperature.a", "/Connected"): 1,
                ("com.victronenergy.temperature.a", "/Temperature"): 19.5,
                ("com.victronenergy.temperature.a", "/CustomName"): "Cabin",
                ("com.victronenergy.temperature.b", "/Connected"): 1,
                ("com.victronenergy.temperature.b", "/Temperature"): 17.0,
                ("com.victronenergy.temperature.b", "/CustomName"): "Garage",
            }
        )

        reading = DbusRoomTemperatureReader(bus=bus).refresh()

        self.assertEqual(reading.temperature_c, 19.5)
        self.assertEqual(reading.source_text, "Cabin")
        self.assertEqual(reading.service_name, "com.victronenergy.temperature.a")

    def test_explicit_service_is_used(self):
        bus = _FakeBus(
            {
                ("com.victronenergy.temperature.a", "/Connected"): 1,
                ("com.victronenergy.temperature.a", "/Temperature"): 19.5,
                ("com.victronenergy.temperature.a", "/CustomName"): "Cabin",
                ("com.victronenergy.temperature.b", "/Connected"): 1,
                ("com.victronenergy.temperature.b", "/Temperature"): 17.0,
                ("com.victronenergy.temperature.b", "/CustomName"): "Garage",
            }
        )

        reading = DbusRoomTemperatureReader(
            selected_service="com.victronenergy.temperature.b",
            bus=bus,
        ).refresh()

        self.assertEqual(reading.temperature_c, 17.0)
        self.assertEqual(reading.source_text, "Garage")
        self.assertEqual(reading.service_name, "com.victronenergy.temperature.b")

    def test_unavailable_explicit_service_reports_unavailable(self):
        bus = _FakeBus({})

        reading = DbusRoomTemperatureReader(
            selected_service="com.victronenergy.temperature.missing",
            bus=bus,
        ).refresh()

        self.assertIsNone(reading.temperature_c)
        self.assertEqual(reading.source_text, "Configured Cerbo temperature sensor unavailable")
        self.assertEqual(reading.service_name, "com.victronenergy.temperature.missing")


if __name__ == "__main__":
    unittest.main()

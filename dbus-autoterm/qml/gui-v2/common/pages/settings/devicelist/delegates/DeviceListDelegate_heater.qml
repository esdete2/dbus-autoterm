import QtQuick
import Victron.VenusOS

DeviceListDelegate {
	id: root

	secondaryText: communicationAlarm.valid && communicationAlarm.value !== 0
		? "Communication problem"
		: (errorText.valid && errorText.value !== ""
			? errorText.value
			: (!controlTemperature.valid
				? stateLabel(heaterState.value)
				: ""))
	quantityModel: QuantityObjectModel {
		filterType: QuantityObjectModel.HasValue

		QuantityObject { object: controlTemperature; unit: Global.systemSettings.temperatureUnit }
	}

	onClicked: {
		Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeater.qml", {
			bindPrefix: root.device.serviceUid,
		})
	}

	VeQuickItem {
		id: heaterState
		uid: root.device.serviceUid + "/State"
	}

	VeQuickItem {
		id: controlTemperature
		uid: root.device.serviceUid + "/Temperatures/Control"
	}

	VeQuickItem {
		id: errorText
		uid: root.device.serviceUid + "/ErrorText"
	}

	VeQuickItem {
		id: communicationAlarm
		uid: root.device.serviceUid + "/Alarms/Communication"
	}

	function stateLabel(value) {
		switch (value) {
		case 0:
			return "Off"
		case 1:
			return "Starting"
		case 2:
			return "Warming up"
		case 3:
			return "Running"
		case 4:
			return "Shutting down"
		case 10:
			return "Error"
		default:
			return "Not connected"
		}
	}
}

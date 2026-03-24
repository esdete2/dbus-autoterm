import QtQuick
import Victron.VenusOS

DeviceListDelegate {
	id: root

	secondaryText: !controlTemperature.valid && !batteryVoltage.valid && stateText.valid
		? stateText.value
		: (stateText.valid ? "" : CommonWords.not_connected)
	quantityModel: QuantityObjectModel {
		filterType: QuantityObjectModel.HasValue

		QuantityObject { object: controlTemperature; unit: Global.systemSettings.temperatureUnit }
		QuantityObject { object: batteryVoltage; unit: VenusOS.Units_Volt_DC }
	}

	onClicked: {
		Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeater.qml", {
			bindPrefix: root.device.serviceUid,
		})
	}

	VeQuickItem {
		id: stateText
		uid: root.device.serviceUid + "/StateText"
	}

	VeQuickItem {
		id: controlTemperature
		uid: root.device.serviceUid + "/Temperatures/Control"
	}

	VeQuickItem {
		id: batteryVoltage
		uid: root.device.serviceUid + "/Dc/0/Voltage"
	}
}

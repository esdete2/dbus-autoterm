import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Room temperature sensor"

	GradientListView {
		model: (availableCount.valid ? availableCount.value : 0) + 1

		delegate: ListButton {
			required property int index
			readonly property bool automaticRow: index === 0
			readonly property int sensorIndex: index - 1
			readonly property string sensorPrefix: root.bindPrefix + "/AvailableRoomSensors/" + sensorIndex
			text: automaticRow ? "Automatic" : (sensorName.valid ? sensorName.value : "")
			secondaryText: automaticRow
				? (selectedService.valid && selectedService.value === "auto" ? "Selected" : "")
				: (selectedService.valid && sensorService.valid && selectedService.value === sensorService.value
					? "Selected"
					: (sensorTemperature.valid
						? Number(sensorTemperature.value).toFixed(1) + Units.defaultUnitString(Global.systemSettings.temperatureUnit)
						: ""))
			onClicked: {
				if (automaticRow) {
					selectedService.setValue("auto")
				} else if (sensorService.valid && sensorService.value !== "") {
					selectedService.setValue(sensorService.value)
				}
			}

			VeQuickItem {
				id: sensorName
				uid: sensorPrefix + "/Name"
			}

			VeQuickItem {
				id: sensorService
				uid: sensorPrefix + "/Service"
			}

			VeQuickItem {
				id: sensorTemperature
				uid: sensorPrefix + "/Temperature"
			}
		}
	}

	VeQuickItem {
		id: selectedService
		uid: root.bindPrefix + "/Settings/RoomTemperatureService"
	}

	VeQuickItem {
		id: availableCount
		uid: root.bindPrefix + "/AvailableRoomSensors/Count"
	}
}

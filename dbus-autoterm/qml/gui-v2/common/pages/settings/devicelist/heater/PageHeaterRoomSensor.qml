import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Room temperature sensor"

	GradientListView {
		model: VisibleItemModel {
			ListButton {
				text: "Automatic"
				secondaryText: selectedService.valid && selectedService.value === "auto" ? "Selected" : ""
				onClicked: selectedService.setValue("auto")
			}

			Repeater {
				model: availableCount.valid ? availableCount.value : 0

				delegate: ListButton {
					required property int index
					readonly property string sensorPrefix: root.bindPrefix + "/AvailableRoomSensors/" + index
					text: sensorName.valid ? sensorName.value : ""
					secondaryText: selectedService.valid && sensorService.valid && selectedService.value === sensorService.value
						? "Selected"
						: (sensorTemperature.valid ? sensorTemperature.value.toFixed(1) + Units.defaultUnitString(Global.systemSettings.temperatureUnit) : "")
					onClicked: {
						if (sensorService.valid && sensorService.value !== "") {
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

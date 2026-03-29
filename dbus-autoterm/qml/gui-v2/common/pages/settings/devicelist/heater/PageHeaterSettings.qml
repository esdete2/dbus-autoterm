import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Heater settings"

	GradientListView {
		model: VisibleItemModel {
			ListNavigation {
				text: "Room temperature sensor"
				secondaryText: roomTemperatureServiceText.valid ? roomTemperatureServiceText.value : ""
				onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterRoomSensor.qml", {
					bindPrefix: root.bindPrefix,
				})

				VeQuickItem {
					id: roomTemperatureServiceText
					uid: root.bindPrefix + "/Settings/RoomTemperatureServiceText"
				}
			}

			ListText {
				text: "Room temperature source"
				dataItem.uid: root.bindPrefix + "/Temperatures/RoomSourceText"
				secondaryText: dataItem.valid ? dataItem.value : ""
			}

			ListText {
				text: "Temperature control"
				dataItem.uid: root.bindPrefix + "/Capabilities/RoomTemperatureControl"
				secondaryText: dataItem.valid && dataItem.value === 1 ? "Available" : "Unavailable"
			}
		}
	}
}

import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Live data"

	GradientListView {
		model: VisibleItemModel {
			ListTemperature {
				text: "Control temperature"
				dataItem.uid: root.bindPrefix + "/Temperatures/Control"
				preferredVisible: dataItem.valid
			}

			ListTemperature {
				text: "Internal temperature"
				dataItem.uid: root.bindPrefix + "/Temperatures/Internal"
				preferredVisible: dataItem.valid
			}

			ListTemperature {
				text: "Heater temperature"
				dataItem.uid: root.bindPrefix + "/Temperatures/Heater"
				preferredVisible: dataItem.valid
			}

			ListQuantity {
				text: "Battery voltage"
				dataItem.uid: root.bindPrefix + "/Dc/0/Voltage"
				unit: VenusOS.Units_Volt_DC
			}

			ListQuantity {
				text: "Fan set"
				dataItem.uid: root.bindPrefix + "/Status/FanRpmSet"
				unit: VenusOS.Units_None
			}

			ListQuantity {
				text: "Fan actual"
				dataItem.uid: root.bindPrefix + "/Status/FanRpmActual"
				unit: VenusOS.Units_None
			}

			ListQuantity {
				text: "Fuel pump frequency"
				dataItem.uid: root.bindPrefix + "/Status/FuelPumpFrequency"
				unit: VenusOS.Units_None
			}
		}
	}
}

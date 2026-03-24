import QtQuick
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	serviceUid: bindPrefix

	showSwitches: false
	title: "Heater settings"

	settingsModel: VisibleItemModel {
		ListRadioButtonGroup {
			text: "Sensor source"
			dataItem.uid: root.bindPrefix + "/Settings/SensorSource"
			optionModel: [
				{ display: "Controller", value: 0 },
				{ display: "External", value: 1 },
				{ display: "Heater", value: 2 },
			]
		}

		ListText {
			text: "Selected source"
			dataItem.uid: root.bindPrefix + "/Settings/SensorSourceText"
			secondaryText: dataItem.valid ? dataItem.value : ""
		}

		ListSpinBox {
			text: CommonWords.temperature
			dataItem.uid: root.bindPrefix + "/Settings/TargetTemperature"
			from: 5
			to: 35
			stepSize: 1
			suffix: Units.defaultUnitString(Global.systemSettings.temperatureUnit)
		}

		ListSpinBox {
			text: "Power level"
			dataItem.uid: root.bindPrefix + "/Settings/PowerLevel"
			from: 1
			to: 9
			stepSize: 1
		}
	}
}

import QtQuick
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	required property int timerIndex
	serviceUid: bindPrefix
	readonly property string timerBindPrefix: root.bindPrefix + "/Timers/" + timerIndex

	showSwitches: false
	title: "Timer " + (timerIndex + 1)

	settingsModel: VisibleItemModel {
		ListSwitch {
			text: CommonWords.enabled
			dataItem.uid: root.timerBindPrefix + "/Enabled"
			valueTrue: 1
			valueFalse: 0
		}

		ListRadioButtonGroup {
			text: "Cycle"
			dataItem.uid: root.timerBindPrefix + "/Cycle"
			optionModel: [
				{ display: "Every day", value: 0 },
				{ display: "Weekdays", value: 1 },
				{ display: "Custom", value: 2 },
			]
		}

		ListSpinBox {
			text: "Days mask"
			dataItem.uid: root.timerBindPrefix + "/Days"
			from: 0
			to: 127
			stepSize: 1
		}

		ListSpinBox {
			text: "Start hour"
			dataItem.uid: root.timerBindPrefix + "/StartHour"
			from: 0
			to: 23
			stepSize: 1
		}

		ListSpinBox {
			text: "Start minute"
			dataItem.uid: root.timerBindPrefix + "/StartMinute"
			from: 0
			to: 59
			stepSize: 1
		}

		ListSpinBox {
			text: "Duration"
			dataItem.uid: root.timerBindPrefix + "/DurationMinutes"
			from: 1
			to: 1440
			stepSize: 5
			suffix: " min"
		}

		ListRadioButtonGroup {
			text: CommonWords.mode
			dataItem.uid: root.timerBindPrefix + "/Mode"
			optionModel: [
				{ display: "Power", value: 0 },
				{ display: "Temperature", value: 1 },
				{ display: "Ventilation", value: 2 },
				{ display: "Heat + ventilation", value: 3 },
			]
		}

		ListSpinBox {
			text: CommonWords.temperature
			dataItem.uid: root.timerBindPrefix + "/TargetTemperature"
			from: 5
			to: 35
			stepSize: 1
			suffix: Units.defaultUnitString(Global.systemSettings.temperatureUnit)
		}

		ListSpinBox {
			text: "Power level"
			dataItem.uid: root.timerBindPrefix + "/PowerLevel"
			from: 1
			to: 9
			stepSize: 1
		}
	}
}

import QtQuick
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	serviceUid: bindPrefix

	showSwitches: false

	settingsModel: VisibleItemModel {
		ListText {
			text: CommonWords.state
			dataItem.uid: root.bindPrefix + "/StateText"
			secondaryText: dataItem.valid ? dataItem.value : CommonWords.not_connected
		}

		ListText {
			text: CommonWords.mode
			dataItem.uid: root.bindPrefix + "/ModeText"
			secondaryText: dataItem.valid ? dataItem.value : ""
		}

		ListText {
			text: "Runtime"
			dataItem.uid: root.bindPrefix + "/Runtime"
			secondaryText: dataItem.valid ? Utils.secondsToString(dataItem.value, false) : "0"
		}

		ListText {
			text: CommonWords.error
			dataItem.uid: root.bindPrefix + "/ErrorText"
			preferredVisible: dataItem.valid && dataItem.value !== ""
			secondaryText: dataItem.valid ? dataItem.value : ""
		}

		ListButton {
			text: startStop.valid && startStop.value ? "Stop heater" : "Start heater"
			secondaryText: startStop.valid && startStop.value ? "Running" : "Idle"
			interactive: startStop.valid
			onClicked: startStop.setValue(startStop.value ? 0 : 1)

			VeQuickItem {
				id: startStop
				uid: root.bindPrefix + "/StartStop"
			}
		}

		ListRadioButtonGroup {
			text: CommonWords.mode
			dataItem.uid: root.bindPrefix + "/Mode"
			optionModel: [
				{ display: "Power", value: 0 },
				{ display: "Temperature", value: 1 },
				{ display: "Ventilation", value: 2 },
				{ display: "Heat + ventilation", value: 3 },
			]
		}

		ListSpinBox {
			text: CommonWords.temperature
			dataItem.uid: root.bindPrefix + "/Settings/TargetTemperature"
			preferredVisible: mode.valid && mode.value !== 0 && mode.value !== 2
			suffix: Units.defaultUnitString(Global.systemSettings.temperatureUnit)
			from: 5
			to: 35
			stepSize: 1
		}

		ListSpinBox {
			text: "Power level"
			dataItem.uid: root.bindPrefix + "/Settings/PowerLevel"
			from: 1
			to: 9
			stepSize: 1
		}

		ListQuantityGroup {
			text: "Live values"
			model: QuantityObjectModel {
				QuantityObject { object: controlTemperature; unit: Global.systemSettings.temperatureUnit }
				QuantityObject { object: batteryVoltage; unit: VenusOS.Units_Volt_DC }
				QuantityObject { object: fanRpmActual; unit: VenusOS.Units_None }
			}

			VeQuickItem {
				id: controlTemperature
				uid: root.bindPrefix + "/Temperatures/Control"
			}

			VeQuickItem {
				id: batteryVoltage
				uid: root.bindPrefix + "/Dc/0/Voltage"
			}

			VeQuickItem {
				id: fanRpmActual
				uid: root.bindPrefix + "/Status/FanRpmActual"
			}
		}

		ListNavigation {
			text: "Timers"
			onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterTimers.qml", {
				bindPrefix: root.bindPrefix,
			})
		}

		ListNavigation {
			text: "Live data"
			onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterLiveData.qml", {
				bindPrefix: root.bindPrefix,
			})
		}

		ListNavigation {
			text: "Diagnostics"
			onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterDiagnostics.qml", {
				bindPrefix: root.bindPrefix,
			})
		}

		ListNavigation {
			text: "Heater settings"
			onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterSettings.qml", {
				bindPrefix: root.bindPrefix,
			})
		}
	}

	VeQuickItem {
		id: mode
		uid: root.bindPrefix + "/Mode"
	}
}

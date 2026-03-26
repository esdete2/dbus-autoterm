import QtQuick
import QtQuick.Templates as T
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	serviceUid: bindPrefix
	readonly property bool isRunning: heaterState.valid && heaterState.value !== 0 && heaterState.value !== 10
	readonly property bool hasRoomTemperatureControl: roomTemperatureControl.valid && roomTemperatureControl.value === 1
	readonly property bool isVentilationMode: mode.valid && mode.value === 2
	readonly property bool showTemperatureControl: hasRoomTemperatureControl && mode.valid && (mode.value === 1 || mode.value === 3)
	readonly property bool showPowerControl: mode.valid && (mode.value === 0 || mode.value === 2)
	readonly property var modeOptions: hasRoomTemperatureControl
		? [
			{ display: "Power", value: 0 },
			{ display: "Temperature", value: 1 },
			{ display: "Ventilation", value: 2 },
			{ display: "Heat + ventilation", value: 3 },
		]
		: [
			{ display: "Power", value: 0 },
			{ display: "Ventilation", value: 2 },
		]
	readonly property string warningTitle: communicationAlarm.valid && communicationAlarm.value !== 0
		? "Communication problem"
		: (errorText.valid && errorText.value !== "" ? "Heater fault" : "")
	readonly property string warningText: communicationAlarm.valid && communicationAlarm.value !== 0
		? "The Cerbo cannot communicate with the heater."
		: (errorText.valid ? errorText.value : "")
	readonly property string actionLabel: isRunning
		? (isVentilationMode ? "Stop ventilation" : "Stop heater")
		: (isVentilationMode ? "Start ventilation" : "Start heater")
	readonly property string actionDescription: isRunning
		? (isVentilationMode
			? "The heater will stop ventilation mode."
			: "The heater will begin its shutdown cycle.")
		: (isVentilationMode
			? "The heater will start in ventilation mode."
			: "The heater will start heating with the current settings.")

	showSwitches: false
	settingsHeader: Item {
		width: root.width
		implicitHeight: warningBanner.visible ? warningBanner.implicitHeight + Theme.geometry_gradientList_spacing : 0

		Rectangle {
			id: warningBanner
			visible: root.warningText.length > 0
			width: parent.width - (Theme.geometry_page_content_horizontalMargin * 2)
			x: Theme.geometry_page_content_horizontalMargin
			y: Theme.geometry_gradientList_spacing
			radius: Theme.geometry_listItem_radius
			color: Theme.color_toastNotification_background_warning
			implicitHeight: bannerContent.implicitHeight + (Theme.geometry_listItem_content_verticalMargin * 2)

			Column {
				id: bannerContent
				width: parent.width - (Theme.geometry_listItem_content_horizontalMargin * 2)
				x: Theme.geometry_listItem_content_horizontalMargin
				y: Theme.geometry_listItem_content_verticalMargin
				spacing: Theme.geometry_listItem_content_verticalMargin / 2

				Label {
					width: parent.width
					text: root.warningTitle
					font.pixelSize: Theme.font_size_body2
					font.bold: true
					color: Theme.color_font_primary
					wrapMode: Text.Wrap
				}

				Label {
					width: parent.width
					text: root.warningText
					font.pixelSize: Theme.font_size_body1
					color: Theme.color_font_primary
					wrapMode: Text.Wrap
				}
			}
		}
	}

	settingsModel: VisibleItemModel {
		ListText {
			text: "State"
			dataItem.uid: root.bindPrefix + "/State"
			secondaryText: dataItem.valid ? root.stateLabel(dataItem.value) : "Not connected"
		}

		ListButton {
			text: "Heater control"
			secondaryText: root.actionLabel
			interactive: startStop.valid
			onClicked: Global.dialogLayer.open(startStopDialogComponent, {
				startRequested: !root.isRunning,
			})

			VeQuickItem {
				id: startStop
				uid: root.bindPrefix + "/StartStop"
			}
		}

		ListText {
			text: "Runtime"
			dataItem.uid: root.bindPrefix + "/Runtime"
			secondaryText: dataItem.valid ? Utils.secondsToString(dataItem.value, false) : "0"
		}

		ListRadioButtonGroup {
			text: "Mode"
			dataItem.uid: root.bindPrefix + "/Mode"
			optionModel: root.modeOptions
		}

		ListText {
			text: "Temperature control"
			preferredVisible: !root.hasRoomTemperatureControl
			secondaryText: "Unavailable: no room sensor"
		}

		ListSpinBox {
			text: "Temperature"
			dataItem.uid: root.bindPrefix + "/Settings/TargetTemperature"
			preferredVisible: root.showTemperatureControl
			suffix: Units.defaultUnitString(Global.systemSettings.temperatureUnit)
			from: 5
			to: 35
			stepSize: 1
		}

		ListSlider {
			text: "Power level"
			dataItem.uid: root.bindPrefix + "/Settings/PowerLevel"
			preferredVisible: root.showPowerControl
			slider.from: 1
			slider.to: 9
			slider.stepSize: 1
		}

		ListQuantityGroup {
			text: "Live values"
			model: QuantityObjectModel {
				QuantityObject { object: roomTemperature; unit: Global.systemSettings.temperatureUnit }
				QuantityObject { object: heaterTemperature; unit: Global.systemSettings.temperatureUnit }
			}

			VeQuickItem {
				id: roomTemperature
				uid: root.bindPrefix + "/Temperatures/Room"
			}

			VeQuickItem {
				id: heaterTemperature
				uid: root.bindPrefix + "/Temperatures/Heater"
			}
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

	VeQuickItem {
		id: heaterState
		uid: root.bindPrefix + "/State"
	}

	VeQuickItem {
		id: errorText
		uid: root.bindPrefix + "/ErrorText"
	}

	VeQuickItem {
		id: communicationAlarm
		uid: root.bindPrefix + "/Alarms/Communication"
	}

	VeQuickItem {
		id: roomTemperatureControl
		uid: root.bindPrefix + "/Capabilities/RoomTemperatureControl"
	}

	Component {
		id: startStopDialogComponent

		ModalWarningDialog {
			required property bool startRequested

			title: root.actionLabel + "?"
			description: root.actionDescription
			dialogDoneOptions: VenusOS.ModalDialog_DoneOptions_OkAndCancel
			acceptText: root.actionLabel
			onClosed: {
				if (result === T.Dialog.Accepted) {
					startStop.setValue(startRequested ? 1 : 0)
				}
			}
		}
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

/*
** Copyright (C) 2026 Victron Energy B.V.
** See LICENSE.txt for license information.
*/

import QtQuick
import QtQuick.Controls.impl as CP
import QtQuick.Templates as T
import Victron.VenusOS

SwipeViewPage {
	id: root

	required property var heaterModel

	property int currentHeaterIndex: 0
	property string pendingStartStopAction: ""

	readonly property int heaterCount: heaterModel ? heaterModel.count : 0
	readonly property var currentHeater: heaterModel ? heaterModel.deviceAt(currentHeaterIndex) : null
	readonly property string bindPrefix: currentHeater ? currentHeater.serviceUid : ""
	readonly property url heaterIcon: Qt.resolvedUrl("../images/heater_bottom_bar.svg")
	readonly property bool hasHeater: !!currentHeater
	readonly property bool isRunning: heaterState.valid && heaterState.value !== 0 && heaterState.value !== 10
	readonly property bool isStarting: pendingStartStopAction === "start"
	readonly property bool isStopping: pendingStartStopAction === "stop"
	readonly property bool isTransitioning: pendingStartStopAction !== ""
	readonly property bool hasRoomTemperatureControl: roomTemperatureControl.valid && roomTemperatureControl.value === 1
	readonly property bool isVentilationMode: mode.valid && mode.value === 2
	readonly property bool showTemperatureControl: hasRoomTemperatureControl && mode.valid && (mode.value === 1 || mode.value === 3)
	readonly property bool showPowerControl: mode.valid && (mode.value === 0 || mode.value === 2)
	readonly property color panelStrokeColor: Theme.color_listItem_secondaryText
	readonly property color ringProgressColor: themeBlueProbe.backgroundColor
	readonly property string actionLabel: isStarting
		? "Starting..."
		: (isStopping
			? "Stopping..."
			: (isRunning
				? (isVentilationMode ? "Stop ventilation" : "Stop heater")
				: (isVentilationMode ? "Start ventilation" : "Start heater")))
	readonly property string actionDescription: isRunning
		? (isVentilationMode
			? "The heater will stop ventilation mode."
			: "The heater will begin its shutdown cycle.")
		: (isVentilationMode
			? "The heater will start in ventilation mode."
			: "The heater will start heating with the current settings.")
	readonly property string activeModeCardKey: {
		if (!mode.valid) {
			return ""
		}
		switch (mode.value) {
		case 0:
			return "power"
		case 1:
			return "temperature"
		case 2:
			return "ventilation"
		case 3:
			return "heat-ventilation"
		default:
			return ""
		}
	}
	readonly property var modeCards: [
		{ key: "temperature", modeValue: 1, label: "Temperature", icon: "qrc:/images/icon_temp_32.svg", description: "Maintain a target room temperature." },
		{ key: "power", modeValue: 0, label: "Power", icon: root.heaterIcon, description: "Run the heater at a fixed power level." },
		{ key: "heat-ventilation", modeValue: 3, label: "Heat & Vent", icon: root.heaterIcon, description: "Blend heating with ventilation support." },
		{ key: "thermostat", modeValue: -1, label: "Thermostat", icon: "qrc:/images/icon_temp_coolant_32.svg", description: "Thermostat control placeholder for the custom GUI." },
		{ key: "ventilation", modeValue: 2, label: "Ventilation", icon: "qrc:/images/icon_propeller_32.png", description: "Circulate air without active heating." },
	]
	readonly property string activeModeDescription: {
		for (let i = 0; i < modeCards.length; ++i) {
			if (modeCards[i].key === activeModeCardKey) {
				return modeCards[i].description
			}
		}
		return "Select a heater mode to see more details here."
	}
	readonly property var tabModel: {
		const tabs = []
		if (!heaterModel) {
			return tabs
		}
		for (let i = 0; i < heaterModel.count; ++i) {
			const device = heaterModel.deviceAt(i)
			tabs.push({ value: device && device.name ? device.name : "Heater " + (i + 1) })
		}
		return tabs
	}
	readonly property real ringValueRatio: {
		if (showPowerControl && powerLevel.valid) {
			return clamp(powerLevel.value / 9.0, 0.0, 1.0)
		}
		if (showTemperatureControl && targetTemperature.valid) {
			return clamp((targetTemperature.value - 5.0) / 30.0, 0.0, 1.0)
		}
		return 1.0
	}
	readonly property string ringSecondaryValue: showPowerControl
		? (powerLevel.valid ? powerLevel.value : "--")
		: (showTemperatureControl ? formatTemperatureValue(targetTemperature) : "--")
	readonly property bool canAdjustRingValue: showPowerControl
		? powerLevel.valid
		: (showTemperatureControl && targetTemperature.valid)

	topLeftButton: VenusOS.StatusBar_LeftButton_ControlsInactive
	fullScreenWhenIdle: true
	focusPolicy: Qt.TabFocus
	navButtonText: "Heater"
	navButtonIcon: heaterIcon
	url: Qt.resolvedUrl("HeaterPage.qml")

	onHeaterCountChanged: {
		if (heaterCount === 0 || currentHeaterIndex >= heaterCount) {
			currentHeaterIndex = 0
		}
	}

	TabBar {
		id: tabBar

		visible: root.heaterCount > 1
		anchors {
			top: parent.top
			topMargin: Global.pageManager?.expandLayout ? -tabBar.height : 0
			horizontalCenter: parent.horizontalCenter
		}
		opacity: Global.pageManager?.interactivity === VenusOS.PageManager_InteractionMode_Interactive
				 || Global.pageManager?.interactivity === VenusOS.PageManager_InteractionMode_ExitIdleMode
				 ? 1.0
				 : 0.0

		Behavior on opacity {
			enabled: root.animationEnabled && root.isCurrentPage
			OpacityAnimator { duration: Theme.animation_page_idleOpacity_duration }
		}

		Behavior on anchors.topMargin {
			enabled: root.animationEnabled && root.isCurrentPage
			NumberAnimation { duration: Theme.animation_page_idleResize_duration; easing.type: Easing.InOutQuad }
		}

		model: root.tabModel
		currentIndex: root.currentHeaterIndex
		KeyNavigation.down: contentScope
		onButtonClicked: function(buttonIndex) {
			root.currentHeaterIndex = buttonIndex
		}
	}

	Button {
		id: themeBlueProbe
		visible: false
	}

	FocusScope {
		id: contentScope

		anchors {
			top: tabBar.bottom
			topMargin: Theme.geometry_page_content_verticalMargin
			left: parent.left
			leftMargin: Theme.geometry_page_content_horizontalMargin
			right: parent.right
			rightMargin: Theme.geometry_page_content_horizontalMargin
			bottom: parent.bottom
			bottomMargin: Theme.geometry_page_content_verticalMargin
		}

		EmptyPageItem {
			visible: !root.hasHeater
			anchors.centerIn: parent
			width: Math.min(parent.width, Theme.geometry_screen_width * 0.7)
			titleText: "Heater"
			imageSource: root.heaterIcon
			imageColor: Theme.color_font_primary
			primaryText: "No heaters available."
			secondaryText: "No heater service detected."
		}

		HeaterTab {
			id: heaterTab

			anchors.fill: parent
			animationEnabled: root.animationEnabled
			visible: root.hasHeater
			focus: visible
			model: root.hasHeater ? [root.currentHeater] : []

			delegate: Item {
				required property var modelData

				width: heaterTab.width
				height: heaterTab.height

				Flickable {
					id: leftPanel

					width: Math.max(parent.width - dialArea.width - 24, 0)
					anchors {
						top: parent.top
						left: parent.left
						bottom: parent.bottom
						right: dialArea.left
						rightMargin: 24
					}
					contentWidth: width
					contentHeight: leftContent.implicitHeight
					boundsBehavior: Flickable.StopAtBounds
					clip: true

					Column {
						id: leftContent

						width: leftPanel.width
						spacing: 18

						Row {
							width: parent.width
							spacing: 12

							Repeater {
								model: root.modeCards

								delegate: Item {
									required property var modelData

									readonly property bool active: modelData.key === root.activeModeCardKey
									readonly property bool roomSensorMode: modelData.modeValue === 1 || modelData.modeValue === 3
									readonly property bool supported: modelData.modeValue >= 0
									readonly property bool selectable: supported && (!roomSensorMode || root.hasRoomTemperatureControl)
									width: (leftContent.width - (4 * parent.spacing)) / 5
									height: 92

									Button {
										anchors.fill: parent
										text: ""
										flat: false
										enabled: selectable
										backgroundColor: active ? Theme.color_blue : Theme.color_gray1
										borderColor: active ? Theme.color_blue : Theme.color_gray1
										color: Theme.color_white
										onClicked: root.requestModeChange(modelData.modeValue, modelData.label)

										Column {
											anchors.centerIn: parent
											width: parent.width - 12
											spacing: 6

											CP.ColorImage {
												anchors.horizontalCenter: parent.horizontalCenter
												width: 26
												height: 26
												source: modelData.icon
												fillMode: Image.PreserveAspectFit
												color: Theme.color_white
											}

											Label {
												width: parent.width
												horizontalAlignment: Text.AlignHCenter
												wrapMode: Text.WordWrap
												maximumLineCount: 2
												text: modelData.label
												color: Theme.color_white
												font.pixelSize: Theme.font_size_caption
											}
										}
									}
								}
							}
						}

						Label {
							width: parent.width
							text: root.activeModeDescription
							wrapMode: Text.WordWrap
							color: Theme.color_font_secondary
							font.pixelSize: Theme.font_size_caption
						}
					}
				}

				Item {
					id: dialArea
					width: Math.min(parent.width / 3, 272)
					height: width + 108
					anchors {
						right: parent.right
						top: parent.top
					}

					CircularHeaterRing {
						id: ring
						width: parent.width
						height: parent.width
						anchors.top: parent.top
						anchors.horizontalCenter: parent.horizontalCenter
						valueRatio: root.ringValueRatio
						progressColor: Theme.color_blue
						primaryValue: root.formatTemperatureValue(roomTemperature)
						secondaryValue: root.ringSecondaryValue
					}

					Row {
						anchors.top: ring.bottom
						anchors.topMargin: -48
						anchors.horizontalCenter: ring.horizontalCenter
						spacing: 12

						Button {
							width: 56
							height: 56
							text: "–"
							enabled: root.canAdjustRingValue
							font.pixelSize: Theme.font_size_h2
							onClicked: root.adjustRingValue(-1)
						}

						Button {
							width: 56
							height: 56
							text: "+"
							enabled: root.canAdjustRingValue
							font.pixelSize: Theme.font_size_h2
							onClicked: root.adjustRingValue(1)
						}
					}

					Button {
						anchors.top: parent.top
						anchors.topMargin: ring.height + 56
						anchors.horizontalCenter: ring.horizontalCenter
						width: parent.width
						height: 52
						text: root.actionLabel
						enabled: startStop.valid && !root.isTransitioning
						flat: false
						backgroundColor: root.pendingStartStopAction === "start"
							? Theme.color_darkBlue
							: (root.pendingStartStopAction === "stop"
								? Theme.color_darkRed
								: (root.isRunning ? Theme.color_red : Theme.color_blue))
						borderColor: root.pendingStartStopAction === "start"
							? Theme.color_darkBlue
							: (root.pendingStartStopAction === "stop"
								? Theme.color_darkRed
								: (root.isRunning ? Theme.color_red : Theme.color_blue))
						color: Theme.color_white
						font.pixelSize: Theme.font_size_body1
						font.bold: true
						onClicked: Global.dialogLayer.open(startStopDialogComponent, {
							startRequested: !root.isRunning,
						})
					}
				}
			}
		}
	}

	VeQuickItem { id: mode; uid: root.bindPrefix + "/Mode" }
	VeQuickItem { id: heaterState; uid: root.bindPrefix + "/State" }
	VeQuickItem { id: startStop; uid: root.bindPrefix + "/StartStop" }
	VeQuickItem { id: roomTemperatureControl; uid: root.bindPrefix + "/Capabilities/RoomTemperatureControl" }
	VeQuickItem { id: roomTemperature; uid: root.bindPrefix + "/Temperatures/Room" }
	VeQuickItem { id: targetTemperature; uid: root.bindPrefix + "/Settings/TargetTemperature" }
	VeQuickItem { id: powerLevel; uid: root.bindPrefix + "/Settings/PowerLevel" }

	Connections {
		target: heaterState

		function onValueChanged() {
			if (root.pendingStartStopAction === "start" && (heaterState.value === 3 || heaterState.value === 0 || heaterState.value === 10)) {
				root.pendingStartStopAction = ""
			} else if (root.pendingStartStopAction === "stop" && (heaterState.value === 0 || heaterState.value === 10)) {
				root.pendingStartStopAction = ""
			}
		}
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
					root.pendingStartStopAction = startRequested ? "start" : "stop"
					startStop.setValue(startRequested ? 1 : 0)
				}
			}
		}
	}

	Component {
		id: modeChangeDialogComponent

		ModalWarningDialog {
			required property int requestedModeValue
			required property string requestedModeLabel

			title: "Change mode?"
			description: "The heater is running. Switch to " + requestedModeLabel + " now?"
			dialogDoneOptions: VenusOS.ModalDialog_DoneOptions_OkAndCancel
			acceptText: "Change mode"
			onClosed: {
				if (result === T.Dialog.Accepted) {
					root.selectMode(requestedModeValue)
				}
			}
		}
	}

	function clamp(value, minValue, maxValue) {
		return Math.max(minValue, Math.min(maxValue, value))
	}

	function formatTemperatureValue(item) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		return Number(Units.convert(item.value, VenusOS.Units_Temperature_Celsius, Global.systemSettings.temperatureUnit)).toFixed(0)
			+ Global.systemSettings.temperatureUnitSuffix
	}

	function adjustRingValue(delta) {
		if (showPowerControl && powerLevel.valid) {
			powerLevel.setValue(clamp(powerLevel.value + delta, 1, 9))
			return
		}
		if (showTemperatureControl && targetTemperature.valid) {
			targetTemperature.setValue(clamp(targetTemperature.value + delta, 5, 35))
		}
	}

	function selectMode(modeValue) {
		if (modeValue < 0) {
			return
		}
		if ((modeValue === 1 || modeValue === 3) && !hasRoomTemperatureControl) {
			return
		}
		mode.setValue(modeValue)
	}

	function requestModeChange(modeValue, modeLabel) {
		if (modeValue < 0 || !mode.valid || mode.value === modeValue) {
			return
		}
		if ((modeValue === 1 || modeValue === 3) && !hasRoomTemperatureControl) {
			return
		}
		if (isRunning) {
			Global.dialogLayer.open(modeChangeDialogComponent, {
				requestedModeValue: modeValue,
				requestedModeLabel: modeLabel,
			})
			return
		}
		selectMode(modeValue)
	}
}

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

	readonly property int heaterCount: heaterModel ? heaterModel.count : 0
	readonly property var currentHeater: heaterModel ? heaterModel.deviceAt(currentHeaterIndex) : null
	readonly property string bindPrefix: currentHeater ? currentHeater.serviceUid : ""
	readonly property url heaterIcon: Qt.resolvedUrl("../images/heater_bottom_bar.svg")
	readonly property bool hasHeater: !!currentHeater
	readonly property bool isRunning: heaterState.valid && heaterState.value !== 0 && heaterState.value !== 10
	readonly property bool hasRoomTemperatureControl: roomTemperatureControl.valid && roomTemperatureControl.value === 1
	readonly property bool isVentilationMode: mode.valid && mode.value === 2
	readonly property bool showTemperatureControl: hasRoomTemperatureControl && mode.valid && (mode.value === 1 || mode.value === 3)
	readonly property bool showPowerControl: mode.valid && (mode.value === 0 || mode.value === 2)
	readonly property bool hasFault: communicationAlarm.valid && communicationAlarm.value !== 0
		|| (errorText.valid && errorText.value !== "")
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
	readonly property color accentColor: hasFault
		? "#ff5f68"
		: (isVentilationMode ? "#49d6ff" : "#ffb13b")
	readonly property color accentDarkColor: hasFault
		? "#4a2024"
		: (isVentilationMode ? "#143748" : "#3e2b16")
	readonly property color accentFillColor: hasFault
		? "#5d2529"
		: (isVentilationMode ? "#173a47" : "#4a3420")
	readonly property color accentBorderColor: hasFault
		? "#ff8087"
		: (isVentilationMode ? "#6fe1ff" : "#ffc26a")
	readonly property color panelColor: "#171a1f"
	readonly property color panelRaisedColor: "#1f242b"
	readonly property color panelStrokeColor: Qt.rgba(1, 1, 1, 0.08)
	readonly property color subtleTextColor: Theme.color_font_secondary
	readonly property real sectionSpacing: 16
	readonly property real cardRadius: Theme.geometry_listItem_radius * 1.2
	readonly property var modeOptions: hasRoomTemperatureControl
		? [
			{ label: "Power", value: 0, icon: "P" },
			{ label: "Temperature", value: 1, icon: "T" },
			{ label: "Ventilation", value: 2, icon: "V" },
			{ label: "Heat + Vent", value: 3, icon: "H" },
		]
		: [
			{ label: "Power", value: 0, icon: "P" },
			{ label: "Ventilation", value: 2, icon: "V" },
		]
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
	readonly property real dialValue: {
		if (showTemperatureControl && targetTemperature.valid && targetTemperature.value > 0 && roomTemperature.valid) {
			return clamp(roomTemperature.value / targetTemperature.value, 0.0, 1.0)
		}
		if (roomTemperature.valid) {
			return clamp((roomTemperature.value - 5) / 30, 0.0, 1.0)
		}
		if (isRunning) {
			return 0.72
		}
		return 0.18
	}

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

	onActiveFocusChanged: {
		if (!root.activeFocus) {
			return
		}
		if (tabBar.visible && root.view.focusEdgeHint === Qt.TopEdge) {
			tabBar.focus = true
		} else if (root.view.focusEdgeHint === Qt.BottomEdge) {
			contentScope.focus = true
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
		model: root.tabModel
		currentIndex: root.currentHeaterIndex
		KeyNavigation.down: contentScope
		onButtonClicked: function(buttonIndex) {
			root.currentHeaterIndex = buttonIndex
		}
	}

	FocusScope {
		id: contentScope

		anchors {
			top: tabBar.visible ? tabBar.bottom : parent.top
			topMargin: tabBar.visible
					? Theme.geometry_levelsPage_gaugesView_compact_topMargin
					: Theme.geometry_page_content_verticalMargin
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

		Flickable {
			visible: root.hasHeater
			anchors.fill: parent
			contentWidth: width
			contentHeight: contentColumn.height
			boundsBehavior: Flickable.StopAtBounds
			clip: true

			Column {
				id: contentColumn

				width: parent.width
				spacing: root.sectionSpacing

				Rectangle {
					width: parent.width
					radius: root.cardRadius
					color: root.panelColor
					border.width: 1
					border.color: root.panelStrokeColor
					implicitHeight: heroContent.implicitHeight + 28
					gradient: Gradient {
						GradientStop { position: 0.0; color: root.accentDarkColor }
						GradientStop { position: 0.22; color: "#20252c" }
						GradientStop { position: 1.0; color: root.panelColor }
					}

					Item {
						id: heroContent
						x: 14
						y: 14
						width: parent.width - 28
						height: Math.max(dialArea.height, infoColumn.implicitHeight) + (warningBanner.visible ? warningBanner.height + 12 : 0)

						Item {
							id: dialArea
							width: Math.min(parent.width * 0.38, 220)
							height: width

							ProgressArc {
								anchors.fill: parent
								radius: (Math.min(parent.width, parent.height) / 2) - 12
								strokeWidth: 16
								startAngle: 135
								endAngle: 405
								value: root.dialValue * 100
								progressColor: root.accentColor
								remainderColor: Qt.rgba(1, 1, 1, 0.08)
							}

							Rectangle {
								anchors {
									fill: parent
									margins: 34
								}
								radius: width / 2
								color: Qt.rgba(0, 0, 0, 0.18)
								border.width: 1
								border.color: Qt.rgba(1, 1, 1, 0.06)

								Column {
									anchors.centerIn: parent
									spacing: 4

									Label {
										anchors.horizontalCenter: parent.horizontalCenter
										text: "Room"
										font.pixelSize: Theme.font_size_caption
										color: root.subtleTextColor
									}

									Label {
										anchors.horizontalCenter: parent.horizontalCenter
										text: root.formatTemperatureValue(roomTemperature)
										font.pixelSize: Theme.font_size_h1
										font.bold: true
										color: Theme.color_font_primary
									}

									Label {
										anchors.horizontalCenter: parent.horizontalCenter
										text: root.roomSourceLabel
										font.pixelSize: Theme.font_size_caption
										color: root.subtleTextColor
										wrapMode: Text.Wrap
										horizontalAlignment: Text.AlignHCenter
									}
								}
							}
						}

						Column {
							id: infoColumn
							x: dialArea.width + 18
							width: parent.width - x
							spacing: 10

							Label {
								width: parent.width
								text: root.currentHeater ? root.currentHeater.name : "Heater"
								font.pixelSize: Theme.font_size_body1
								color: root.subtleTextColor
								elide: Text.ElideRight
							}

							Label {
								width: parent.width
								text: root.stateLabel(heaterState.value)
								font.pixelSize: Theme.font_size_h1
								font.bold: true
								color: Theme.color_font_primary
								elide: Text.ElideRight
							}

							Row {
								spacing: 8

								Rectangle {
									radius: 14
									color: Qt.rgba(1, 1, 1, 0.08)
									implicitWidth: modeText.implicitWidth + 18
									implicitHeight: modeText.implicitHeight + 10

									Label {
										id: modeText
										anchors.centerIn: parent
										text: root.modeLabel(mode.value)
										font.pixelSize: Theme.font_size_caption
										color: Theme.color_font_primary
									}
								}

								Rectangle {
									radius: 14
									color: root.accentFillColor
									border.width: 1
									border.color: root.accentBorderColor
									implicitWidth: phaseText.implicitWidth + 18
									implicitHeight: phaseText.implicitHeight + 10

									Label {
										id: phaseText
										anchors.centerIn: parent
										text: root.actionPhaseLabel
										font.pixelSize: Theme.font_size_caption
										color: Theme.color_font_primary
									}
								}
							}

							Row {
								spacing: 18

								Column {
									spacing: 2

									Label {
										text: "Heater"
										font.pixelSize: Theme.font_size_caption
										color: root.subtleTextColor
									}

									Label {
										text: root.formatTemperature(heaterTemperature)
										font.pixelSize: Theme.font_size_body1
										color: Theme.color_font_primary
									}
								}

								Column {
									spacing: 2

									Label {
										text: "Voltage"
										font.pixelSize: Theme.font_size_caption
										color: root.subtleTextColor
									}

									Label {
										text: root.formatVoltage(dcVoltage)
										font.pixelSize: Theme.font_size_body1
										color: Theme.color_font_primary
									}
								}
							}

							Flow {
								width: parent.width
								spacing: 8

								Rectangle {
									radius: 14
									color: "#20252c"
									border.width: 1
									border.color: root.panelStrokeColor
									implicitWidth: runtimeChipText.implicitWidth + 18
									implicitHeight: runtimeChipText.implicitHeight + 10

									Label {
										id: runtimeChipText
										anchors.centerIn: parent
										text: "Runtime " + root.formatRuntime(runtimeItem)
										font.pixelSize: Theme.font_size_caption
										color: Theme.color_font_primary
									}
								}

								Rectangle {
									radius: 14
									color: "#20252c"
									border.width: 1
									border.color: root.panelStrokeColor
									implicitWidth: sourceChipText.implicitWidth + 18
									implicitHeight: sourceChipText.implicitHeight + 10

									Label {
										id: sourceChipText
										anchors.centerIn: parent
										text: root.roomSourceChipLabel
										font.pixelSize: Theme.font_size_caption
										color: Theme.color_font_primary
									}
								}
							}
						}

						Rectangle {
							id: warningBanner
							visible: root.warningText.length > 0
							x: 0
							y: Math.max(dialArea.height, infoColumn.implicitHeight) + 12
							width: parent.width
							radius: 16
							color: Qt.rgba(0.36, 0.12, 0.15, 0.92)
							border.width: 1
							border.color: Qt.rgba(1, 0.44, 0.49, 0.4)
							implicitHeight: warningColumn.implicitHeight + 16

							Column {
								id: warningColumn
								x: 12
								y: 8
								width: parent.width - 24
								spacing: 2

								Label {
									width: parent.width
									text: root.warningTitle
									font.pixelSize: Theme.font_size_body2
									font.bold: true
									color: Theme.color_font_primary
								}

								Label {
									width: parent.width
									text: root.warningText
									font.pixelSize: Theme.font_size_caption
									color: Theme.color_font_primary
									wrapMode: Text.Wrap
								}
							}
						}
					}
				}

				Rectangle {
					width: parent.width
					radius: root.cardRadius
					color: root.panelRaisedColor
					border.width: 1
					border.color: root.panelStrokeColor
					implicitHeight: controlColumn.implicitHeight + 24

					Column {
						id: controlColumn
						x: 12
						y: 12
						width: parent.width - 24
						spacing: 14

						Label {
							text: "Quick control"
							font.pixelSize: Theme.font_size_body2
							font.bold: true
							color: Theme.color_font_primary
						}

						Button {
							width: parent.width
							height: 56
							text: root.actionLabel
							enabled: startStop.valid
							flat: false
							backgroundColor: root.accentColor
							borderColor: root.accentColor
							color: "#0e1114"
							font.pixelSize: Theme.font_size_body1
							font.bold: true
							onClicked: Global.dialogLayer.open(startStopDialogComponent, {
								startRequested: !root.isRunning,
							})
						}

						Flow {
							width: parent.width
							spacing: 10

							Repeater {
								model: root.modeOptions

								delegate: Button {
									width: Math.max(132, (controlColumn.width - 10) / 2)
									height: 54
									text: modelData.label
									enabled: mode.valid
									flat: false
									backgroundColor: mode.valid && mode.value === modelData.value ? root.accentColor : "#222730"
									borderColor: mode.valid && mode.value === modelData.value
										? root.accentColor
										: root.panelStrokeColor
									color: mode.valid && mode.value === modelData.value ? "#0e1114" : Theme.color_font_primary
									font.pixelSize: Theme.font_size_body1
									onClicked: {
										if (mode.valid && mode.value !== modelData.value) {
											mode.setValue(modelData.value)
										}
									}
								}
							}
						}

						Rectangle {
							width: parent.width
							radius: 18
							color: "#181c22"
							border.width: 1
							border.color: root.panelStrokeColor
							implicitHeight: targetColumn.implicitHeight + 18

							Column {
								id: targetColumn
								x: 14
								y: 9
								width: parent.width - 28
								spacing: 12

								Label {
									text: root.showTemperatureControl ? "Target temperature"
										: root.showPowerControl ? "Power target"
										: "Temperature control unavailable"
									font.pixelSize: Theme.font_size_body2
									font.bold: true
									color: Theme.color_font_primary
								}

								Item {
									visible: root.showTemperatureControl
									width: parent.width
									height: 76

									Button {
										width: 72
										height: 72
										text: "-"
										enabled: targetTemperature.valid
										flat: false
										backgroundColor: "#242a32"
										borderColor: root.panelStrokeColor
										color: Theme.color_font_primary
										font.pixelSize: Theme.font_size_h2
										onClicked: targetTemperature.setValue(Math.max(5, targetTemperature.value - 1))
									}

									Column {
										anchors.centerIn: parent
										spacing: 2

										Label {
											anchors.horizontalCenter: parent.horizontalCenter
											text: root.formatTemperature(targetTemperature)
											font.pixelSize: Theme.font_size_h1
											font.bold: true
											color: Theme.color_font_primary
										}

										Label {
											anchors.horizontalCenter: parent.horizontalCenter
											text: "Reference: " + root.roomSourceLabel
											font.pixelSize: Theme.font_size_caption
											color: root.subtleTextColor
										}
									}

									Button {
										anchors.right: parent.right
										width: 72
										height: 72
										text: "+"
										enabled: targetTemperature.valid
										flat: false
										backgroundColor: root.accentDarkColor
										borderColor: root.accentColor
										color: Theme.color_font_primary
										font.pixelSize: Theme.font_size_h2
										onClicked: targetTemperature.setValue(Math.min(35, targetTemperature.value + 1))
									}
								}

								Item {
									visible: root.showPowerControl
									width: parent.width
									height: powerSegments.height + 28

									Column {
										width: parent.width
										spacing: 10

										Row {
											spacing: 8

											Label {
												text: powerLevel.valid ? "Level " + powerLevel.value : "Level --"
												font.pixelSize: Theme.font_size_h2
												font.bold: true
												color: Theme.color_font_primary
											}

											Label {
												anchors.verticalCenter: parent.verticalCenter
												text: root.isVentilationMode ? "Ventilation output" : "Heating power"
												font.pixelSize: Theme.font_size_caption
												color: root.subtleTextColor
											}
										}

										Row {
											id: powerSegments
											width: parent.width
											spacing: 6

											Repeater {
												model: 9

												delegate: Button {
													width: (powerSegments.width - (powerSegments.spacing * 8)) / 9
													height: 42
													text: String(index + 1)
													enabled: powerLevel.valid
													flat: false
													backgroundColor: powerLevel.valid && powerLevel.value >= index + 1
														? root.accentColor
														: "#242a32"
													borderColor: powerLevel.valid && powerLevel.value === index + 1
														? "#ffffff"
														: root.panelStrokeColor
													borderWidth: powerLevel.valid && powerLevel.value === index + 1 ? 2 : 1
													color: powerLevel.valid && powerLevel.value >= index + 1
														? "#0e1114"
														: Theme.color_font_primary
													font.pixelSize: Theme.font_size_body1
													onClicked: powerLevel.setValue(index + 1)
												}
											}
										}
									}
								}

								Label {
									visible: !root.showTemperatureControl && !root.showPowerControl
									width: parent.width
									text: root.hasRoomTemperatureControl
										? "Select a supported operating mode to edit its target."
										: "Connect a room sensor to unlock temperature-based modes."
									font.pixelSize: Theme.font_size_body1
									color: root.subtleTextColor
									wrapMode: Text.Wrap
								}
							}
						}
					}
				}

				Rectangle {
					width: parent.width
					radius: root.cardRadius
					color: root.panelRaisedColor
					border.width: 1
					border.color: root.panelStrokeColor
					implicitHeight: timersColumn.implicitHeight + 24

					Column {
						id: timersColumn
						x: 12
						y: 12
						width: parent.width - 24
						spacing: 12

						Item {
							width: parent.width
							height: Math.max(timersTitle.implicitHeight, timersHint.implicitHeight)

							Label {
								id: timersTitle
								anchors.left: parent.left
								anchors.verticalCenter: parent.verticalCenter
								text: "Timers"
								font.pixelSize: Theme.font_size_body2
								font.bold: true
								color: Theme.color_font_primary
							}

							Label {
								id: timersHint
								anchors.right: parent.right
								anchors.verticalCenter: parent.verticalCenter
								text: "Tap a tile to toggle"
								font.pixelSize: Theme.font_size_caption
								color: root.subtleTextColor
							}
						}

						Flow {
							width: parent.width
							spacing: 10

							Repeater {
								model: [
									{
										label: "Timer 1",
										enabledItem: timer0Enabled,
										hourItem: timer0Hour,
										minuteItem: timer0Minute,
									},
									{
										label: "Timer 2",
										enabledItem: timer1Enabled,
										hourItem: timer1Hour,
										minuteItem: timer1Minute,
									},
									{
										label: "Timer 3",
										enabledItem: timer2Enabled,
										hourItem: timer2Hour,
										minuteItem: timer2Minute,
									},
								]

								delegate: Rectangle {
									width: (timersColumn.width - 20) / 3
									height: 104
									radius: 18
									color: modelData.enabledItem.valid && modelData.enabledItem.value === 1
										? root.accentFillColor
										: "#181c22"
									border.width: 1
									border.color: modelData.enabledItem.valid && modelData.enabledItem.value === 1
										? root.accentBorderColor
										: root.panelStrokeColor

									PressArea {
										anchors.fill: parent
										radius: parent.radius
										onClicked: {
											if (modelData.enabledItem.valid) {
												modelData.enabledItem.setValue(modelData.enabledItem.value === 1 ? 0 : 1)
											}
										}
									}

									Column {
										anchors {
											fill: parent
											margins: 12
										}
										spacing: 8

										Label {
											text: modelData.label
											font.pixelSize: Theme.font_size_caption
											color: root.subtleTextColor
										}

										Label {
											text: root.timerTime(modelData.hourItem, modelData.minuteItem)
											font.pixelSize: Theme.font_size_h2
											font.bold: true
											color: Theme.color_font_primary
										}

										Rectangle {
											radius: 12
											color: modelData.enabledItem.valid && modelData.enabledItem.value === 1
												? root.accentColor
												: "#252b33"
											implicitWidth: timerStatusLabel.implicitWidth + 16
											implicitHeight: timerStatusLabel.implicitHeight + 8

											Label {
												id: timerStatusLabel
												anchors.centerIn: parent
												text: modelData.enabledItem.valid && modelData.enabledItem.value === 1 ? "Enabled" : "Disabled"
												font.pixelSize: Theme.font_size_caption
												color: modelData.enabledItem.valid && modelData.enabledItem.value === 1
													? "#0e1114"
													: Theme.color_font_primary
											}
										}
									}
								}
							}
						}
					}
				}

				Rectangle {
					width: parent.width
					radius: root.cardRadius
					color: root.panelRaisedColor
					border.width: 1
					border.color: root.panelStrokeColor
					implicitHeight: metricsColumn.implicitHeight + 24

					Column {
						id: metricsColumn
						x: 12
						y: 12
						width: parent.width - 24
						spacing: 12

						Label {
							text: "Live metrics"
							font.pixelSize: Theme.font_size_body2
							font.bold: true
							color: Theme.color_font_primary
						}

						Flow {
							width: parent.width
							spacing: 10

							Repeater {
								model: [
									{ label: "Fan", value: root.formatNumber(fanRpmActual, "RPM") },
									{ label: "Pump", value: root.formatNumber(fuelPumpFrequency, "Hz", 1) },
									{ label: "Voltage", value: root.formatVoltage(dcVoltage) },
									{ label: "Runtime", value: root.formatRuntime(runtimeItem) },
								]

								delegate: Rectangle {
									width: (metricsColumn.width - 10) / 2
									height: 72
									radius: 18
									color: "#181c22"
									border.width: 1
									border.color: root.panelStrokeColor

									Column {
										anchors {
											fill: parent
											margins: 12
										}
										spacing: 4

										Label {
											text: modelData.label
											font.pixelSize: Theme.font_size_caption
											color: root.subtleTextColor
										}

										Label {
											text: modelData.value
											font.pixelSize: Theme.font_size_body1
											font.bold: true
											color: Theme.color_font_primary
											elide: Text.ElideRight
										}
									}
								}
							}
						}
					}
				}

				Rectangle {
					width: parent.width
					radius: root.cardRadius
					color: root.panelRaisedColor
					border.width: 1
					border.color: root.panelStrokeColor
					implicitHeight: actionsColumn.implicitHeight + 24

					Column {
						id: actionsColumn
						x: 12
						y: 12
						width: parent.width - 24
						spacing: 12

						Label {
							text: "More"
							font.pixelSize: Theme.font_size_body2
							font.bold: true
							color: Theme.color_font_primary
						}

						Flow {
							width: parent.width
							spacing: 10

							Repeater {
								model: [
									{ label: "Timers", subtitle: "Edit schedules", action: "timers" },
									{ label: "Live data", subtitle: "Raw telemetry", action: "live" },
									{ label: "Diagnostics", subtitle: "Fault details", action: "diagnostics" },
									{ label: "Device page", subtitle: "Setup and settings", action: "device" },
								]

								delegate: Button {
									width: (actionsColumn.width - 10) / 2
									height: 72
									flat: false
									backgroundColor: "#181c22"
									borderColor: root.panelStrokeColor
									onClicked: root.openAction(modelData.action)

									contentItem: Column {
										spacing: 3

										Label {
											text: modelData.label
											font.pixelSize: Theme.font_size_body2
											font.bold: true
											color: Theme.color_font_primary
										}

										Label {
											text: modelData.subtitle
											font.pixelSize: Theme.font_size_caption
											color: root.subtleTextColor
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}

	VeQuickItem { id: mode; uid: root.bindPrefix + "/Mode" }
	VeQuickItem { id: heaterState; uid: root.bindPrefix + "/State" }
	VeQuickItem { id: startStop; uid: root.bindPrefix + "/StartStop" }
	VeQuickItem { id: errorText; uid: root.bindPrefix + "/ErrorText" }
	VeQuickItem { id: communicationAlarm; uid: root.bindPrefix + "/Alarms/Communication" }
	VeQuickItem { id: roomTemperatureControl; uid: root.bindPrefix + "/Capabilities/RoomTemperatureControl" }
	VeQuickItem { id: roomTemperature; uid: root.bindPrefix + "/Temperatures/Room" }
	VeQuickItem { id: roomSourceText; uid: root.bindPrefix + "/Temperatures/RoomSourceText" }
	VeQuickItem { id: heaterTemperature; uid: root.bindPrefix + "/Temperatures/Heater" }
	VeQuickItem { id: dcVoltage; uid: root.bindPrefix + "/Dc/0/Voltage" }
	VeQuickItem { id: runtimeItem; uid: root.bindPrefix + "/Runtime" }
	VeQuickItem { id: targetTemperature; uid: root.bindPrefix + "/Settings/TargetTemperature" }
	VeQuickItem { id: powerLevel; uid: root.bindPrefix + "/Settings/PowerLevel" }
	VeQuickItem { id: fanRpmActual; uid: root.bindPrefix + "/Status/FanRpmActual" }
	VeQuickItem { id: fuelPumpFrequency; uid: root.bindPrefix + "/Status/FuelPumpFrequency" }

	VeQuickItem { id: timer0Enabled; uid: root.bindPrefix + "/Timers/0/Enabled" }
	VeQuickItem { id: timer0Hour; uid: root.bindPrefix + "/Timers/0/StartHour" }
	VeQuickItem { id: timer0Minute; uid: root.bindPrefix + "/Timers/0/StartMinute" }
	VeQuickItem { id: timer1Enabled; uid: root.bindPrefix + "/Timers/1/Enabled" }
	VeQuickItem { id: timer1Hour; uid: root.bindPrefix + "/Timers/1/StartHour" }
	VeQuickItem { id: timer1Minute; uid: root.bindPrefix + "/Timers/1/StartMinute" }
	VeQuickItem { id: timer2Enabled; uid: root.bindPrefix + "/Timers/2/Enabled" }
	VeQuickItem { id: timer2Hour; uid: root.bindPrefix + "/Timers/2/StartHour" }
	VeQuickItem { id: timer2Minute; uid: root.bindPrefix + "/Timers/2/StartMinute" }

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

	function clamp(value, minValue, maxValue) {
		return Math.max(minValue, Math.min(maxValue, value))
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

	function modeLabel(value) {
		switch (value) {
		case 0:
			return "Power"
		case 1:
			return "Temperature"
		case 2:
			return "Ventilation"
		case 3:
			return "Heat + ventilation"
		default:
			return "Unknown"
		}
	}

	function formatTemperature(item) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		return Number(Units.convert(item.value, VenusOS.Units_Temperature_Celsius, Global.systemSettings.temperatureUnit)).toFixed(0)
			+ Global.systemSettings.temperatureUnitSuffix
	}

	function formatTemperatureValue(item) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		return Number(Units.convert(item.value, VenusOS.Units_Temperature_Celsius, Global.systemSettings.temperatureUnit)).toFixed(0)
			+ Global.systemSettings.temperatureUnitSuffix
	}

	function formatVoltage(item) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		return Number(item.value).toFixed(1) + "V"
	}

	function formatNumber(item, unit, decimals) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		const fixed = decimals === undefined ? 0 : decimals
		return Number(item.value).toFixed(fixed) + " " + unit
	}

	function formatRuntime(item) {
		if (!item.valid || item.value === undefined || item.value === null || item.value === "") {
			return "--"
		}
		return Utils.secondsToString(item.value, false)
	}

	function timerTime(hourItem, minuteItem) {
		if (!hourItem.valid || !minuteItem.valid) {
			return "--:--"
		}
		const hour = String(Math.max(0, hourItem.value)).padStart(2, "0")
		const minute = String(Math.max(0, minuteItem.value)).padStart(2, "0")
		return hour + ":" + minute
	}

	function openAction(action) {
		switch (action) {
		case "timers":
			Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterTimers.qml", {
				bindPrefix: root.bindPrefix,
			})
			break
		case "live":
			Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterLiveData.qml", {
				bindPrefix: root.bindPrefix,
			})
			break
		case "diagnostics":
			Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterDiagnostics.qml", {
				bindPrefix: root.bindPrefix,
			})
			break
		case "device":
			Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeater.qml", {
				bindPrefix: root.bindPrefix,
			})
			break
		}
	}

	readonly property string roomSourceLabel: roomSourceText.valid && roomSourceText.value
		? roomSourceText.value
		: "No room sensor"
	readonly property string roomSourceChipLabel: roomSourceText.valid && roomSourceText.value
		? "Source " + roomSourceText.value
		: "Source unavailable"
	readonly property string actionPhaseLabel: hasFault
		? "Needs attention"
		: (isRunning ? "Active now" : "Standby")
}

import QtQuick
import QtQml.Models
import Victron.VenusOS
import Victron.Boat as Boat

ObjectModel {
	id: root

	required property SwipeView view
	readonly property bool showLevelsPage: tankCount > 0 || environmentInputCount > 0
	readonly property int tankCount: Global.tanks ? Global.tanks.totalTankCount : 0
	readonly property int environmentInputCount: Global.environmentInputs ? Global.environmentInputs.model.count : 0
	readonly property FilteredDeviceModel heaterModel: FilteredDeviceModel {
		serviceTypes: ["heater"]
		sorting: FilteredDeviceModel.DeviceInstance
	}
	readonly property bool showHeaterPage: heaterCount > 0
	readonly property int heaterCount: heaterModel.count

	readonly property Component boatPage: Component {
		Boat.BoatPage {
			view: root.view
		}
	}
	readonly property VeQuickItem showBoatPage: VeQuickItem {
		uid: !!Global.systemSettings ? Global.systemSettings.serviceUid + "/Settings/Gui/ElectricPropulsionUI/Enabled" : ""
		onValueChanged: {
			if (!completed) {
				return
			}

			if (value) {
				root.view.insertItem(0, boatPage.createObject(parent))
			} else {
				root.view.removeItem(view.itemAt(0))
			}
		}
	}

	readonly property Component levelsComponent: Component {
		LevelsPage {
			view: root.view
		}
	}
	readonly property Component heaterComponent: Component {
		Item {}
	}
	property LevelsPage levelsPage
	property Item heaterPage

	property bool completed: false

	BriefPage {
		view: root.view

		Image {
			width: status === Image.Null ? 0 : Theme.geometry_screen_width
			fillMode: Image.PreserveAspectFit
			source: BackendConnection.demoImageFileName
			onStatusChanged: {
				if (status === Image.Ready) {
					console.info("Loaded demo image:", source)
				}
			}
		}
	}

	OverviewPage {
		view: root.view
	}

	NotificationsPage {
		id: notificationsPage
		view: root.view
	}

	SettingsPage {
		view: root.view
	}

	Component.onCompleted: {
		if (showLevelsPage) {
			levelsPage = levelsComponent.createObject(parent)
			insert(2, levelsPage) // ideally the index would not be hardcoded, but the view is not initialized yet
		}

		if (showBoatPage.value) {
			insert(0, boatPage.createObject(parent))
		}

		if (showHeaterPage) {
			const component = Qt.createComponent(Qt.resolvedUrl("../pages/HeaterPage.qml"))
			heaterPage = component.createObject(parent, {
				"view": root.view,
				"heaterModel": root.heaterModel
			})
			insert(count - 2, heaterPage)
		}

		completed = true
	}

	onShowLevelsPageChanged: {
		if (!completed) {
			return
		}

		if (showLevelsPage) {
			for (let i = 0; i < root.view.count; ++i) {
				if (root.view.itemAt(i) === notificationsPage) {
					root.levelsPage = levelsComponent.createObject(parent)
					root.view.insertItem(i, root.levelsPage)
					break
				}
			}
		} else if (root.levelsPage) {
			root.view.removeItem(root.levelsPage)
			root.levelsPage = null
		}
	}

	onShowHeaterPageChanged: {
		if (!completed) {
			return
		}

		if (showHeaterPage) {
			for (let i = 0; i < root.view.count; ++i) {
				if (root.view.itemAt(i) === notificationsPage) {
					const component = Qt.createComponent(Qt.resolvedUrl("../pages/HeaterPage.qml"))
					root.heaterPage = component.createObject(parent, {
						"view": root.view,
						"heaterModel": root.heaterModel
					})
					root.view.insertItem(i, root.heaterPage)
					break
				}
			}
		} else if (root.heaterPage) {
			root.view.removeItem(root.heaterPage)
			root.heaterPage = null
		}
	}
}

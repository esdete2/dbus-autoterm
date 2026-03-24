import QtQuick
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	serviceUid: bindPrefix

	showSwitches: false
	title: "Timers"

	settingsModel: VisibleItemModel {
		Repeater {
			model: 3

			delegate: ListNavigation {
				required property int index
				readonly property string timerPrefix: root.bindPrefix + "/Timers/" + index
				text: "Timer " + (index + 1)
				secondaryText: enabled.valid && enabled.value ? "Enabled" : "Disabled"
				onClicked: Global.pageManager.pushPage("/pages/settings/devicelist/heater/PageHeaterTimer.qml", {
					bindPrefix: root.bindPrefix,
					timerIndex: index,
				})

				VeQuickItem {
					id: enabled
					uid: timerPrefix + "/Enabled"
				}
			}
		}
	}
}

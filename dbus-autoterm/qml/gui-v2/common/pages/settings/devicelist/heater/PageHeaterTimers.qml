import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Timers"

	GradientListView {
		model: VisibleItemModel {
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
}

import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Diagnostics"

	GradientListView {
		model: VisibleItemModel {
			ListText {
				text: "Connection"
				dataItem.uid: root.bindPrefix + "/Connected"
				secondaryText: dataItem.valid && dataItem.value === 1 ? "Connected" : "Disconnected"
			}

			ListText {
				text: "State"
				dataItem.uid: root.bindPrefix + "/StateText"
				secondaryText: dataItem.valid ? dataItem.value : ""
			}

			ListText {
				text: "Error"
				dataItem.uid: root.bindPrefix + "/ErrorCode"
				secondaryText: dataItem.valid ? String(dataItem.value) : ""
			}

			ListText {
				text: "Error details"
				dataItem.uid: root.bindPrefix + "/ErrorText"
				secondaryText: dataItem.valid ? dataItem.value : ""
			}

			ListText {
				text: "Communication alarm"
				dataItem.uid: root.bindPrefix + "/Alarms/Communication"
				secondaryText: dataItem.valid && dataItem.value === 0 ? "OK" : "Alarm"
			}
		}
	}
}

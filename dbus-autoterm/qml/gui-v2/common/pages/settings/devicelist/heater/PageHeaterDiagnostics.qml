import QtQuick
import Victron.VenusOS

DevicePage {
	id: root

	required property string bindPrefix
	serviceUid: bindPrefix

	showSwitches: false
	title: "Diagnostics"

	settingsModel: VisibleItemModel {
		ListText {
			text: "Connection"
			dataItem.uid: root.bindPrefix + "/Connected"
			secondaryText: dataItem.valid && dataItem.value === 1 ? "Connected" : "Disconnected"
		}

		ListText {
			text: CommonWords.state
			dataItem.uid: root.bindPrefix + "/StateText"
			secondaryText: dataItem.valid ? dataItem.value : ""
		}

		ListText {
			text: CommonWords.error
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

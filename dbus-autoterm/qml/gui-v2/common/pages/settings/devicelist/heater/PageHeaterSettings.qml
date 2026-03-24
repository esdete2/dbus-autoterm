import QtQuick
import Victron.VenusOS

Page {
	id: root

	required property string bindPrefix
	title: "Heater settings"

	GradientListView {
		model: VisibleItemModel {
			ListRadioButtonGroup {
				text: "Sensor source"
				dataItem.uid: root.bindPrefix + "/Settings/SensorSource"
				optionModel: [
					{ display: "Controller", value: 0 },
					{ display: "External", value: 1 },
					{ display: "Heater", value: 2 },
				]
			}
		}
	}
}

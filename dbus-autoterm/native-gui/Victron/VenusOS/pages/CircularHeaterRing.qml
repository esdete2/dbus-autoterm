import QtQuick
import Victron.VenusOS

Item {
	id: root

	property real valueRatio: 0.0
	property real strokeWidth: 22
	property color progressColor: Theme.color_blue
	property color remainderColor: Theme.color_gray1
	property color centerFillColor: Qt.rgba(0, 0, 0, 0.18)
	property color centerStrokeColor: Qt.rgba(1, 1, 1, 0.06)
	property color primaryValueColor: Theme.color_font_primary
	property color secondaryValueColor: Theme.color_listItem_secondaryText
	property string primaryValue: ""
	property string secondaryValue: ""

	readonly property real normalizedRatio: clamp(valueRatio, 0.0, 1.0)
	readonly property real startAngle: 225
	readonly property real endAngle: 495
	readonly property real arcRadius: (Math.min(width, height) / 2) - (strokeWidth / 2) - 10
	readonly property real centerDiameter: (arcRadius * 2) - (strokeWidth * 1.9)

	function clamp(value, minValue, maxValue) {
		return Math.max(minValue, Math.min(maxValue, value))
	}

	Item {
		id: ringBounds
		width: root.arcRadius * 2
		height: root.arcRadius * 2
		anchors.centerIn: parent

		ProgressArc {
			anchors.fill: parent
			radius: root.arcRadius
			strokeWidth: root.strokeWidth
			startAngle: root.startAngle
			endAngle: root.endAngle
			value: root.normalizedRatio * 100
			progressColor: root.progressColor
			remainderColor: root.remainderColor
		}

		Rectangle {
			width: root.centerDiameter
			height: root.centerDiameter
			anchors.centerIn: parent
			radius: width / 2
			color: root.centerFillColor
			border.width: 1
			border.color: root.centerStrokeColor

			Column {
				anchors.centerIn: parent
				spacing: 0

				Label {
					anchors.horizontalCenter: parent.horizontalCenter
					text: root.primaryValue
					font.pixelSize: Theme.font_size_h1 * 1.35
					font.bold: true
					color: root.primaryValueColor
				}

				Label {
					anchors.horizontalCenter: parent.horizontalCenter
					text: root.secondaryValue
					font.pixelSize: Theme.font_size_body1 * 1.2
					font.bold: true
					color: root.secondaryValueColor
				}
			}
		}
	}
}

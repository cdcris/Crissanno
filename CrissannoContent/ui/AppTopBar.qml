import QtQuick
import QtQuick.Controls

// Shared application header for every form in this directory.
// Override the public properties below to match each form's content or theme.
Rectangle {
    id: root

    property string appTitle: qsTr("CVAT AI")
    property string logoText: "\u2733"
    property var menuItems: [] // [{ label: "File", active: true }, ...]
    property string statusText: qsTr("Ready")
    property string fontFamily: ""

    property color backgroundColor: "#171d21"
    property color borderColor: "#2c3439"
    property color accentColor: "#2479e8"
    property color chipColor: "#191f23"
    property color chipHoverColor: "#212a2f"
    property color primaryTextColor: "#f1f4f5"
    property color secondaryTextColor: "#c7d0d5"
    property color statusColor: "#58c62e"

    property int smallRadius: 5
    property int extraSmallSpacing: 4
    property int smallSpacing: 8
    property int horizontalPadding: 16
    property int menuLeftMargin: 158

    signal menuClicked(int index, string label)

    height: 48
    color: backgroundColor
    border.color: borderColor
    border.width: 1

    Row {
        anchors.left: parent.left
        anchors.leftMargin: root.horizontalPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: root.smallSpacing

        Rectangle {
            width: 28
            height: 28
            radius: root.smallRadius
            color: root.accentColor
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.logoText
                color: root.primaryTextColor
                font.pixelSize: 16
                font.bold: true
            }
        }

        Text {
            text: root.appTitle
            color: root.primaryTextColor
            font.family: root.fontFamily
            font.pixelSize: 17
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: root.menuLeftMargin
        anchors.verticalCenter: parent.verticalCenter
        spacing: root.extraSmallSpacing

        Repeater {
            model: root.menuItems

            delegate: Item {
                required property var modelData
                required property int index

                width: menuLabel.implicitWidth + 24
                height: 34

                Rectangle {
                    anchors.fill: parent
                    radius: root.smallRadius
                    color: modelData.active ? root.chipColor : (menuArea.containsMouse ? root.chipHoverColor : "transparent")
                    border.color: modelData.active ? root.borderColor : "transparent"
                    border.width: 1

                    Text {
                        id: menuLabel
                        anchors.centerIn: parent
                        text: modelData.label
                        color: modelData.active ? root.primaryTextColor : root.secondaryTextColor
                        font.family: root.fontFamily
                        font.pixelSize: 14
                    }
                }

                MouseArea {
                    id: menuArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.menuClicked(index, modelData.label)
                }
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: root.horizontalPadding
        anchors.verticalCenter: parent.verticalCenter
        spacing: root.extraSmallSpacing

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: root.statusColor
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.statusText
            color: root.statusColor
            font.family: root.fontFamily
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}

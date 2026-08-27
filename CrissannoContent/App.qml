import QtQuick
import QtQuick.Window
import Crissanno

Window {
    // A windowed default makes the app immediately resizable; the limits keep
    // the annotation controls usable while still supporting large displays.
    width: 1440
    height: 900
    minimumWidth: 1200
    minimumHeight: 760
    maximumWidth: 3840
    maximumHeight: 2160

    visible: true
    visibility: Window.Windowed
    title: "Crissanno"

    Screen01 {
        id: mainScreen

        anchors.fill: parent
    }

}


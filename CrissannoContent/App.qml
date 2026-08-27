import QtQuick
import QtQuick.Window
import Crissanno
import "ui"

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

    Annotation {
        id: annotationScreen

        anchors.fill: parent
    }

}


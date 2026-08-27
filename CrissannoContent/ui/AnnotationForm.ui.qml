

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Window
import Crissanno 1.0

Rectangle {
    id: root
    width: Constants.width
    height: Constants.height
    // These preferred dimensions match the usable window size enforced by
    // App.qml.  When embedded elsewhere, the form continues to fill its
    // parent and all primary regions resize from their anchors.
    implicitWidth: 1200
    implicitHeight: 760
    visible: true

    color: theme.bgApp
    property alias bBox: bBox
    property alias topBar: topBar
    property string activeTool: "box"
    property var polygonPaths: []

    // ---- elements the logic layer (AnnotationForm.qml) drives ----
    property alias selectTool: selectTool
    property alias moveTool: moveTool
    property alias polygonTool: polygonTool
    property alias handTool: handTool

    property alias objectsModel: objectsModel
    property alias objectsRepeater: objectsRepeater
    property alias objectsCountText: objectsCountText

    property alias labelChipSwatch: labelChipSwatch
    property alias labelChipText: labelChipText
    property alias xValueText: xValueText
    property alias yValueText: yValueText
    property alias widthValueText: widthValueText
    property alias heightValueText: heightValueText

    property alias zoomPercentText: zoomPercentText
    property alias pageIndexInput: pageIndexInput
    property alias pageTotalText: pageTotalText
    property alias currentImageNameText: currentImageNameText
    property alias nextImageNameText: nextImageNameText
    property alias imageProgressSlider: imageProgressSlider
    property alias canvasImage: canvasImage
    property alias imageCanvas: imageCanvas
    property alias annotationLayer: annotationLayer
    // Populate with image URLs to make image navigation/scrubbing update the canvas.
    property var imageSources: []
    // Set by the logic layer for the lightweight "Up next" thumbnail.
    property url nextImageSource: ""
    property bool gridVisible: false
    property real canvasPanX: 0
    property real canvasPanY: 0

    property alias addObjectBtn: addObjectBtn
    property alias prevBtn: prevBtn
    property alias nextBtn: nextBtn
    property alias zoomInBtn: zoomInBtn
    property alias zoomOutBtn: zoomOutBtn
    property alias fitBtn: fitBtn
    property alias gridToggleArea: gridToggleArea
    property alias canvasWheelHandler: canvasWheelHandler
    property alias drawingArea: drawingArea

    // ---- signals the logic layer connects to ----
    signal toolSelected(string tool)
    signal topMenuClicked(int index, string label)
    signal objectSelected(int index)
    signal annotationMoveRequested(int index, real deltaX, real deltaY)
    signal addObjectRequested
    signal duplicateRequested
    signal lockRequested
    signal deleteRequested
    signal prevImageRequested
    signal nextImageRequested
    signal imageIndexRequested(int index)
    signal zoomInRequested
    signal zoomOutRequested
    signal fitRequested
    signal gridToggleRequested
    signal boxDrawn(real x, real y, real width, real height)
    signal polygonDrawn(var points)
    signal canvasPanStarted(real x, real y)
    signal canvasPanMoved(real x, real y)
    signal canvasPanFinished

    // ============================================================
    // DESIGN TOKENS
    // Single source of truth for color / radius / spacing so every
    // panel below stays visually consistent and easy to re-theme.
    // ============================================================
    QtObject {
        id: theme

        // surfaces
        readonly property color bgApp: "#101416"
        readonly property color bgPanel: "#151a1d"
        readonly property color bgPanelHeader: "#171d21"
        readonly property color bgCanvas: "#0b0f11"
        readonly property color bgChip: "#191f23"
        readonly property color bgChipHover: "#212a2f"
        readonly property color bgInput: "#0f1417"

        // borders
        readonly property color border: "#2c3439"
        readonly property color borderStrong: "#3b464d"

        // brand / accent
        readonly property color accent: "#2479e8"
        readonly property color accentBorder: "#2c91ff"
        readonly property color accentSoft: "#14569b"
        readonly property color accentTint: "#1d2c38"

        // text
        readonly property color textPrimary: "#f1f4f5"
        readonly property color textSecondary: "#c7d0d5"
        readonly property color textMuted: "#849198"
        readonly property color textFaint: "#5b666c"

        // status / class colors
        readonly property color success: "#58c62e"
        readonly property color warning: "#ff9818"
        readonly property color danger: "#e8636c"
        readonly property color dangerBg: "#241819"
        readonly property color dangerBorder: "#5c3a3e"
        readonly property color classPerson: "#2389ff"
        readonly property color classCar: "#58c62e"
        readonly property color classTruck: "#ff9818"

        // metrics
        readonly property int radiusS: 5
        readonly property int radiusM: 7
        readonly property int spacingXs: 4
        readonly property int spacingS: 8
        readonly property int spacingM: 12
        readonly property int spacingL: 16
    }

    // ============================================================
    // TOP APPLICATION BAR
    // ============================================================
    AppTopBar {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        appTitle: qsTr("Crissanno")
        menuItems: [{
                "label": qsTr("File"),
                "active": false
            }, {
                "label": qsTr("Edit"),
                "active": false
            }, {
                "label": qsTr("View"),
                "active": false
            }, {
                "label": qsTr("Tools"),
                "active": false
            }, {
                "label": qsTr("AI"),
                "active": false
            }, {
                "label": qsTr("Export"),
                "active": false
            }]
        statusText: qsTr("")
        fontFamily: Constants.font.family
        backgroundColor: theme.bgPanelHeader
        borderColor: theme.border
        accentColor: theme.accent
        chipColor: theme.bgChip
        chipHoverColor: theme.bgChipHover
        primaryTextColor: theme.textPrimary
        secondaryTextColor: theme.textSecondary
        statusColor: theme.success
        smallRadius: theme.radiusS
        extraSmallSpacing: theme.spacingXs
        smallSpacing: theme.spacingS
        horizontalPadding: theme.spacingL
    }

    Connections {
        target: topBar

        function onMenuClicked(index, label) {
            root.topMenuClicked(index, label)
        }
    }

    // ============================================================
    // MAIN BODY
    // ============================================================
    Item {
        id: mainBody
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomBar.top

        // ========================================================
        // LEFT TOOL PANEL
        // ========================================================
        Rectangle {
            id: leftPanel
            // Let the inspector panels grow modestly on wide displays but
            // reserve the bulk of the space for the annotation canvas.
            width: Math.round(Math.max(208, Math.min(248, root.width * 0.17)))
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            color: theme.bgPanel
            border.color: theme.border
            border.width: 1

            Text {
                id: toolsHeading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.topMargin: theme.spacingL
                anchors.leftMargin: theme.spacingL
                text: qsTr("TOOLS")
                color: theme.textSecondary
                font.family: Constants.font.family
                font.pixelSize: 13
                font.bold: true
                font.letterSpacing: 1
            }

            Column {
                id: toolList
                anchors.top: toolsHeading.bottom
                anchors.topMargin: theme.spacingM
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: theme.spacingM
                anchors.rightMargin: theme.spacingM
                spacing: theme.spacingS

                // ---- Select ----
                Rectangle {
                    id: selectTool
                    width: parent.width
                    height: 52
                    radius: theme.radiusM
                    property bool selected: false
                    property bool hovered: false
                    color: selected ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                    border.color: selected ? theme.accentBorder : theme.border
                    border.width: 1

                    Rectangle {
                        visible: selectTool.selected
                        width: 3
                        height: parent.height - 14
                        radius: 2
                        color: theme.accentBorder
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spacingM

                        Text {
                            text: "\u21F1"
                            color: theme.textPrimary
                            font.pixelSize: 22
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: qsTr("Select")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("S")
                        color: theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: selectToolArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: selectTool.hovered = true
                        onExited: selectTool.hovered = false
                    }

                    Connections {
                        target: selectToolArea
                        function onClicked() {
                            root.toolSelected("select")
                        }
                    }
                }

                // ---- Move annotations ----
                Rectangle {
                    id: moveTool
                    width: parent.width
                    height: 52
                    radius: theme.radiusM
                    property bool selected: false
                    property bool hovered: false
                    color: selected ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                    border.color: selected ? theme.accentBorder : theme.border
                    border.width: 1

                    Rectangle {
                        visible: moveTool.selected
                        width: 3
                        height: parent.height - 14
                        radius: 2
                        color: theme.accentBorder
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spacingM

                        Text {
                            text: "\u2630"
                            color: theme.textPrimary
                            font.pixelSize: 20
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: qsTr("Move")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("V")
                        color: moveTool.selected ? "#bfe0ff" : theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: moveToolArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: moveTool.hovered = true
                        onExited: moveTool.hovered = false
                    }

                    Connections {
                        target: moveToolArea
                        function onClicked() {
                            root.toolSelected("move")
                        }
                    }
                }

                // ---- Box (default active tool) ----
                Rectangle {
                    id: bBox
                    width: parent.width
                    height: 52
                    radius: theme.radiusM
                    property bool selected: true
                    property bool hovered: false
                    color: selected ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                    border.color: selected ? theme.accentBorder : theme.border
                    border.width: 1

                    Rectangle {
                        visible: bBox.selected
                        width: 3
                        height: parent.height - 14
                        radius: 2
                        color: theme.accentBorder
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spacingM

                        Text {
                            text: "\u25A1"
                            color: theme.textPrimary
                            font.pixelSize: 22
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: qsTr("Box")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("B")
                        color: bBox.selected ? "#bfe0ff" : theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: boxToolArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: bBox.hovered = true
                        onExited: bBox.hovered = false
                    }

                    Connections {
                        target: boxToolArea
                        function onClicked() {
                            root.toolSelected("box")
                        }
                    }
                }

                // ---- Polygon ----
                Rectangle {
                    id: polygonTool
                    width: parent.width
                    height: 52
                    radius: theme.radiusM
                    property bool selected: false
                    property bool hovered: false
                    color: selected ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                    border.color: selected ? theme.accentBorder : theme.border
                    border.width: 1

                    Rectangle {
                        visible: polygonTool.selected
                        width: 3
                        height: parent.height - 14
                        radius: 2
                        color: theme.accentBorder
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spacingM

                        Text {
                            text: "\u2B21"
                            color: theme.textPrimary
                            font.pixelSize: 20
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: qsTr("Polygon")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("P")
                        color: theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: polygonToolArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: polygonTool.hovered = true
                        onExited: polygonTool.hovered = false
                    }

                    Connections {
                        target: polygonToolArea
                        function onClicked() {
                            root.toolSelected("polygon")
                        }
                    }
                }

                // Navigation tools are kept separate from annotation tools.
                Rectangle {
                    width: parent.width
                    height: 1
                    color: theme.border
                }

                Rectangle {
                    id: handTool
                    width: parent.width
                    height: 52
                    radius: theme.radiusM
                    property bool selected: false
                    property bool hovered: false
                    color: selected ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                    border.color: selected ? theme.accentBorder : theme.border
                    border.width: 1

                    Rectangle {
                        visible: handTool.selected
                        width: 3
                        height: parent.height - 14
                        radius: 2
                        color: theme.accentBorder
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spacingM

                        Text {
                            text: "\u270B"
                            color: theme.textPrimary
                            font.pixelSize: 20
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: qsTr("Hand")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("H")
                        color: handTool.selected ? "#bfe0ff" : theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: handToolArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: handTool.hovered = true
                        onExited: handTool.hovered = false
                    }

                    Connections {
                        target: handToolArea
                        function onClicked() {
                            root.toolSelected("hand")
                        }
                    }
                }
            }
        }

        // ========================================================
        // CENTER CANVAS
        // ========================================================
        Rectangle {
            id: canvasPanel
            anchors.top: parent.top
            anchors.left: leftPanel.right
            anchors.right: rightPanel.left
            anchors.bottom: parent.bottom
            color: theme.bgCanvas
            border.color: theme.border
            border.width: 1

            Rectangle {
                id: canvasToolbar
                height: 52
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                color: theme.bgPanelHeader
                border.color: theme.border
                border.width: 1

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: theme.spacingM
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: theme.spacingS

                    Rectangle {
                        width: 1
                        height: 24
                        color: theme.border
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        width: 38
                        height: 34
                        radius: theme.radiusS
                        property bool hovered: false
                        color: root.gridVisible ? theme.accentSoft : (hovered ? theme.bgChipHover : theme.bgChip)
                        border.color: root.gridVisible ? theme.accentBorder : theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "\u25A3"
                            color: theme.textPrimary
                            font.pixelSize: 17
                        }

                        MouseArea {
                            id: gridToggleArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                        }

                        ToolTip.visible: gridToggleArea.containsMouse
                        ToolTip.delay: 400
                        ToolTip.text: qsTr("Toggle grid")
                    }

                    Rectangle {
                        width: 1
                        height: 24
                        color: theme.border
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        id: zoomOutBtn
                        width: 34
                        height: 34
                        radius: theme.radiusS
                        property bool hovered: false
                        color: hovered ? theme.bgChipHover : theme.bgChip
                        border.color: theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "\u2212"
                            color: theme.textPrimary
                            font.pixelSize: 18
                        }

                        MouseArea {
                            id: zoomOutArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                        }

                        Connections {
                            target: zoomOutArea
                            function onClicked() {
                                root.zoomOutRequested()
                            }
                        }
                    }

                    Rectangle {
                        width: 78
                        height: 34
                        radius: theme.radiusS
                        color: theme.bgInput
                        border.color: theme.borderStrong
                        border.width: 1

                        Text {
                            id: zoomPercentText
                            anchors.centerIn: parent
                            text: qsTr("100%")
                            color: theme.textPrimary
                            font.family: Constants.font.family
                            font.pixelSize: 13
                        }
                    }

                    Rectangle {
                        id: zoomInBtn
                        width: 34
                        height: 34
                        radius: theme.radiusS
                        property bool hovered: false
                        color: hovered ? theme.bgChipHover : theme.bgChip
                        border.color: theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "+"
                            color: theme.textPrimary
                            font.pixelSize: 18
                        }

                        MouseArea {
                            id: zoomInArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                        }

                        Connections {
                            target: zoomInArea
                            function onClicked() {
                                root.zoomInRequested()
                            }
                        }
                    }

                    Rectangle {
                        id: fitBtn
                        width: 38
                        height: 34
                        radius: theme.radiusS
                        property bool hovered: false
                        color: hovered ? theme.bgChipHover : theme.bgChip
                        border.color: theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "\u26F6"
                            color: theme.textPrimary
                            font.pixelSize: 17
                        }

                        MouseArea {
                            id: fitArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                        }

                        Connections {
                            target: fitArea
                            function onClicked() {
                                root.fitRequested()
                            }
                        }

                        ToolTip.visible: fitArea.containsMouse
                        ToolTip.delay: 400
                        ToolTip.text: qsTr("Fit to screen")
                    }
                }
            }

            Rectangle {
                id: imageCanvas
                anchors.top: canvasToolbar.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                color: theme.bgCanvas
                clip: true

                // Scroll up/down anywhere on the canvas to zoom in/out.
                // The existing logic layer clamps the zoom to 25%–400%.
                WheelHandler {
                    id: canvasWheelHandler
                }

                Image {
                    id: canvasImage
                    anchors.centerIn: parent
                    anchors.horizontalCenterOffset: root.canvasPanX
                    anchors.verticalCenterOffset: root.canvasPanY
                    width: Math.max(0, Math.min(parent.width - 50, 900))
                    height: Math.max(0, Math.min(parent.height - 50, 620))
                    fillMode: Image.PreserveAspectFit
                    source: ""
                    transformOrigin: Item.Center

                    Behavior on scale {
                        NumberAnimation {
                            duration: 140
                        }
                    }
                }

                // Screen-aligned composition grid, kept behind annotations.
                Item {
                    id: gridOverlay
                    anchors.fill: parent
                    z: 1
                    visible: root.gridVisible
                    property int gridSize: 32

                    Repeater {
                        // An anchored parent can briefly have a negative width
                        // while the surrounding panels are being laid out.
                        model: Math.max(
                                   0, Math.ceil(
                                       gridOverlay.width / gridOverlay.gridSize) + 1)

                        delegate: Rectangle {
                            x: index * gridOverlay.gridSize
                            width: 1
                            height: gridOverlay.height
                            color: "#26343b"
                        }
                    }

                    Repeater {
                        // Do not pass a negative count to Repeater during layout.
                        model: Math.max(
                                   0, Math.ceil(
                                       gridOverlay.height / gridOverlay.gridSize) + 1)

                        delegate: Rectangle {
                            y: index * gridOverlay.gridSize
                            width: gridOverlay.width
                            height: 1
                            color: "#26343b"
                        }
                    }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: theme.spacingS
                    visible: canvasImage.status !== Image.Ready

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: qsTr("IMAGE CANVAS")
                        color: theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 23
                        font.bold: true
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: qsTr("Open an image to begin annotation")
                        color: theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 13
                    }
                }

                // Keep annotations and their input coordinates inside the painted
                // portion of the image (not the letterboxed canvas around it).
                Item {
                    id: annotationLayer
                    x: canvasImage.x + (canvasImage.width - width) / 2
                    y: canvasImage.y + (canvasImage.height - height) / 2
                    // In Design Studio (and while an image is loading), an Image
                    // has no painted size yet. Fall back to its frame so box-tool
                    // previews and annotations remain visible.
                    width: canvasImage.paintedWidth
                           > 0 ? canvasImage.paintedWidth : canvasImage.width
                    height: canvasImage.paintedHeight
                            > 0 ? canvasImage.paintedHeight : canvasImage.height
                    z: 2
                    // drawingArea extends to the full canvas so tools can start
                    // outside the image; its event handlers snap coordinates back
                    // to this image-bounded layer.
                    clip: false
                    scale: canvasImage.scale
                    transformOrigin: Item.Center

                    // Every canvas annotation is driven by the same model as the Objects panel.
                    Repeater {
                        model: objectsModel

                        delegate: Item {
                            anchors.fill: parent
                            z: 2
                            clip: true
                            // Preserve the annotation's size where possible and
                            // shift it back into the image if the canvas is resized.
                            property real boundedWidth: Math.min(
                                                            Math.max(
                                                                0, model.boxW),
                                                            parent.width)
                            property real boundedHeight: Math.min(
                                                             Math.max(
                                                                 0,
                                                                 model.boxH),
                                                             parent.height)
                            property real boundedX: Math.max(
                                                        0, Math.min(
                                                            model.boxX,
                                                            parent.width - boundedWidth))
                            property real boundedY: Math.max(
                                                        0, Math.min(
                                                            model.boxY,
                                                            parent.height - boundedHeight))

                            // The selection hit area uses the same model row as the
                            // object list. This keeps canvas, list, and properties
                            // selection in sync through root.objectSelected(index).
                            MouseArea {
                                id: annotationSelectArea
                                x: parent.boundedX
                                y: parent.boundedY
                                width: Math.max(8, parent.boundedWidth)
                                height: Math.max(8, parent.boundedHeight)
                                visible: root.activeTool === "select"
                                enabled: visible
                                cursorShape: Qt.PointingHandCursor
                            }

                            Connections {
                                target: annotationSelectArea
                                function onClicked() {
                                    root.objectSelected(index)
                                }
                            }

                            // Move mode is intentionally limited to annotation
                            // hit areas; it cannot move or pan the image itself.
                            MouseArea {
                                id: annotationMoveArea
                                x: parent.boundedX
                                y: parent.boundedY
                                width: Math.max(8, parent.boundedWidth)
                                height: Math.max(8, parent.boundedHeight)
                                visible: root.activeTool === "move"
                                enabled: visible
                                acceptedButtons: Qt.LeftButton
                                cursorShape: pressed ? Qt.SizeAllCursor : Qt.ArrowCursor
                                property real lastCanvasX: 0
                                property real lastCanvasY: 0
                            }

                            Connections {
                                target: annotationMoveArea

                                function onPressed(mouse) {
                                    const position = annotationMoveArea.mapToItem(
                                                       annotationLayer,
                                                       mouse.x, mouse.y)
                                    annotationMoveArea.lastCanvasX = position.x
                                    annotationMoveArea.lastCanvasY = position.y
                                    root.objectSelected(index)
                                }

                                function onPositionChanged(mouse) {
                                    if (!annotationMoveArea.pressed)
                                        return
                                    const position = annotationMoveArea.mapToItem(
                                                       annotationLayer,
                                                       mouse.x, mouse.y)
                                    root.annotationMoveRequested(
                                                index,
                                                position.x - annotationMoveArea.lastCanvasX,
                                                position.y - annotationMoveArea.lastCanvasY)
                                    annotationMoveArea.lastCanvasX = position.x
                                    annotationMoveArea.lastCanvasY = position.y
                                }
                            }

                            Rectangle {
                                visible: model.shape !== "polygon"
                                x: parent.boundedX
                                y: parent.boundedY
                                width: parent.boundedWidth
                                height: parent.boundedHeight
                                color: "transparent"
                                border.color: model.colorHex
                                border.width: model.selected ? 3 : 2
                            }

                            Rectangle {
                                visible: model.shape !== "polygon"
                                x: parent.boundedX
                                y: parent.boundedY
                                width: annotationLabel.implicitWidth + 18
                                height: 24
                                color: model.colorHex

                                Text {
                                    id: annotationLabel
                                    anchors.centerIn: parent
                                    text: model.label
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }
                        }
                    }

                    Repeater {
                        model: root.polygonPaths

                        delegate: Item {
                            anchors.fill: parent
                            z: 2
                            clip: true

                            Shape {
                                anchors.fill: parent

                                ShapePath {
                                    strokeColor: modelData.colorHex
                                    strokeWidth: 3
                                    fillColor: "transparent"

                                    PathPolyline {
                                        // Points are captured by drawingArea, which
                                        // is bounded to annotationLayer (the painted
                                        // image area). The delegate clips previously
                                        // saved paths to the same image bounds.
                                        path: modelData.points
                                    }
                                }
                            }

                            Rectangle {
                                x: modelData.boxX
                                y: modelData.boxY
                                width: polygonLabel.implicitWidth + 18
                                height: 24
                                color: modelData.colorHex

                                Text {
                                    id: polygonLabel
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: draftBox
                        // A first click starts a draft; the outline then follows
                        // the cursor until the next click finishes it.
                        visible: drawingArea.drawing
                        // currentX/Y are initialized on press and updated while
                        // the pointer is held and moved.
                        property real previewX: drawingArea.currentX
                        property real previewY: drawingArea.currentY
                        // Keep the drag outline within the painted image area.
                        x: Math.abs(previewX - drawingArea.startX)
                           < drawingArea.minimumBoxSize ? Math.min(
                                                              drawingArea.startX,
                                                              Math.max(
                                                                  0,
                                                                  annotationLayer.width - drawingArea.minimumBoxSize)) : (previewX < drawingArea.startX ? previewX : drawingArea.startX)
                        y: Math.abs(previewY - drawingArea.startY)
                           < drawingArea.minimumBoxSize ? Math.min(
                                                              drawingArea.startY,
                                                              Math.max(
                                                                  0,
                                                                  annotationLayer.height - drawingArea.minimumBoxSize)) : (previewY < drawingArea.startY ? previewY : drawingArea.startY)
                        width: Math.abs(previewX - drawingArea.startX)
                               < drawingArea.minimumBoxSize ? Math.min(
                                                                  drawingArea.minimumBoxSize,
                                                                  annotationLayer.width) : Math.abs(
                                                                  previewX - drawingArea.startX)
                        height: Math.abs(previewY - drawingArea.startY)
                                < drawingArea.minimumBoxSize ? Math.min(
                                                                   drawingArea.minimumBoxSize,
                                                                   annotationLayer.height) : Math.abs(
                                                                   previewY - drawingArea.startY)
                        z: 3
                        color: "transparent"
                        border.color: theme.accentBorder
                        border.width: 2
                    }

                    Shape {
                        visible: root.activeTool === "polygon"
                                 && drawingArea.polygonPreviewPoints.length > 1
                        anchors.fill: parent
                        z: 3

                        ShapePath {
                            strokeColor: theme.accentBorder
                            strokeWidth: 2
                            fillColor: "transparent"

                            PathPolyline {
                                path: drawingArea.polygonPreviewPoints
                            }
                        }
                    }

                    Repeater {
                        model: drawingArea.polygonPoints

                        delegate: Rectangle {
                            x: modelData.x - 4
                            y: modelData.y - 4
                            width: 8
                            height: 8
                            radius: 4
                            z: 5
                            color: theme.accentBorder
                        }
                    }

                    MouseArea {
                        id: drawingArea
                        // Receive pointer events over the full canvas. Coordinates
                        // are converted and clamped in the Connections block below.
                        x: -annotationLayer.x
                        y: -annotationLayer.y
                        width: imageCanvas.width
                        height: imageCanvas.height
                        // The annotation layer zooms with the image; cancel that
                        // transform here so the hit target always covers the canvas.
                        scale: 1 / annotationLayer.scale
                        transformOrigin: Item.Center
                        z: 4
                        enabled: root.activeTool === "box"
                                 || root.activeTool === "polygon"
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        hoverEnabled: true
                        cursorShape: enabled ? Qt.CrossCursor : Qt.ArrowCursor
                        property bool drawing: false
                        // A second click finishes a pending click-to-draw box.
                        // A held drag still finishes on release.
                        property bool secondBoxPoint: false
                        property bool draggedSincePress: false
                        property real startX: 0
                        property real startY: 0
                        property real currentX: 0
                        property real currentY: 0
                        property int minimumBoxSize: 24
                        property var polygonPoints: []
                        property var polygonPreviewPoints: []
                    }

                    Connections {
                        target: drawingArea

                        function onPressed(mouse) {
                            if (root.activeTool === "box") {
                                // drawingArea cancels annotationLayer's scale to
                                // cover the full canvas. Map the pointer through
                                // that transform so annotation coordinates stay
                                // relative to the underlying image.
                                const imagePosition = drawingArea.mapToItem(
                                                        annotationLayer,
                                                        mouse.x, mouse.y)
                                const x = Math.max(0, Math.min(
                                                       imagePosition.x,
                                                       annotationLayer.width))
                                const y = Math.max(0, Math.min(
                                                       imagePosition.y,
                                                       annotationLayer.height))
                                drawingArea.draggedSincePress = false
                                if (drawingArea.drawing) {
                                    drawingArea.secondBoxPoint = true
                                    drawingArea.currentX = x
                                    drawingArea.currentY = y
                                } else {
                                    drawingArea.startX = x
                                    drawingArea.startY = y
                                    drawingArea.currentX = x
                                    drawingArea.currentY = y
                                    drawingArea.drawing = true
                                }
                            }
                        }

                        function onPositionChanged(mouse) {
                            const imagePosition = drawingArea.mapToItem(
                                                    annotationLayer,
                                                    mouse.x, mouse.y)
                            const x = Math.max(0,
                                               Math.min(imagePosition.x,
                                                        annotationLayer.width))
                            const y = Math.max(0,
                                               Math.min(imagePosition.y,
                                                        annotationLayer.height))
                            if (root.activeTool === "box"
                                    && drawingArea.drawing) {
                                drawingArea.currentX = x
                                drawingArea.currentY = y
                                if (drawingArea.pressed
                                        && (Math.abs(
                                                x - drawingArea.startX) >= 8
                                            || Math.abs(
                                                y - drawingArea.startY) >= 8)) {
                                    drawingArea.draggedSincePress = true
                                }
                            } else if (root.activeTool === "polygon") {
                                if (drawingArea.polygonPoints.length > 1) {
                                    drawingArea.polygonPreviewPoints
                                            = drawingArea.polygonPoints.concat(
                                                [Qt.point(
                                                     x,
                                                     y), drawingArea.polygonPoints[0]])
                                } else {
                                    drawingArea.polygonPreviewPoints
                                            = drawingArea.polygonPoints.concat(
                                                [Qt.point(x, y)])
                                }
                            }
                        }

                        function onReleased(mouse) {
                            if (root.activeTool === "box"
                                    && drawingArea.drawing) {
                                const imagePosition = drawingArea.mapToItem(
                                                        annotationLayer,
                                                        mouse.x, mouse.y)
                                const x = Math.max(0, Math.min(
                                                       imagePosition.x,
                                                       annotationLayer.width))
                                const y = Math.max(0, Math.min(
                                                       imagePosition.y,
                                                       annotationLayer.height))
                                drawingArea.currentX = x
                                drawingArea.currentY = y
                                const releasedAsDrag = Math.abs(
                                                         x - drawingArea.startX) >= 8
                                                     || Math.abs(
                                                         y - drawingArea.startY) >= 8

                                if (drawingArea.secondBoxPoint
                                        || drawingArea.draggedSincePress
                                        || releasedAsDrag) {
                                    root.boxDrawn(
                                                drawingArea.startX,
                                                drawingArea.startY,
                                                drawingArea.currentX - drawingArea.startX,
                                                drawingArea.currentY - drawingArea.startY)
                                }
                                if (drawingArea.secondBoxPoint
                                        || drawingArea.draggedSincePress
                                        || releasedAsDrag) {
                                    drawingArea.drawing = false
                                    drawingArea.secondBoxPoint = false
                                    drawingArea.draggedSincePress = false
                                }
                            }
                        }

                        function onClicked(mouse) {
                            if (root.activeTool !== "polygon")
                                return

                            const imagePosition = drawingArea.mapToItem(
                                                    annotationLayer,
                                                    mouse.x, mouse.y)
                            const x = Math.max(0,
                                               Math.min(imagePosition.x,
                                                        annotationLayer.width))
                            const y = Math.max(0,
                                               Math.min(imagePosition.y,
                                                        annotationLayer.height))

                            if (mouse.button === Qt.RightButton) {
                                if (drawingArea.polygonPoints.length >= 3) {
                                    root.polygonDrawn(drawingArea.polygonPoints)
                                }
                                // A right-click before three points cancels the
                                // unfinished polygon; after three it completes it.
                                drawingArea.polygonPoints = []
                                drawingArea.polygonPreviewPoints = []
                            } else if (mouse.button === Qt.LeftButton) {
                                drawingArea.polygonPoints = drawingArea.polygonPoints.concat(
                                            [Qt.point(x, y)])
                                drawingArea.polygonPreviewPoints = drawingArea.polygonPoints
                            }
                        }
                    }

                    // Middle-mouse (scroll-wheel) drag always pans. With the Hand
                    // tool selected, left-mouse drag pans too.
                    MouseArea {
                        id: canvasPanArea
                        anchors.fill: parent
                        z: 6
                        acceptedButtons: root.activeTool === "hand" ? Qt.LeftButton | Qt.MiddleButton : Qt.MiddleButton
                        hoverEnabled: true
                        cursorShape: root.activeTool === "hand" ? (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor) : (root.activeTool === "box" || root.activeTool === "polygon" ? Qt.CrossCursor : (root.activeTool === "move" ? Qt.SizeAllCursor : Qt.ArrowCursor))
                    }

                    Connections {
                        target: canvasPanArea

                        function onPressed(mouse) {
                            const position = canvasPanArea.mapToItem(
                                               imageCanvas, mouse.x, mouse.y)
                            root.canvasPanStarted(position.x, position.y)
                        }

                        function onPositionChanged(mouse) {
                            const position = canvasPanArea.mapToItem(
                                               imageCanvas, mouse.x, mouse.y)
                            // canvasPanArea sits above drawingArea, so use its
                            // hover motion to keep a first-click draft box live.
                            if (root.activeTool === "box" && drawingArea.drawing
                                    && !drawingArea.secondBoxPoint) {
                                const imagePosition = canvasPanArea.mapToItem(
                                                        annotationLayer,
                                                        mouse.x, mouse.y)
                                drawingArea.currentX = Math.max(
                                            0, Math.min(imagePosition.x,
                                                        annotationLayer.width))
                                drawingArea.currentY = Math.max(
                                            0, Math.min(imagePosition.y,
                                                        annotationLayer.height))
                            }
                            root.canvasPanMoved(position.x, position.y)
                        }

                        function onReleased() {
                            root.canvasPanFinished()
                        }
                    }
                }
            }
        }

        // ========================================================
        // RIGHT PANEL
        // ========================================================
        Rectangle {
            id: rightPanel
            width: Math.round(Math.max(250, Math.min(310, root.width * 0.20)))
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            color: theme.bgPanel
            border.color: theme.border
            border.width: 1

            Rectangle {
                id: objectsPanel
                height: 300
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                color: theme.bgPanel

                Rectangle {
                    id: classesHeader
                    height: 52
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    color: theme.bgPanelHeader
                    border.color: theme.border

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: theme.spacingL
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Classes")
                        color: theme.textSecondary
                        font.family: Constants.font.family
                        font.pixelSize: 13
                        font.bold: true
                        font.letterSpacing: 1
                    }

                    Text {
                        id: objectsCountText
                        anchors.left: parent.left
                        anchors.leftMargin: 92
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("3")
                        color: theme.textFaint
                        font.family: Constants.font.family
                        font.pixelSize: 13
                    }

                    Rectangle {
                        id: addObjectBtn
                        width: 32
                        height: 32
                        radius: theme.radiusS
                        anchors.right: parent.right
                        anchors.rightMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        property bool hovered: false
                        color: hovered ? theme.bgChipHover : theme.bgPanelHeader
                        border.color: theme.borderStrong
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "+"
                            color: theme.textPrimary
                            font.pixelSize: 20
                        }

                        MouseArea {
                            id: addObjectArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                        }

                        Connections {
                            target: addObjectArea
                            function onClicked() {
                                root.addObjectRequested()
                            }
                        }

                        ToolTip.visible: addObjectArea.containsMouse
                        ToolTip.delay: 400
                        ToolTip.text: qsTr("Add object")
                    }
                }

                // Backing data for the list below. Kept as a ListModel
                // (rather than a plain JS array) so the logic layer can
                // append/remove/update rows for Add, Duplicate and Delete.
                ListModel {
                    id: objectsModel
                }

                Flickable {
                    id: objectsScrollView
                    anchors.top: classesHeader.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    clip: true
                    contentWidth: width
                    contentHeight: objectsList.height
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }

                    Column {
                        id: objectsList
                        width: objectsScrollView.width
                        spacing: 1

                        Repeater {
                            id: objectsRepeater
                            model: objectsModel

                            delegate: Rectangle {
                                width: parent ? parent.width : 0
                                height: 52
                                property bool hovered: false
                                color: model.selected ? theme.accentTint : (hovered ? theme.bgChipHover : theme.bgPanel)
                                border.color: model.selected ? theme.accentBorder : "transparent"
                                border.width: 1

                                Rectangle {
                                    width: 16
                                    height: 16
                                    radius: 3
                                    anchors.left: parent.left
                                    anchors.leftMargin: theme.spacingL
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: model.colorHex
                                }

                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 46
                                    anchors.right: layerActions.left
                                    anchors.rightMargin: theme.spacingS
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: model.label
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 15
                                }

                                Row {
                                    id: layerActions
                                    anchors.right: parent.right
                                    anchors.rightMargin: theme.spacingM
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: theme.spacingS
                                    visible: model.selected || parent.hovered
                                    z: 1

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: theme.radiusS
                                        property bool hovered: false
                                        color: hovered ? theme.bgChipHover : "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: model.locked ? "\u{1F512}" : "\u{1F513}"
                                            color: model.locked ? theme.textPrimary : theme.textSecondary
                                            font.pixelSize: 13
                                        }

                                        MouseArea {
                                            id: layerLockArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onEntered: parent.hovered = true
                                            onExited: parent.hovered = false
                                        }

                                        Connections {
                                            target: layerLockArea
                                            function onClicked() {
                                                root.objectSelected(index)
                                                root.lockRequested()
                                            }
                                        }

                                        ToolTip.visible: layerLockArea.containsMouse
                                        ToolTip.delay: 400
                                        ToolTip.text: model.locked ? qsTr("Unlock layer") : qsTr(
                                                                         "Lock layer")
                                    }

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: theme.radiusS
                                        property bool hovered: false
                                        color: hovered ? "#2e1e20" : "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: "\u2715"
                                            color: theme.danger
                                            font.pixelSize: 14
                                        }

                                        MouseArea {
                                            id: layerDeleteArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onEntered: parent.hovered = true
                                            onExited: parent.hovered = false
                                        }

                                        Connections {
                                            target: layerDeleteArea
                                            function onClicked() {
                                                root.objectSelected(index)
                                                root.deleteRequested()
                                            }
                                        }

                                        ToolTip.visible: layerDeleteArea.containsMouse
                                        ToolTip.delay: 400
                                        ToolTip.text: qsTr("Delete layer")
                                    }
                                }

                                MouseArea {
                                    id: rowArea
                                    anchors.fill: parent
                                    z: 0
                                    hoverEnabled: true
                                    onEntered: parent.hovered = true
                                    onExited: parent.hovered = false
                                }

                                Connections {
                                    target: rowArea
                                    function onClicked() {
                                        root.objectSelected(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: theme.border
                anchors.top: objectsPanel.bottom
            }

            Rectangle {
                id: propertiesPanel
                anchors.top: objectsPanel.bottom
                anchors.topMargin: 1
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                color: theme.bgPanel

                Text {
                    id: propertiesHeading
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.topMargin: theme.spacingL
                    anchors.leftMargin: theme.spacingL
                    text: qsTr("PROPERTIES")
                    color: theme.textSecondary
                    font.family: Constants.font.family
                    font.pixelSize: 13
                    font.bold: true
                    font.letterSpacing: 1
                }

                // Current label chip
                Rectangle {
                    id: labelChip
                    anchors.top: propertiesHeading.bottom
                    anchors.topMargin: theme.spacingM
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: theme.spacingL
                    anchors.rightMargin: theme.spacingL
                    height: 42
                    radius: theme.radiusS
                    color: theme.bgInput
                    border.color: theme.borderStrong
                    border.width: 1

                    Rectangle {
                        id: labelChipSwatch
                        width: 14
                        height: 14
                        radius: 3
                        anchors.left: parent.left
                        anchors.leftMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        color: theme.classPerson
                    }

                    Text {
                        id: labelChipText
                        anchors.left: parent.left
                        anchors.leftMargin: 36
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("person")
                        color: theme.textPrimary
                        font.family: Constants.font.family
                        font.pixelSize: 14
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: "\u25BE"
                        color: theme.textMuted
                        font.pixelSize: 13
                    }
                }

                // Native dimensions of the currently loaded image.
                Rectangle {
                    id: imagePixelSizeField
                    anchors.top: labelChip.bottom
                    anchors.topMargin: theme.spacingM
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: theme.spacingL
                    anchors.rightMargin: theme.spacingL
                    height: 48
                    radius: theme.radiusS
                    color: theme.bgInput
                    border.color: theme.borderStrong
                    border.width: 1

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Image pixel size"
                        color: theme.textMuted
                        font.family: Constants.font.family
                        font.pixelSize: 11
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: theme.spacingM
                        anchors.verticalCenter: parent.verticalCenter
                        text: canvasImage.status
                              === Image.Ready ? canvasImage.sourceSize.width + " x "
                                                + canvasImage.sourceSize.height
                                                + " px" : "No image loaded"
                        color: theme.textPrimary
                        font.family: Constants.font.family
                        font.pixelSize: 14
                    }
                }

                Column {
                    id: fieldsColumn
                    anchors.top: imagePixelSizeField.bottom
                    anchors.topMargin: theme.spacingM
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: theme.spacingL
                    anchors.rightMargin: theme.spacingL
                    spacing: theme.spacingS

                    Row {
                        width: parent.width
                        height: 60
                        spacing: theme.spacingS

                        Column {
                            width: (parent.width - theme.spacingS) / 2
                            spacing: 4

                            Text {
                                text: qsTr("X")
                                color: theme.textMuted
                                font.family: Constants.font.family
                                font.pixelSize: 11
                            }

                            Rectangle {
                                width: parent.width
                                height: 38
                                radius: theme.radiusS
                                color: theme.bgInput
                                border.color: theme.borderStrong
                                border.width: 1

                                Text {
                                    id: xValueText
                                    anchors.left: parent.left
                                    anchors.leftMargin: theme.spacingM
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("0")
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 14
                                }
                            }
                        }

                        Column {
                            width: (parent.width - theme.spacingS) / 2
                            spacing: 4

                            Text {
                                text: qsTr("Y")
                                color: theme.textMuted
                                font.family: Constants.font.family
                                font.pixelSize: 11
                            }

                            Rectangle {
                                width: parent.width
                                height: 38
                                radius: theme.radiusS
                                color: theme.bgInput
                                border.color: theme.borderStrong
                                border.width: 1

                                Text {
                                    id: yValueText
                                    anchors.left: parent.left
                                    anchors.leftMargin: theme.spacingM
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("0")
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 14
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: 60
                        spacing: theme.spacingS

                        Column {
                            width: (parent.width - theme.spacingS) / 2
                            spacing: 4

                            Text {
                                text: qsTr("Width")
                                color: theme.textMuted
                                font.family: Constants.font.family
                                font.pixelSize: 11
                            }

                            Rectangle {
                                width: parent.width
                                height: 38
                                radius: theme.radiusS
                                color: theme.bgInput
                                border.color: theme.borderStrong
                                border.width: 1

                                Text {
                                    id: widthValueText
                                    anchors.left: parent.left
                                    anchors.leftMargin: theme.spacingM
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("0")
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 14
                                }
                            }
                        }

                        Column {
                            width: (parent.width - theme.spacingS) / 2
                            spacing: 4

                            Text {
                                text: qsTr("Height")
                                color: theme.textMuted
                                font.family: Constants.font.family
                                font.pixelSize: 11
                            }

                            Rectangle {
                                width: parent.width
                                height: 38
                                radius: theme.radiusS
                                color: theme.bgInput
                                border.color: theme.borderStrong
                                border.width: 1

                                Text {
                                    id: heightValueText
                                    anchors.left: parent.left
                                    anchors.leftMargin: theme.spacingM
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("0")
                                    color: theme.textPrimary
                                    font.family: Constants.font.family
                                    font.pixelSize: 14
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ============================================================
    // BOTTOM IMAGE NAVIGATION
    // ============================================================
    Rectangle {
        id: bottomBar
        height: 92
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: theme.bgPanel
        border.color: theme.border
        border.width: 1

        // Draggable dataset progress control. The logic layer keeps its value
        // synchronized with Next/Previous and responds continuously to drag.
        Slider {
            id: imageProgressSlider
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 4
            anchors.leftMargin: theme.spacingL
            anchors.rightMargin: theme.spacingL
            height: 18
            from: 1
            to: 500
            value: 1
            stepSize: 1
            snapMode: Slider.SnapAlways

            background: Rectangle {
                x: imageProgressSlider.leftPadding
                y: imageProgressSlider.topPadding
                   + (imageProgressSlider.availableHeight - height) / 2
                width: imageProgressSlider.availableWidth
                height: 6
                radius: 3
                color: theme.bgInput
                border.color: theme.border
                border.width: 1

                Rectangle {
                    width: imageProgressSlider.visualPosition * parent.width
                    height: parent.height
                    radius: parent.radius
                    color: theme.accent
                }
            }

            handle: Rectangle {
                x: imageProgressSlider.leftPadding + imageProgressSlider.visualPosition
                   * (imageProgressSlider.availableWidth - width)
                y: imageProgressSlider.topPadding
                   + (imageProgressSlider.availableHeight - height) / 2
                width: 14
                height: 14
                radius: 7
                color: imageProgressSlider.pressed ? theme.accentBorder : theme.textPrimary
                border.color: theme.accent
                border.width: 2

                Behavior on scale {
                    NumberAnimation {
                        duration: 120
                    }
                }

                scale: imageProgressSlider.pressed ? 1.2 : (imageProgressSlider.hovered ? 1.08 : 1.0)
            }
        }

        Row {
            id: imageThumbnailStrip
            anchors.top: imageProgressSlider.bottom
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: theme.spacingM

            Rectangle {
                id: prevBtn
                width: 44
                height: 48
                anchors.verticalCenter: parent.verticalCenter
                radius: theme.radiusS
                property bool hovered: false
                color: hovered ? theme.bgChipHover : theme.bgChip
                border.color: theme.borderStrong
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "\u2039"
                    color: theme.textPrimary
                    font.pixelSize: 28
                }

                MouseArea {
                    id: prevArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: parent.hovered = true
                    onExited: parent.hovered = false
                }

                Connections {
                    target: prevArea
                    function onClicked() {
                        root.prevImageRequested()
                    }
                }

                ToolTip.visible: prevArea.containsMouse
                ToolTip.delay: 400
                ToolTip.text: qsTr("Previous image")
            }

            Rectangle {
                width: 240
                height: 56
                anchors.verticalCenter: parent.verticalCenter
                radius: theme.radiusS
                color: theme.accentTint
                border.color: theme.accentBorder
                border.width: 1

                Rectangle {
                    width: 48
                    height: 48
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    radius: theme.radiusS
                    color: theme.bgChip
                    border.color: theme.borderStrong
                    border.width: 1
                    clip: true

                    Image {
                        anchors.fill: parent
                        source: canvasImage.source
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: 48
                        sourceSize.height: 48
                        asynchronous: true
                        cache: true
                        smooth: false
                    }
                }

                Text {
                    id: currentImageNameText
                    anchors.left: parent.left
                    anchors.leftMargin: 62
                    anchors.top: parent.top
                    anchors.topMargin: 11
                    text: qsTr("image_001.jpg")
                    color: theme.textPrimary
                    font.family: Constants.font.family
                    font.pixelSize: 14
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 62
                    anchors.top: parent.top
                    anchors.topMargin: 32
                    text: qsTr("Current image")
                    color: theme.textMuted
                    font.family: Constants.font.family
                    font.pixelSize: 11
                }
            }

            Rectangle {
                width: 108
                height: 42
                anchors.verticalCenter: parent.verticalCenter
                radius: theme.radiusS
                color: theme.bgInput
                border.color: theme.borderStrong
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    height: parent.height
                    spacing: 4

                    TextField {
                        id: pageIndexInput
                        width: 30
                        height: parent.height
                        text: "1"
                        color: theme.textPrimary
                        font.family: Constants.font.family
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        selectByMouse: true
                        // Page number can be edited only while it has focus.
                        // Clicking elsewhere returns it to a display-only state.
                        readOnly: !activeFocus
                        cursorVisible: activeFocus
                        validator: IntValidator {
                            bottom: 1
                            top: 999999
                        }

                        background: Rectangle {
                            color: "transparent"
                        }
                    }

                    Text {
                        text: "/"
                        color: theme.textPrimary
                        font.family: Constants.font.family
                        font.pixelSize: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        id: pageTotalText
                        text: "500"
                        color: theme.textPrimary
                        font.family: Constants.font.family
                        font.pixelSize: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Connections {
                    target: pageIndexInput

                    function onAccepted() {
                        root.imageIndexRequested(Number(pageIndexInput.text))
                        pageIndexInput.focus = false
                        pageIndexInput.deselect()
                    }

                    function onEditingFinished() {
                        pageIndexInput.focus = false
                        pageIndexInput.deselect()
                    }

                    function onActiveFocusChanged() {
                        if (!pageIndexInput.activeFocus)
                            pageIndexInput.deselect()
                    }
                }
            }

            Rectangle {
                width: 240
                height: 56
                anchors.verticalCenter: parent.verticalCenter
                radius: theme.radiusS
                property bool hovered: false
                color: hovered ? theme.bgChipHover : "transparent"
                border.color: hovered ? theme.border : "transparent"
                border.width: 1

                Rectangle {
                    width: 48
                    height: 48
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    radius: theme.radiusS
                    color: theme.bgChip
                    border.color: theme.borderStrong
                    border.width: 1
                    clip: true

                    Image {
                        anchors.fill: parent
                        source: root.nextImageSource
                        fillMode: Image.PreserveAspectCrop
                        sourceSize.width: 48
                        sourceSize.height: 48
                        asynchronous: true
                        cache: true
                        smooth: false
                    }
                }

                Text {
                    id: nextImageNameText
                    anchors.left: parent.left
                    anchors.leftMargin: 62
                    anchors.top: parent.top
                    anchors.topMargin: 11
                    text: qsTr("image_002.jpg")
                    color: theme.textPrimary
                    font.family: Constants.font.family
                    font.pixelSize: 14
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 62
                    anchors.top: parent.top
                    anchors.topMargin: 32
                    text: qsTr("Up next")
                    color: theme.textMuted
                    font.family: Constants.font.family
                    font.pixelSize: 11
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: parent.hovered = true
                    onExited: parent.hovered = false
                }
            }

            Rectangle {
                id: nextBtn
                width: 44
                height: 48
                anchors.verticalCenter: parent.verticalCenter
                radius: theme.radiusS
                property bool hovered: false
                color: hovered ? theme.bgChipHover : theme.bgChip
                border.color: theme.borderStrong
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "\u203A"
                    color: theme.textPrimary
                    font.pixelSize: 28
                }

                MouseArea {
                    id: nextArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: parent.hovered = true
                    onExited: parent.hovered = false
                }

                Connections {
                    target: nextArea
                    function onClicked() {
                        root.nextImageRequested()
                    }
                }

                ToolTip.visible: nextArea.containsMouse
                ToolTip.delay: 400
                ToolTip.text: qsTr("Next image")
            }
        }
    }
}

/*
This is the logic layer for AnnotationForm.ui.qml.

Qt Design Studio keeps .ui.qml files purely declarative (visuals only), so
all behavior -- tool switching, selection state, button actions, zoom,
image navigation -- lives here instead. The .ui.qml exposes the ids it
needs to be driven (via `property alias`) and a set of signals for every
interactive element; this file listens to those signals and updates the
exposed elements directly.

Save this file as AnnotationForm.qml next to AnnotationForm.ui.qml so the
type name below resolves.
*/
import QtQuick
import Qt.labs.folderlistmodel

AnnotationForm {
    id: form
    focus: true

    // ------------------------------------------------------------
    // State
    // ------------------------------------------------------------
    property string currentTool: "box"
    property int currentImageIndex: 1
    property int totalImages: 0
    property int zoomPercent: 100
    readonly property var staticClasses: [
        { classId: "class0", label: qsTr("A"), colorHex: "#2389ff" },
        { classId: "class1", label: qsTr("B"), colorHex: "#58c62e" },
        { classId: "class2", label: qsTr("C"), colorHex: "#ff9818" },
        { classId: "class3", label: qsTr("D"), colorHex: "#bd6cff" }
    ]
    property int currentClassIndex: 0
    property int nextAnnotationId: 0
    property string toolBeforePan: "box"
    property bool panShortcutActive: false
    property bool canvasPanning: false
    property real lastPanX: 0
    property real lastPanY: 0
    property var undoStack: []
    property var redoStack: []
    // Annotation data is isolated by the 1-based dataset image index.
    property var annotationsByImage: ({})
    property bool restoringHistory: false
    property real previousAnnotationLayerWidth: 0
    property real previousAnnotationLayerHeight: 0
    // Qt Design Studio can preview this component without starting the Python
    // launcher. In that mode the context property is intentionally absent.
    readonly property var exportBackend: typeof datasetExporter !== "undefined"
                                         ? datasetExporter : null

    FolderListModel {
        id: datasetFolderModel

        folder: Qt.resolvedUrl("../../Images")
        nameFilters: ["*.bmp", "*.gif", "*.jpeg", "*.jpg", "*.png", "*.webp"]
        showDirs: false
        sortField: FolderListModel.Name

        onCountChanged: form.refreshDatasetImages()
    }

    // A resize changes the visible canvas bounds. Re-clamp any zoomed/panned
    // image so it remains reachable after the window becomes smaller.
    onWidthChanged: clampCanvasPan()
    onHeightChanged: clampCanvasPan()

    // Coordinates are stored in the displayed image's local coordinate space.
    // Re-project them when that image area changes size so annotations remain
    // at the same relative point in the image after a window resize.
    Connections {
        target: annotationLayer

        function onWidthChanged() {
            form.rescaleAnnotationsToImage()
        }

        function onHeightChanged() {
            form.rescaleAnnotationsToImage()
        }
    }

    Connections {
        target: boxClassComboBox.popup

        function onClosed() {
            boxClassComboBox.visible = false
        }
    }

    Component.onCompleted: {
        forceActiveFocus()
        applyToolSelection()
        syncPropertiesPanel(selectedObjectIndex())
        refreshDatasetImages()
        updateImageLabels()
        setZoom(zoomPercent)
    }

    onImageSourcesChanged: {
        if (imageSources.length === 0)
            return
        totalImages = imageSources.length
        currentImageIndex = Math.min(currentImageIndex, totalImages)
        updateImageLabels()
    }

    // ------------------------------------------------------------
    // Tools (Select / Move / Box / Polygon)
    // ------------------------------------------------------------
    onToolSelected: (tool) => {
        currentTool = tool
        applyToolSelection()
        boxClassComboBox.visible = false
    }

    onBoxClassPickerRequested: {
        currentTool = "box"
        applyToolSelection()
        boxClassComboBox.currentIndex = currentClassIndex
        boxClassComboBox.visible = true
        boxClassComboBox.forceActiveFocus()
        boxClassComboBox.popup.open()
    }

    onBoxClassSelected: (index) => {
        if (index < 0 || index >= staticClasses.length)
            return
        currentClassIndex = index
        boxClassComboBox.currentIndex = index
        boxClassComboBox.popup.close()
        boxClassComboBox.visible = false
    }

    onTopMenuClicked: (index, label) => {
        const updatedItems = []
        for (let i = 0; i < topBar.menuItems.length; ++i) {
            updatedItems.push({
                label: topBar.menuItems[i].label,
                active: i === index
            })
        }
        topBar.menuItems = updatedItems
        if (label === qsTr("Export")) {
            exportUltralyticsYoloDetection()
            return
        }
        topBar.statusText = label + " selected"
    }

    function buildExportPayload() {
        saveAnnotationsForImage(currentImageIndex)
        const images = []
        for (let index = 1; index <= imageSources.length; ++index) {
            const state = annotationsForImage(index)
            const annotations = []
            for (let objectIndex = 0; objectIndex < state.objects.length;
                 ++objectIndex) {
                const item = state.objects[objectIndex]
                annotations.push({
                    classId: item.classId,
                    shape: item.shape,
                    boxX: item.boxX,
                    boxY: item.boxY,
                    boxW: item.boxW,
                    boxH: item.boxH
                })
            }
            images.push({
                source: String(imageSources[index - 1]),
                name: imageFileName(imageSources[index - 1]),
                canvasWidth: state.canvasWidth || annotationLayer.width,
                canvasHeight: state.canvasHeight || annotationLayer.height,
                annotations: annotations
            })
        }
        const classes = []
        for (let classIndex = 0; classIndex < staticClasses.length; ++classIndex) {
            classes.push({
                classId: staticClasses[classIndex].classId,
                label: staticClasses[classIndex].label
            })
        }
        return { classes: classes, images: images }
    }

    function exportUltralyticsYoloDetection() {
        if (!exportBackend) {
            topBar.statusText = qsTr("Export requires python Python/main.py")
            return
        }
        topBar.statusText = qsTr("Preparing Ultralytics YOLO Detection 1.0...")
        const result = exportBackend.exportUltralyticsYoloDetection(
                    buildExportPayload())
        if (result.cancelled) {
            topBar.statusText = qsTr("Export cancelled")
        } else if (!result.ok) {
            topBar.statusText = qsTr("Export failed: ") + result.error
        } else {
            topBar.statusText = qsTr("Exported %1 images and %2 boxes")
                    .arg(result.images).arg(result.boxes)
            if (result.skipped > 0)
                topBar.statusText += qsTr(" (%1 non-box annotations skipped)")
                        .arg(result.skipped)
        }
    }

    function discardPolygonDraft() {
        drawingArea.polygonPoints = []
        drawingArea.polygonPreviewPoints = []
    }

    function discardBoxDraft() {
        drawingArea.drawing = false
        drawingArea.secondBoxPoint = false
        drawingArea.draggedSincePress = false
    }

    // ------------------------------------------------------------
    // Undo / redo history
    // ------------------------------------------------------------
    function copyPoints(points) {
        if (!points)
            return []
        const copiedPoints = []
        if (typeof points.count === "number") {
            for (let i = 0; i < points.count; ++i) {
                const point = points.get(i)
                copiedPoints.push(Qt.point(point.x, point.y))
            }
        } else {
            for (let i = 0; i < points.length; ++i) {
                const point = points[i]
                copiedPoints.push(Qt.point(point.x, point.y))
            }
        }
        return copiedPoints
    }

    function rescaleAnnotationsToImage() {
        const newWidth = annotationLayer.width
        const newHeight = annotationLayer.height
        if (newWidth <= 0 || newHeight <= 0)
            return

        if (previousAnnotationLayerWidth <= 0
                || previousAnnotationLayerHeight <= 0) {
            previousAnnotationLayerWidth = newWidth
            previousAnnotationLayerHeight = newHeight
            return
        }

        const scaleX = newWidth / previousAnnotationLayerWidth
        const scaleY = newHeight / previousAnnotationLayerHeight
        if (scaleX === 1 && scaleY === 1)
            return

        for (let i = 0; i < objectsModel.count; ++i) {
            const item = objectsModel.get(i)
            objectsModel.setProperty(i, "boxX", item.boxX * scaleX)
            objectsModel.setProperty(i, "boxY", item.boxY * scaleY)
            objectsModel.setProperty(i, "boxW", item.boxW * scaleX)
            objectsModel.setProperty(i, "boxH", item.boxH * scaleY)

            if (item.shape === "polygon") {
                const scaledPoints = copyPoints(item.points).map((point) =>
                    Qt.point(point.x * scaleX, point.y * scaleY))
                objectsModel.setProperty(i, "points", scaledPoints)
            }
        }

        polygonPaths = polygonPaths.map((path) => ({
            annotationId: path.annotationId,
            label: path.label,
            colorHex: path.colorHex,
            points: copyPoints(path.points).map((point) =>
                Qt.point(point.x * scaleX, point.y * scaleY)),
            boxX: path.boxX * scaleX,
            boxY: path.boxY * scaleY
        }))

        previousAnnotationLayerWidth = newWidth
        previousAnnotationLayerHeight = newHeight
        syncPropertiesPanel(selectedObjectIndex())
    }

    function captureAnnotationState() {
        const objects = []
        for (let i = 0; i < objectsModel.count; ++i) {
            const item = objectsModel.get(i)
            objects.push({
                annotationId: item.annotationId,
                classId: item.classId,
                label: item.label,
                shape: item.shape,
                points: copyPoints(item.points),
                colorHex: item.colorHex,
                selected: item.selected,
                locked: item.locked,
                boxX: item.boxX,
                boxY: item.boxY,
                boxW: item.boxW,
                boxH: item.boxH
            })
        }

        return {
            objects: objects,
            canvasWidth: annotationLayer.width,
            canvasHeight: annotationLayer.height,
            polygonPaths: polygonPaths.map((path) => ({
                annotationId: path.annotationId,
                label: path.label,
                colorHex: path.colorHex,
                points: copyPoints(path.points),
                boxX: path.boxX,
                boxY: path.boxY
            }))
        }
    }

    function restoreAnnotationState(state) {
        restoringHistory = true
        objectsModel.clear()
        for (let i = 0; i < state.objects.length; ++i)
            objectsModel.append(state.objects[i])
        polygonPaths = state.polygonPaths
        objectsCountText.text = String(objectsModel.count)
        syncPropertiesPanel(selectedObjectIndex())
        restoringHistory = false
    }

    function saveAnnotationsForImage(index) {
        const savedStates = {}
        for (const key in annotationsByImage)
            savedStates[key] = annotationsByImage[key]
        savedStates[String(index)] = captureAnnotationState()
        annotationsByImage = savedStates
    }

    function annotationsForImage(index) {
        const savedState = annotationsByImage[String(index)]
        return savedState || {
            objects: [],
            polygonPaths: []
        }
    }

    function showImage(index) {
        const nextIndex = Math.max(1, Math.min(totalImages, index))
        if (nextIndex === currentImageIndex)
            return

        saveAnnotationsForImage(currentImageIndex)
        currentImageIndex = nextIndex
        // History belongs to the image that was just left. It must not undo
        // edits from another image after navigation.
        undoStack = []
        redoStack = []
        restoreAnnotationState(annotationsForImage(currentImageIndex))
        updateImageLabels()
    }

    function recordHistory() {
        if (restoringHistory)
            return
        undoStack = undoStack.concat([captureAnnotationState()])
        redoStack = []
    }

    function undo() {
        if (undoStack.length === 0)
            return
        const previousState = undoStack[undoStack.length - 1]
        undoStack = undoStack.slice(0, -1)
        redoStack = redoStack.concat([captureAnnotationState()])
        restoreAnnotationState(previousState)
    }

    function redo() {
        if (redoStack.length === 0)
            return
        const nextState = redoStack[redoStack.length - 1]
        redoStack = redoStack.slice(0, -1)
        undoStack = undoStack.concat([captureAnnotationState()])
        restoreAnnotationState(nextState)
    }

    onGridToggleRequested: gridVisible = !gridVisible

    Connections {
        target: gridToggleArea

        function onClicked() {
            form.gridToggleRequested()
        }
    }

    Connections {
        target: canvasWheelHandler

        function onWheel(wheel) {
            if (wheel.angleDelta.y > 0 || wheel.pixelDelta.y > 0)
                form.zoomInRequested()
            else if (wheel.angleDelta.y < 0 || wheel.pixelDelta.y < 0)
                form.zoomOutRequested()
            wheel.accepted = true
        }
    }

    Connections {
        target: imageProgressSlider

        function onMoved() {
            form.imageIndexRequested(Math.round(imageProgressSlider.value))
        }
    }

    function applyToolSelection() {
        if (currentTool !== "polygon")
            discardPolygonDraft()
        if (currentTool !== "box")
            discardBoxDraft()
        selectTool.selected = currentTool === "select"
        moveTool.selected = currentTool === "move"
        bBox.selected = currentTool === "box"
        polygonTool.selected = currentTool === "polygon"
        handTool.selected = currentTool === "hand"
        activeTool = currentTool
    }

    // ------------------------------------------------------------
    // Canvas pan (Hand tool, Space, or middle-mouse drag)
    // ------------------------------------------------------------
    onCanvasPanStarted: (x, y) => {
        if (zoomPercent <= 100)
            return
        canvasPanning = true
        lastPanX = x
        lastPanY = y
    }

    onCanvasPanMoved: (x, y) => {
        if (!canvasPanning)
            return
        // Coordinates arrive in imageCanvas space, which does not move with the
        // zoomed image. This prevents pan movement feeding back into its own
        // next mouse delta.
        canvasPanX += x - lastPanX
        canvasPanY += y - lastPanY
        lastPanX = x
        lastPanY = y
        clampCanvasPan()
    }

    onCanvasPanFinished: canvasPanning = false

    function clampCanvasPan() {
        const maxPanX = Math.max(0, (canvasImage.paintedWidth * canvasImage.scale
                                     - imageCanvas.width) / 2)
        const maxPanY = Math.max(0, (canvasImage.paintedHeight * canvasImage.scale
                                     - imageCanvas.height) / 2)
        canvasPanX = Math.max(-maxPanX, Math.min(canvasPanX, maxPanX))
        canvasPanY = Math.max(-maxPanY, Math.min(canvasPanY, maxPanY))
    }

    // ------------------------------------------------------------
    // Objects list <-> Properties panel
    // ------------------------------------------------------------
    onObjectSelected: (index) => selectObject(index)

    // Move annotations while preserving their dimensions and keeping every line
    // within the painted image bounds. The image itself is never transformed.
    onAnnotationMoveRequested: (index, deltaX, deltaY) => {
        if (index < 0 || index >= objectsModel.count)
            return

        const item = objectsModel.get(index)
        if (item.locked)
            return
        recordHistory()
        const maxX = canvasImage.paintedWidth
        const maxY = canvasImage.paintedHeight
        const newX = Math.max(0, Math.min(item.boxX + deltaX,
                                          Math.max(0, maxX - item.boxW)))
        const newY = Math.max(0, Math.min(item.boxY + deltaY,
                                          Math.max(0, maxY - item.boxH)))
        const roundedX = Math.round(newX)
        const roundedY = Math.round(newY)
        const appliedX = roundedX - item.boxX
        const appliedY = roundedY - item.boxY

        objectsModel.setProperty(index, "boxX", roundedX)
        objectsModel.setProperty(index, "boxY", roundedY)

        if (item.shape === "polygon") {
            polygonPaths = polygonPaths.map((path) => {
                if (path.annotationId !== item.annotationId)
                    return path
                return {
                    annotationId: path.annotationId,
                    label: path.label,
                    colorHex: path.colorHex,
                    points: path.points.map((point) => Qt.point(
                                Math.max(0, Math.min(point.x + appliedX, maxX)),
                                Math.max(0, Math.min(point.y + appliedY, maxY)))),
                    boxX: roundedX,
                    boxY: roundedY
                }
            })
        }

        syncPropertiesPanel(index)
    }

    function selectObject(index) {
        for (let i = 0; i < objectsModel.count; i++)
            objectsModel.setProperty(i, "selected", i === index)
        syncPropertiesPanel(index)
    }

    function selectedObjectIndex() {
        for (let i = 0; i < objectsModel.count; i++) {
            if (objectsModel.get(i).selected)
                return i
        }
        return -1
    }

    function syncPropertiesPanel(index) {
        if (index < 0 || index >= objectsModel.count)
            return
        const item = objectsModel.get(index)
        labelChipText.text = item.label
        labelChipSwatch.color = item.colorHex
        xValueText.text = String(item.boxX)
        yValueText.text = String(item.boxY)
        widthValueText.text = String(item.boxW)
        heightValueText.text = String(item.boxH)
    }

    function currentStaticClass() {
        return staticClasses[currentClassIndex]
    }

    function createAnnotationId() {
        nextAnnotationId += 1
        return nextAnnotationId
    }

    onAddObjectRequested: {
        recordHistory()
        const index = objectsModel.count
        const annotationClass = currentStaticClass()
        objectsModel.append({
            annotationId: createAnnotationId(),
            classId: annotationClass.classId,
            label: annotationClass.label,
            shape: "box",
            colorHex: annotationClass.colorHex,
            selected: true,
            locked: false,
            boxX: 120,
            boxY: 120,
            boxW: 120,
            boxH: 120
        })
        selectObject(index)
        objectsCountText.text = String(objectsModel.count)
    }

    // Keyboard shortcuts are defined in the logic layer so AnnotationForm.ui.qml
    // remains compatible with Qt Design Studio's declarative-only restrictions.
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space) {
            if (!event.isAutoRepeat && !panShortcutActive) {
                if (currentTool === "polygon")
                    discardPolygonDraft()
                toolBeforePan = currentTool
                panShortcutActive = true
                activeTool = "hand"
            }
            event.accepted = true
            return
        }

        if (event.modifiers & Qt.ControlModifier) {
            if (event.key === Qt.Key_Z) {
                undo()
                event.accepted = true
                return
            }
            if (event.key === Qt.Key_Y) {
                redo()
                event.accepted = true
                return
            }
        }

        if (event.isAutoRepeat)
            return

        if (event.key === Qt.Key_S) {
            currentTool = "select"
            applyToolSelection()
            event.accepted = true
        } else if (event.key === Qt.Key_V) {
            currentTool = "move"
            applyToolSelection()
            event.accepted = true
        } else if (event.key === Qt.Key_B) {
            currentTool = "box"
            applyToolSelection()
            event.accepted = true
        } else if (event.key === Qt.Key_H) {
            currentTool = "hand"
            applyToolSelection()
            event.accepted = true
        } else if (event.key === Qt.Key_F) {
            nextImageRequested()
            event.accepted = true
        } else if (event.key === Qt.Key_D) {
            prevImageRequested()
            event.accepted = true
        } else if (event.key === Qt.Key_Delete) {
            deleteRequested()
            event.accepted = true
        }
    }

    Keys.onReleased: function(event) {
        if (event.key === Qt.Key_Space && panShortcutActive) {
            panShortcutActive = false
            currentTool = toolBeforePan
            applyToolSelection()
            event.accepted = true
        }
    }

    // A Box-tool drag on the image canvas creates both a model row and its
    // matching visual rectangle. Negative drag directions are normalized here.
    onBoxDrawn: (x, y, width, height) => {
        recordHistory()
        const boxX = width < 0 ? x + width : x
        const boxY = height < 0 ? y + height : y
        const boxW = Math.abs(width)
        const boxH = Math.abs(height)
        const index = objectsModel.count
        const annotationClass = currentStaticClass()

        objectsModel.append({
            annotationId: createAnnotationId(),
            classId: annotationClass.classId,
            label: annotationClass.label,
            shape: "box",
            colorHex: annotationClass.colorHex,
            selected: true,
            locked: false,
            boxX: Math.round(boxX),
            boxY: Math.round(boxY),
            boxW: Math.round(boxW),
            boxH: Math.round(boxH)
        })
        selectObject(index)
        objectsCountText.text = String(objectsModel.count)
    }

    // Polygon vertices are supplied by the UI after the user right-clicks to
    // finish the shape. Store a closed path and its bounds in the shared model.
    onPolygonDrawn: (points) => {
        if (points.length < 3)
            return

        recordHistory()

        let minX = points[0].x
        let minY = points[0].y
        let maxX = points[0].x
        let maxY = points[0].y
        for (let i = 1; i < points.length; ++i) {
            minX = Math.min(minX, points[i].x)
            minY = Math.min(minY, points[i].y)
            maxX = Math.max(maxX, points[i].x)
            maxY = Math.max(maxY, points[i].y)
        }

        const index = objectsModel.count
        const annotationClass = currentStaticClass()
        const annotationId = createAnnotationId()
        const label = annotationClass.label
        const colorHex = annotationClass.colorHex
        const closedPoints = points.concat([points[0]])
        const boxX = Math.round(minX)
        const boxY = Math.round(minY)
        const boxW = Math.round(maxX - minX)
        const boxH = Math.round(maxY - minY)
        objectsModel.append({
            annotationId: annotationId,
            classId: annotationClass.classId,
            label: label,
            shape: "polygon",
            points: closedPoints,
            colorHex: colorHex,
            selected: true,
            locked: false,
            boxX: boxX,
            boxY: boxY,
            boxW: boxW,
            boxH: boxH
        })
        polygonPaths = polygonPaths.concat([{
            annotationId: annotationId,
            label: label,
            colorHex: colorHex,
            points: closedPoints,
            boxX: boxX,
            boxY: boxY
        }])
        selectObject(index)
        objectsCountText.text = String(objectsModel.count)
    }

    onDuplicateRequested: {
        const idx = selectedObjectIndex()
        if (idx < 0)
            return
        recordHistory()
        const item = objectsModel.get(idx)
        objectsModel.setProperty(idx, "selected", false)
        const duplicateAnnotationId = createAnnotationId()
        objectsModel.insert(idx + 1, {
            annotationId: duplicateAnnotationId,
            classId: item.classId,
            label: item.label,
            shape: item.shape,
            points: copyPoints(item.points),
            colorHex: item.colorHex,
            selected: true,
            locked: item.locked,
            boxX: item.boxX + 12,
            boxY: item.boxY + 12,
            boxW: item.boxW,
            boxH: item.boxH
        })
        if (item.shape === "polygon") {
            const sourcePath = polygonPaths.find((path) =>
                path.annotationId === item.annotationId)
            if (sourcePath) {
                polygonPaths = polygonPaths.concat([{
                    annotationId: duplicateAnnotationId,
                    label: sourcePath.label,
                    colorHex: sourcePath.colorHex,
                    points: sourcePath.points.map((point) =>
                        Qt.point(point.x + 12, point.y + 12)),
                    boxX: sourcePath.boxX + 12,
                    boxY: sourcePath.boxY + 12
                }])
            }
        }
        objectsCountText.text = String(objectsModel.count)
        syncPropertiesPanel(idx + 1)
    }

    onDeleteRequested: {
        const idx = selectedObjectIndex()
        if (idx < 0)
            return
        recordHistory()
        const item = objectsModel.get(idx)
        if (item.shape === "polygon")
            polygonPaths = polygonPaths.filter((path) =>
                path.annotationId !== item.annotationId)
        objectsModel.remove(idx)
        objectsCountText.text = String(objectsModel.count)
        const nextIndex = Math.min(idx, objectsModel.count - 1)
        if (nextIndex >= 0) {
            objectsModel.setProperty(nextIndex, "selected", true)
            syncPropertiesPanel(nextIndex)
        }
    }

    onLockRequested: {
        const idx = selectedObjectIndex()
        if (idx < 0)
            return
        recordHistory()
        const item = objectsModel.get(idx)
        objectsModel.setProperty(idx, "locked", !item.locked)
    }

    // ------------------------------------------------------------
    // Canvas zoom
    // ------------------------------------------------------------
    onZoomInRequested: setZoom(zoomPercent + 25)
    onZoomOutRequested: setZoom(zoomPercent - 25)
    onFitRequested: setZoom(100)

    function setZoom(value) {
        zoomPercent = Math.max(25, Math.min(400, value))
        zoomPercentText.text = zoomPercent + "%"
        canvasImage.scale = zoomPercent / 100
        canvasPanX = zoomPercent <= 100 ? 0 : canvasPanX
        canvasPanY = zoomPercent <= 100 ? 0 : canvasPanY
        clampCanvasPan()
    }

    // ------------------------------------------------------------
    // Image navigation
    // ------------------------------------------------------------
    function refreshDatasetImages() {
        const sources = []
        for (let i = 0; i < datasetFolderModel.count; ++i)
            sources.push(datasetFolderModel.get(i, "fileUrl"))

        sources.sort((left, right) => {
            const leftKey = naturalImageSortKey(left)
            const rightKey = naturalImageSortKey(right)
            return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0
        })
        imageSources = sources
    }

    function naturalImageSortKey(source) {
        return imageFileName(source).toLowerCase().replace(/\d+/g, digits => {
            return ("000000000000" + digits).slice(-12)
        })
    }

    function imageFileName(source) {
        const sourceText = String(source)
        return decodeURIComponent(sourceText.substring(sourceText.lastIndexOf("/") + 1))
    }

    onPrevImageRequested: {
        showImage(currentImageIndex > 1 ? currentImageIndex - 1 : totalImages)
    }

    onNextImageRequested: {
        showImage(currentImageIndex < totalImages ? currentImageIndex + 1 : 1)
    }

    // Slider updates continuously while dragging, so users can scrub through
    // the dataset and see the current/next image labels change immediately.
    onImageIndexRequested: (index) => {
        showImage(index)
    }

    function updateImageLabels() {
        pageIndexInput.text = String(currentImageIndex)
        pageTotalText.text = String(totalImages)
        currentImageNameText.text = imageNameFor(currentImageIndex)
        const nextIndex = currentImageIndex < totalImages ? currentImageIndex + 1 : 1
        nextImageNameText.text = imageNameFor(nextIndex)
        imageProgressSlider.to = totalImages
        imageProgressSlider.value = currentImageIndex
        if (imageSources.length >= currentImageIndex)
            canvasImage.source = imageSources[currentImageIndex - 1]
        if (imageSources.length >= nextIndex)
            nextImageSource = imageSources[nextIndex - 1]
    }

    function imageNameFor(index) {
        if (imageSources.length < index)
            return ""
        return imageFileName(imageSources[index - 1])
    }
}

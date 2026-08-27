"""Ultralytics YOLO Detection 1.0 dataset export support."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

FORMAT_NAME = "Ultralytics YOLO Detection 1.0"


def _local_path(source: str) -> Path:
    parsed = urlparse(source)
    if parsed.scheme != "file":
        return Path(source)
    path = unquote(parsed.path)
    if parsed.netloc:
        path = f"//{parsed.netloc}{path}"
    elif len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    return Path(path)


def _unique_image_name(
    name: str, used_names: set[str], used_stems: set[str]
) -> str:
    candidate = name
    counter = 2
    while (
        candidate.lower() in used_names
        or Path(candidate).stem.lower() in used_stems
    ):
        path = Path(name)
        candidate = f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    used_names.add(candidate.lower())
    used_stems.add(Path(candidate).stem.lower())
    return candidate


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _label_lines(image: dict, class_indices: dict[str, int]) -> tuple[list[str], int]:
    canvas_width = float(image.get("canvasWidth") or 0)
    canvas_height = float(image.get("canvasHeight") or 0)
    if canvas_width <= 0 or canvas_height <= 0:
        return [], 0

    lines = []
    skipped = 0
    for annotation in image.get("annotations", []):
        if annotation.get("shape") != "box":
            skipped += 1
            continue
        class_id = str(annotation.get("classId", ""))
        if class_id not in class_indices:
            skipped += 1
            continue

        x = float(annotation.get("boxX") or 0)
        y = float(annotation.get("boxY") or 0)
        width = max(0.0, float(annotation.get("boxW") or 0))
        height = max(0.0, float(annotation.get("boxH") or 0))
        x1 = _clamp(x / canvas_width)
        y1 = _clamp(y / canvas_height)
        x2 = _clamp((x + width) / canvas_width)
        y2 = _clamp((y + height) / canvas_height)
        if x2 <= x1 or y2 <= y1:
            skipped += 1
            continue
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        lines.append(
            f"{class_indices[class_id]} {center_x:.6f} {center_y:.6f} "
            f"{x2 - x1:.6f} {y2 - y1:.6f}"
        )
    return lines, skipped


def export_dataset(archive_path: Path, payload: dict) -> dict:
    """Write a CVAT-compatible Ultralytics YOLO Detection archive."""
    classes = payload.get("classes", [])
    class_indices = {
        str(item.get("classId", "")): index for index, item in enumerate(classes)
    }
    images = payload.get("images", [])
    archive_path = archive_path.with_suffix(".zip")
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    skipped = 0
    exported_boxes = 0
    used_names: set[str] = set()
    used_stems: set[str] = set()
    train_entries = []

    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for image in images:
            source = _local_path(str(image.get("source", "")))
            if not source.is_file():
                raise FileNotFoundError(f"Dataset image was not found: {source}")
            image_name = _unique_image_name(
                str(image.get("name") or source.name), used_names, used_stems
            )
            image_archive_path = f"images/train/{image_name}"
            archive.write(source, image_archive_path)
            train_entries.append(image_archive_path)

            lines, image_skipped = _label_lines(image, class_indices)
            skipped += image_skipped
            exported_boxes += len(lines)
            if lines:
                label_path = f"labels/train/{Path(image_name).stem}.txt"
                archive.writestr(label_path, "\n".join(lines) + "\n")

        archive.writestr("train.txt", "\n".join(train_entries) + "\n")
        yaml_lines = ["path: ./", "train: train.txt", "names:"]
        for index, item in enumerate(classes):
            label = json.dumps(str(item.get("label", "")), ensure_ascii=False)
            yaml_lines.append(f"  {index}: {label}")
        archive.writestr("data.yaml", "\n".join(yaml_lines) + "\n")

    return {
        "ok": True,
        "path": str(archive_path),
        "images": len(images),
        "boxes": exported_boxes,
        "skipped": skipped,
    }

"""Pure marker-coordinate calculations with no UI or file access."""

from typing import TypeAlias


MarkerPosition: TypeAlias = tuple[int, int]
FrameSize: TypeAlias = tuple[int, int]
PreviewBounds: TypeAlias = tuple[float, float, float, float]


def marker_text(position: MarkerPosition | None) -> str:
    """Return a short label for a marker position."""
    if position is None:
        return "Click preview"
    x, y = position
    return f"x: {x}  y: {y}"


def preview_bounds(width: int, height: int, media_size: FrameSize) -> PreviewBounds:
    """Return the media rectangle inside a letterboxed preview area."""
    media_width, media_height = media_size
    scale = min(width / media_width, height / media_height)
    image_width = media_width * scale
    image_height = media_height * scale
    return (
        (width - image_width) / 2,
        (height - image_height) / 2,
        image_width,
        image_height,
    )


def canvas_to_camera(
    canvas_x: int,
    canvas_y: int,
    preview_size: FrameSize,
    media_size: FrameSize,
    camera_size: FrameSize,
) -> MarkerPosition | None:
    """Convert a preview click to camera coordinates, or reject letterbox clicks."""
    left, top, image_width, image_height = preview_bounds(*preview_size, media_size)
    if not (
        left <= canvas_x <= left + image_width
        and top <= canvas_y <= top + image_height
    ):
        return None

    camera_width, camera_height = camera_size
    x = min(
        camera_width - 1,
        max(0, round((canvas_x - left) * camera_width / image_width)),
    )
    y = min(
        camera_height - 1,
        max(0, round((canvas_y - top) * camera_height / image_height)),
    )
    return x, y

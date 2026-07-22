from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageChops, ImageOps

from app.models import ImageVariant


def _save(image: Image.Image, filename: str, fmt: str = "JPEG") -> bytes:
    buffer = BytesIO()
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    image.save(buffer, format=fmt, quality=95)
    return buffer.getvalue()


def _trim_black_borders(image: Image.Image) -> Image.Image | None:
    rgb = image.convert("RGB")
    bg = Image.new("RGB", rgb.size, (0, 0, 0))
    diff = ImageChops.difference(rgb, bg)
    bbox = diff.getbbox()
    if not bbox:
        return None

    left, top, right, bottom = bbox
    width, height = rgb.size
    trimmed = rgb.crop(bbox)

    if trimmed.size[0] < width * 0.85 or trimmed.size[1] < height * 0.85:
        return trimmed
    return None


def build_variants(
    image_bytes: bytes,
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
    enabled: bool = True,
) -> list[ImageVariant]:
    variants = [
        ImageVariant(
            name="original",
            filename=filename,
            content_type=content_type,
            data=image_bytes,
        )
    ]

    if not enabled:
        return variants

    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except Exception:
        return variants

    trimmed = _trim_black_borders(image)
    if trimmed is not None:
        variants.append(
            ImageVariant(
                name="trimmed",
                filename="trimmed.jpg",
                content_type="image/jpeg",
                data=_save(trimmed, "trimmed.jpg"),
            )
        )

    mirrored = ImageOps.mirror(image)
    variants.append(
        ImageVariant(
            name="mirrored",
            filename="mirrored.jpg",
            content_type="image/jpeg",
            data=_save(mirrored, "mirrored.jpg"),
        )
    )

    return variants

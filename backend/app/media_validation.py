"""Uploaded image validation shared by AI inspection and work-order evidence."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 24_000_000


def validate_image_bytes(data: bytes) -> tuple[int, int, str]:
    """Validate file signature, decoder integrity and decompressed dimensions."""
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image_format = (image.format or "").upper()
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("仅支持 JPEG、PNG、WEBP 图片")
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("图片尺寸无效或解压后像素数量超过限制")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("文件内容不是有效图片") from exc
    return width, height, image_format

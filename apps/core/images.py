"""Image validation and processing helpers built on Pillow."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

RASTER_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


def validate_image_upload(upload):
    """Validate type, size and dimensions of an uploaded image file.

    Raises ``ValidationError`` on failure; returns ``(width, height)`` on success
    (``(0, 0)`` for SVG, which Pillow does not open).
    """
    if upload is None:
        return 0, 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = getattr(upload, "size", None)
    if size is not None and size > max_bytes:
        raise ValidationError(f"Image is too large ({size / 1024 / 1024:.1f} MB). Maximum is {settings.MAX_UPLOAD_SIZE_MB} MB.")
    ext = Path(getattr(upload, "name", "")).suffix.lower().lstrip(".")
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported file type '.{ext}'. Allowed: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}.")
    if ext == "svg":
        head = upload.read(2048)
        upload.seek(0)
        if b"<svg" not in head.lower():
            raise ValidationError("The file is not a valid SVG image.")
        if b"<script" in head.lower():
            raise ValidationError("SVG files containing scripts are not allowed.")
        return 0, 0
    try:
        upload.seek(0)
        with Image.open(upload) as img:
            img.verify()
        upload.seek(0)
        with Image.open(upload) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("The uploaded file is not a valid image.") from exc
    finally:
        try:
            upload.seek(0)
        except Exception:  # pragma: no cover
            pass
    if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
        raise ValidationError(
            f"Image dimensions {width}x{height} exceed the maximum of {settings.MAX_IMAGE_DIMENSION}px per side."
        )
    if width < 16 or height < 16:
        raise ValidationError("Image is too small.")
    return width, height


def image_dimensions(field_file):
    """Return (width, height) of a stored image, without raising."""
    try:
        if not field_file or field_file.name.lower().endswith(".svg"):
            return 0, 0
        with field_file.storage.open(field_file.name, "rb") as fh:
            data = fh.read()
        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return 0, 0


def _open_for_processing(field_file):
    """Load a stored image fully into memory (so the file handle can be released on Windows),
    apply EXIF orientation and return (image, original_format)."""
    # Read through the storage directly: FieldFile caches an open File object whose path
    # goes stale after the file is renamed (WebP conversion).
    with field_file.storage.open(field_file.name, "rb") as fh:
        data = fh.read()
    img = Image.open(BytesIO(data))
    fmt = img.format or "JPEG"
    img.load()
    img = ImageOps.exif_transpose(img)
    return img, fmt


def optimise_image(field_file, max_edge=None):
    """Resize an over-sized raster image and convert it to WebP.

    Works in place on the storage. Returns the new storage name when the file was
    renamed (format changed), otherwise None. SVG and GIF files are left untouched.
    """
    if not field_file or not field_file.name or field_file.name.lower().endswith((".svg", ".gif")):
        return None
    max_edge = max_edge or settings.IMAGE_MAX_EDGE
    convert = settings.IMAGE_CONVERT_WEBP
    try:
        img, fmt = _open_for_processing(field_file)
    except Exception:
        return None
    try:
        needs_resize = max(img.size) > max_edge
        needs_convert = convert and fmt != "WEBP"
        if not needs_resize and not needs_convert:
            return None
        if needs_resize:
            img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        if needs_convert:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.mode or img.mode == "P" else "RGB")
            img.save(buffer, format="WEBP", quality=settings.IMAGE_WEBP_QUALITY, method=6)
        else:
            save_kwargs = {"optimize": True}
            if fmt == "JPEG" and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if fmt in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 85
            img.save(buffer, format=fmt, **save_kwargs)
    finally:
        img.close()
    storage = field_file.storage
    old_name = field_file.name
    if needs_convert:
        base = old_name.rsplit(".", 1)[0]
        new_name = storage.save(f"{base}.webp", ContentFile(buffer.getvalue()))
        storage.delete(old_name)
        field_file.name = new_name
        field_file._file = None
        return new_name
    storage.delete(old_name)
    storage.save(old_name, ContentFile(buffer.getvalue()))
    return None


def shrink_if_needed(field_file, max_edge=None):
    """Backwards-compatible alias: resize + WebP conversion. Returns True when the file changed."""
    return optimise_image(field_file, max_edge) is not None


def optimise_fields(instance, *fields):
    """Optimise the given image fields of a saved instance and persist any renamed files."""
    changed = {}
    for name in fields:
        image = getattr(instance, name, None)
        if image:
            new_name = optimise_image(image)
            if new_name:
                changed[name] = new_name
    if changed and instance.pk:
        type(instance)._default_manager.filter(pk=instance.pk).update(**changed)
    return changed


shrink_images = optimise_fields


def make_thumbnail(field_file, size=None, suffix="_thumb"):
    """Create a thumbnail file next to ``field_file``; returns the new storage name or ''."""
    if not field_file or field_file.name.lower().endswith(".svg"):
        return ""
    size = size or settings.THUMBNAIL_SIZE
    try:
        img, fmt = _open_for_processing(field_file)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        ext = RASTER_FORMATS.get(fmt, "jpg")
        if fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(buffer, format=fmt, quality=82, optimize=True)
        img.close()
        path = Path(field_file.name)
        name = f"{path.parent.as_posix()}/{path.stem}{suffix}.{ext}" if path.parent.as_posix() != "." else f"{path.stem}{suffix}.{ext}"
        storage = field_file.storage
        if storage.exists(name):
            storage.delete(name)
        return storage.save(name, ContentFile(buffer.getvalue()))
    except Exception:
        return ""

import asyncio
import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps

from src.config import settings
from src.exceptions import AppException, PayloadTooLarge, UnsupportedMediaType

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
UPLOAD_ROOT = settings.UPLOAD_DIR.resolve()

# Batas piksel supaya gambar "bom" (kecil di disk, raksasa di memori) ditolak
Image.MAX_IMAGE_PIXELS = 25_000_000


def image_url(path: str | None) -> str | None:
    """Path relatif di database -> URL lengkap untuk client."""
    if not path:
        return None
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{path}"


async def read_upload(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if size > settings.MAX_IMAGE_BYTES:
            limit_mb = settings.MAX_IMAGE_BYTES // (1024 * 1024)
            raise PayloadTooLarge(f"Image must be at most {limit_mb} MB", field="file")
        chunks.append(chunk)
    if not chunks:
        raise UnsupportedMediaType("File is empty", field="file")
    return b"".join(chunks)


def _process(data: bytes) -> bytes:
    """Validasi isi file, perkecil, buang metadata, simpan ulang sebagai WebP."""
    invalid = UnsupportedMediaType(
        "File must be a valid JPEG, PNG, or WebP image", field="file"
    )
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()

        with Image.open(io.BytesIO(data)) as img:
            if img.format not in ALLOWED_FORMATS:
                raise invalid

            img = ImageOps.exif_transpose(img)  # luruskan orientasi dari EXIF
            img.thumbnail((settings.IMAGE_MAX_DIMENSION, settings.IMAGE_MAX_DIMENSION))

            has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
            img = img.convert("RGBA" if has_alpha else "RGB")

            out = io.BytesIO()
            img.save(
                out, format="WEBP", quality=85
            )  # metadata EXIF tidak ikut tersimpan
            return out.getvalue()
    except AppException:
        raise
    except Exception:
        raise invalid


async def save_image(data: bytes, folder: str = "products") -> str:
    """Return path relatif, misalnya 'products/ab12cd.webp'."""
    processed = await asyncio.to_thread(_process, data)  # Pillow itu blocking
    relative = f"{folder}/{uuid.uuid4().hex}.webp"
    target = UPLOAD_ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_bytes, processed)
    return relative


def delete_image(relative: str | None) -> None:
    if not relative:
        return
    target = (UPLOAD_ROOT / relative).resolve()
    if target.is_relative_to(
        UPLOAD_ROOT
    ):  # jangan pernah menghapus di luar folder uploads
        target.unlink(missing_ok=True)

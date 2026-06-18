from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable, Literal

import fitz
from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PDF_EXTENSIONS = {".pdf"}
PDFMode = Literal["optimize", "rasterize"]
ProgressCallback = Callable[[int, int, Path], None]


@dataclass(frozen=True)
class ProcessingError:
    source: str
    message: str


@dataclass
class BatchResult:
    processed: int = 0
    skipped: int = 0
    outputs: list[str] = field(default_factory=list)
    errors: list[ProcessingError] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        return len(self.errors)


def parse_drop_data(event_data: str) -> list[str]:
    """Parse tkinterdnd2 file lists while preserving spaces inside paths."""
    files: list[str] = []
    current = []
    in_braces = False

    for char in event_data:
        if char == "{":
            in_braces = True
            continue
        if char == "}":
            in_braces = False
            if current:
                files.append("".join(current))
                current = []
            continue
        if char == " " and not in_braces:
            if current:
                files.append("".join(current))
                current = []
            continue
        current.append(char)

    if current:
        files.append("".join(current))

    return files


def collect_image_paths(paths: Iterable[str | Path]) -> list[str]:
    return _collect_paths(paths, IMAGE_EXTENSIONS, recursive_dirs=True)


def collect_pdf_paths(paths: Iterable[str | Path]) -> list[str]:
    return _collect_paths(paths, PDF_EXTENSIONS, recursive_dirs=False)


def compress_images(
    source_paths: Iterable[str | Path],
    output_dir: str | Path,
    *,
    quality: int,
    convert_to: str | None = None,
    input_filter: str = "all",
    progress_callback: ProgressCallback | None = None,
) -> BatchResult:
    sources = [Path(path) for path in source_paths]
    output = _ensure_directory(output_dir)
    result = BatchResult()
    reserved: set[Path] = set()
    total = len(sources)

    for index, source in enumerate(sources, start=1):
        try:
            if not _matches_input_filter(source, input_filter):
                result.skipped += 1
                continue
            output_path = _compress_image_file(
                source,
                output,
                quality=_clamp(quality, 1, 100),
                convert_to=convert_to,
                reserved=reserved,
            )
            result.outputs.append(str(output_path))
            result.processed += 1
        except Exception as exc:  # pragma: no cover - exact library errors vary
            result.errors.append(ProcessingError(str(source), str(exc)))
        finally:
            if progress_callback:
                progress_callback(index, total, source)

    return result


def compress_pdfs(
    source_paths: Iterable[str | Path],
    output_dir: str | Path,
    *,
    mode: PDFMode,
    dpi: int = 100,
    progress_callback: ProgressCallback | None = None,
) -> BatchResult:
    sources = [Path(path) for path in source_paths]
    output = _ensure_directory(output_dir)
    result = BatchResult()
    reserved: set[Path] = set()
    total = len(sources)

    for index, source in enumerate(sources, start=1):
        try:
            output_path = _compress_pdf_file(
                source,
                output,
                mode=mode,
                dpi=_clamp(dpi, 30, 300),
                reserved=reserved,
            )
            result.outputs.append(str(output_path))
            result.processed += 1
        except Exception as exc:  # pragma: no cover - exact library errors vary
            result.errors.append(ProcessingError(str(source), str(exc)))
        finally:
            if progress_callback:
                progress_callback(index, total, source)

    return result


def _collect_paths(
    paths: Iterable[str | Path],
    extensions: set[str],
    *,
    recursive_dirs: bool,
) -> list[str]:
    collected: list[str] = []
    seen: set[Path] = set()

    for raw_path in paths:
        path = Path(raw_path).expanduser()
        candidates: Iterable[Path]
        if path.is_dir() and recursive_dirs:
            candidates = sorted(item for item in path.rglob("*") if item.is_file())
        elif path.is_file():
            candidates = [path]
        else:
            continue

        for candidate in candidates:
            if candidate.suffix.lower() not in extensions:
                continue
            key = _resolved_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            collected.append(str(candidate))

    return collected


def _compress_image_file(
    source: Path,
    output_dir: Path,
    *,
    quality: int,
    convert_to: str | None,
    reserved: set[Path],
) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"File not found: {source}")
    if source.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {source.suffix}")

    extension = _normalise_image_extension(convert_to) if convert_to else _normalise_image_extension(source.suffix)
    output_path = _unique_output_path(output_dir, f"{source.stem}_compressed", extension, reserved)
    image_format = _pil_format_for_extension(extension)

    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.load()
        save_kwargs = _image_save_kwargs(image_format, quality)
        if image_format == "JPEG":
            image = _prepare_for_jpeg(image)
        elif image_format == "WEBP" and image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if _has_alpha(image) else "RGB")
        image.save(output_path, format=image_format, **save_kwargs)

    return output_path


def _compress_pdf_file(
    source: Path,
    output_dir: Path,
    *,
    mode: PDFMode,
    dpi: int,
    reserved: set[Path],
) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"File not found: {source}")
    if source.suffix.lower() not in PDF_EXTENSIONS:
        raise ValueError(f"Unsupported PDF format: {source.suffix}")

    output_path = _unique_output_path(output_dir, f"{source.stem}_compressed", ".pdf", reserved)
    if mode == "optimize":
        _optimize_pdf(source, output_path)
    elif mode == "rasterize":
        _rasterize_pdf(source, output_path, dpi=dpi)
    else:
        raise ValueError(f"Unknown PDF mode: {mode}")
    return output_path


def _optimize_pdf(source: Path, output_path: Path) -> None:
    document = fitz.open(source)
    try:
        if document.needs_pass:
            raise ValueError("Encrypted PDFs are not supported.")
        if document.page_count == 0:
            raise ValueError("PDF has no pages.")
        document.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        document.close()


def _rasterize_pdf(source: Path, output_path: Path, *, dpi: int) -> None:
    source_doc = fitz.open(source)
    output_doc = fitz.open()
    try:
        if source_doc.needs_pass:
            raise ValueError("Encrypted PDFs are not supported.")
        if source_doc.page_count == 0:
            raise ValueError("PDF has no pages.")

        jpeg_quality = 60 if dpi < 72 else 75 if dpi < 120 else 85
        for page in source_doc:
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            stream = _pixmap_to_jpeg_bytes(pixmap, jpeg_quality=jpeg_quality)
            output_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            output_page.insert_image(output_page.rect, stream=stream)

        output_doc.save(output_path, garbage=4, deflate=True)
    finally:
        output_doc.close()
        source_doc.close()


def _pixmap_to_jpeg_bytes(pixmap: fitz.Pixmap, *, jpeg_quality: int) -> bytes:
    mode = "RGB" if pixmap.n < 4 else "RGBA"
    image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    return buffer.getvalue()


def _ensure_directory(path: str | Path) -> Path:
    directory = Path(path).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _unique_output_path(output_dir: Path, stem: str, extension: str, reserved: set[Path]) -> Path:
    extension = extension if extension.startswith(".") else f".{extension}"
    candidate = output_dir / f"{stem}{extension}"
    index = 2

    while candidate.exists() or candidate in reserved:
        candidate = output_dir / f"{stem}_{index}{extension}"
        index += 1

    reserved.add(candidate)
    return candidate


def _normalise_image_extension(value: str) -> str:
    suffix = value.lower().strip()
    if not suffix:
        raise ValueError("Missing image format.")
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    if suffix == ".jpeg":
        suffix = ".jpg"
    if suffix not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {value}")
    return suffix


def _pil_format_for_extension(extension: str) -> str:
    return {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }[extension]


def _image_save_kwargs(image_format: str, quality: int) -> dict[str, int | bool]:
    if image_format == "JPEG":
        return {"quality": quality, "optimize": True, "progressive": True}
    if image_format == "WEBP":
        return {"quality": quality, "method": 6}
    if image_format == "PNG":
        compression = round((100 - quality) / 100 * 9)
        return {"optimize": True, "compress_level": _clamp(compression, 0, 9)}
    return {}


def _prepare_for_jpeg(image: Image.Image) -> Image.Image:
    if _has_alpha(image):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)


def _matches_input_filter(source: Path, input_filter: str) -> bool:
    selected = input_filter.lower().strip()
    if selected == "all":
        return True
    if selected == "jpg":
        return source.suffix.lower() in {".jpg", ".jpeg"}
    return source.suffix.lower() == _normalise_image_extension(selected)


def _clamp(value: int | float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def _resolved_key(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()

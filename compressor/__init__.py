"""Core compression helpers for VB Compress."""

from .core import (
    BatchResult,
    ProcessingError,
    collect_image_paths,
    collect_pdf_paths,
    compress_images,
    compress_pdfs,
    parse_drop_data,
)

__all__ = [
    "BatchResult",
    "ProcessingError",
    "collect_image_paths",
    "collect_pdf_paths",
    "compress_images",
    "compress_pdfs",
    "parse_drop_data",
]

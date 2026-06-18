import tempfile
import unittest
from pathlib import Path

import fitz
from PIL import Image

from compressor.core import (
    collect_image_paths,
    compress_images,
    compress_pdfs,
    parse_drop_data,
)


class CoreTests(unittest.TestCase):
    def test_parse_drop_data_preserves_paths_with_spaces(self):
        data = "{/tmp/one file.jpg} /tmp/two.png {/tmp/three file.webp}"

        self.assertEqual(
            parse_drop_data(data),
            ["/tmp/one file.jpg", "/tmp/two.png", "/tmp/three file.webp"],
        )

    def test_collect_image_paths_recurses_and_filters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()
            (root / "skip.txt").write_text("no")
            Image.new("RGB", (4, 4), "red").save(root / "a.jpg")
            Image.new("RGB", (4, 4), "blue").save(nested / "b.png")

            collected = {Path(path).name for path in collect_image_paths([root])}

        self.assertEqual(collected, {"a.jpg", "b.png"})

    def test_compress_images_uses_unique_output_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_dir = root / "first"
            second_dir = root / "second"
            output_dir = root / "out"
            first_dir.mkdir()
            second_dir.mkdir()
            Image.new("RGB", (8, 8), "red").save(first_dir / "photo.jpg")
            Image.new("RGB", (8, 8), "blue").save(second_dir / "photo.jpg")

            result = compress_images(
                [first_dir / "photo.jpg", second_dir / "photo.jpg"],
                output_dir,
                quality=80,
            )

            outputs = [Path(path).name for path in result.outputs]

        self.assertEqual(result.processed, 2)
        self.assertEqual(outputs, ["photo_compressed.jpg", "photo_compressed_2.jpg"])
        self.assertEqual(result.total_errors, 0)

    def test_convert_transparent_png_to_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "transparent.png"
            output_dir = root / "out"
            Image.new("RGBA", (8, 8), (255, 0, 0, 120)).save(source)

            result = compress_images([source], output_dir, quality=80, convert_to="jpg")
            with Image.open(result.outputs[0]) as converted:
                converted_mode = converted.mode

        self.assertEqual(result.processed, 1)
        self.assertEqual(converted_mode, "RGB")
        self.assertEqual(Path(result.outputs[0]).suffix, ".jpg")
        self.assertEqual(result.total_errors, 0)

    def test_optimize_pdf_keeps_text_layer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output_dir = root / "out"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Selectable text")
            doc.save(source)
            doc.close()

            result = compress_pdfs([source], output_dir, mode="optimize")
            optimized = fitz.open(result.outputs[0])
            text = optimized[0].get_text()
            optimized.close()

        self.assertEqual(result.processed, 1)
        self.assertIn("Selectable text", text)
        self.assertEqual(result.total_errors, 0)

    def test_rasterize_pdf_creates_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output_dir = root / "out"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Raster text")
            doc.save(source)
            doc.close()

            result = compress_pdfs([source], output_dir, mode="rasterize", dpi=72)
            rasterized = fitz.open(result.outputs[0])
            page_count = rasterized.page_count
            rasterized.close()

        self.assertEqual(result.processed, 1)
        self.assertEqual(page_count, 1)
        self.assertEqual(result.total_errors, 0)


if __name__ == "__main__":
    unittest.main()

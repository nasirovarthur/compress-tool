import subprocess
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist" / "VB Compress Swift.app"
E2E_BINARY = ROOT / "build" / "swift" / "VBCompressE2E"


class SwiftAppE2ETests(unittest.TestCase):
    def run_command(self, command, timeout=60):
        return subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )

    def test_swift_engine_and_app_launch(self):
        self.run_command([".venv/bin/python", "build_swift.py"], timeout=120)

        self.run_command(
            [
                "swiftc",
                "-D",
                "E2E_TEST",
                "-O",
                "-parse-as-library",
                "-o",
                str(E2E_BINARY),
                str(ROOT / "SwiftUIApp" / "VBCompressSwift.swift"),
                str(ROOT / "SwiftUIApp" / "VBCompressE2E.swift"),
                "-framework",
                "SwiftUI",
                "-framework",
                "AppKit",
                "-framework",
                "UniformTypeIdentifiers",
                "-framework",
                "ImageIO",
                "-framework",
                "PDFKit",
            ],
            timeout=120,
        )

        result = self.run_command([str(E2E_BINARY)], timeout=30)
        self.assertIn("swift e2e ok", result.stdout)

        self.assertTrue(APP.exists(), "SwiftUI app bundle should exist")
        self.run_command(["open", "-n", str(APP)], timeout=10)
        time.sleep(2)
        process = subprocess.run(
            ["pgrep", "-fl", "VBCompressSwift"],
            text=True,
            capture_output=True,
        )
        try:
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("VBCompressSwift", process.stdout)
        finally:
            subprocess.run(["pkill", "-f", "VB Compress Swift.app/Contents/MacOS/VBCompressSwift"])


if __name__ == "__main__":
    unittest.main()

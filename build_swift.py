import fcntl
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "SwiftUIApp" / "VBCompressSwift.swift"
BUILD_DIR = ROOT / "build" / "swift"
DIST_DIR = ROOT / "dist"
APP_NAME = "VB Compress Swift"
APP_DIR = DIST_DIR / f"{APP_NAME}.app"
EXECUTABLE = "VBCompressSwift"
BUNDLE_ID = "com.vbcompress.swift"
LOCK_FILE = BUILD_DIR / ".build_swift.lock"


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    build_token = str(os.getpid())
    binary = BUILD_DIR / f"{EXECUTABLE}-{build_token}"
    tmp_app_dir = DIST_DIR / f".{APP_NAME}.app.tmp-{build_token}"

    if tmp_app_dir.exists():
        shutil.rmtree(tmp_app_dir, ignore_errors=True)

    run(
        [
            "swiftc",
            "-O",
            "-parse-as-library",
            "-o",
            str(binary),
            str(SOURCE),
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
        ]
    )

    macos_dir = tmp_app_dir / "Contents" / "MacOS"
    resources_dir = tmp_app_dir / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    shutil.copy2(binary, macos_dir / EXECUTABLE)
    os.chmod(macos_dir / EXECUTABLE, 0o755)

    icon_source = ROOT / "icon.icns"
    icon_name = None
    if icon_source.exists():
        icon_name = "AppIcon.icns"
        shutil.copy2(icon_source, resources_dir / icon_name)

    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": EXECUTABLE,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "14.0",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    }
    if icon_name:
        info["CFBundleIconFile"] = icon_name

    with (tmp_app_dir / "Contents" / "Info.plist").open("wb") as file:
        plistlib.dump(info, file)

    with LOCK_FILE.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if APP_DIR.exists():
            shutil.rmtree(APP_DIR, ignore_errors=True)
        os.rename(tmp_app_dir, APP_DIR)

    binary.unlink(missing_ok=True)

    print(f"Built {APP_DIR}")


if __name__ == "__main__":
    main()

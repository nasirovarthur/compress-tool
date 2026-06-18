# VB Compress

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

VB Compress is a desktop tool for compressing images and PDF documents.

The repository currently contains two app shells:

- `main.py` - the original Python / CustomTkinter app.
- `SwiftUIApp/VBCompressSwift.swift` - the native macOS SwiftUI app.

## Features

- Drag and drop files into the app.
- Recursively import image folders.
- Compress `JPG`, `PNG`, and `WEBP` images.
- Convert images between `JPG`, `PNG`, and `WEBP`.
- Save duplicate filenames safely without overwriting previous output.
- Optimize PDFs while preserving text and vector content.
- Rasterize scanned PDFs with a DPI setting when smaller scan-style output is preferred.
- Run long compression jobs in the background with progress and error reporting.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/nasirovarthur/compress-tool.git
cd compress-tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Test

```bash
python -m unittest discover -s tests
```

## Build Python App

```bash
python build.py
```

## Build SwiftUI App

The SwiftUI app is macOS-only and can be built without an Xcode project:

```bash
python build_swift.py
```

Build outputs are written to `dist/`.

## Notes

- macOS builds use `icon.icns` when it exists.
- Windows builds use `icon.ico` when it exists.
- The SwiftUI app builds only for macOS.
- The app is unsigned, so macOS Gatekeeper or Windows SmartScreen may show a warning on first launch.

## License

MIT. See [LICENSE](LICENSE).

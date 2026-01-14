# VB Compress 🗜️

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

VB Compress — a modern application for optimizing images and PDF documents. Minimalist dark UI and powerful compression algorithms.

---

## ✨ Key Features

- **Drag & Drop:** drag and drop files and folders into the application window.
- **Images**
    - Supported formats: `JPG`, `PNG`, `WEBP`.
    - Smart compression while maintaining quality.
    - On-the-fly format conversion (e.g., `WEBP → JPG`).
- **PDF**
    - Compression of scans and documents.
    - DPI settings for controlling quality and size.
- **Interface**
    - Dark theme, implemented with `CustomTkinter`.

---

## 🛠 Installation (for developers)

Requires Python 3.11+.

1. Clone the repository:
```bash
git clone https://github.com/your-username/compress-tool.git
cd compress-tool
```

2. Create and activate a virtual environment

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run:
```bash
python main.py
```

---

## 📦 Building the Application

Ready-to-use build script:
```bash
python build.py
```
After building:
- macOS: `VB Compress.app` will appear in the `dist` folder.
- Windows: `VB Compress.exe` will appear in the `dist` folder.

---

## 🚨 Opening the Downloaded Application

Since the application is not signed with a developer certificate:

macOS
- Right-click the application → "Open" → confirm "Open".

Windows (SmartScreen)
- Click "More info" → "Run anyway".

---

## 🧩 Technologies Used

- CustomTkinter — UI
- TkinterDnD2 — Drag & Drop
- Pillow (PIL) — image processing
- PyMuPDF — PDF handling
- PyInstaller — building into .app / .exe

---

## 📄 License and Author

MIT License.

Made with ❤️ by Arthur.
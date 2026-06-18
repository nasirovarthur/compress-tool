import os
from pathlib import Path

import customtkinter
import PyInstaller.__main__

ctk_path = os.path.dirname(customtkinter.__file__)
data_separator = ";" if os.name == "nt" else ":"
icon_path = Path("icon.ico") if os.name == "nt" else Path("icon.icns")

args = [
    'main.py',
    '--name=VB Compress',
    '--noconsole',
    '--windowed',
    '--clean',
    '--noconfirm',
    '--collect-all=tkinterdnd2',
    f'--add-data={ctk_path}{data_separator}customtkinter',
    f'--add-data=Logo.png{data_separator}.',
]

if icon_path.exists():
    args.append(f'--icon={icon_path}')

PyInstaller.__main__.run(args)

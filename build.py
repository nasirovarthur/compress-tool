import PyInstaller.__main__
import customtkinter
import os

ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'main.py',
    '--name=VB Compress',
    '--noconsole',
    '--windowed',
    '--clean',
    '--icon=icon.icns',

    f'--add-data={ctk_path}:customtkinter',
    '--add-data=Logo.png:.',
])
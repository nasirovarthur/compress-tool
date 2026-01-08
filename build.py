import PyInstaller.__main__
import customtkinter
import os

ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'main.py',
    '--name=Compress',
    '--noconsole',
    '--windowed',
    '--clean',

    f'--add-data={ctk_path}:customtkinter',

    '--add-data=Logo.png:.',

])
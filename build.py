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
    '--icon=icon.icns', # Убедитесь, что этот файл есть в папке!

    # ГЛАВНОЕ: Собираем библиотеку Drag-and-Drop целиком
    '--collect-all=tkinterdnd2',

    # Добавляем ресурсы
    f'--add-data={ctk_path}:customtkinter',
    '--add-data=Logo.png:.',
])
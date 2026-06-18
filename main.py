import os
import sys
import threading
import tkinter as tk
import traceback
import warnings
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox

from compressor.core import (
    BatchResult,
    collect_image_paths,
    collect_pdf_paths,
    compress_images,
    compress_pdfs,
    parse_drop_data,
)

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        import tkinter.tix
except ImportError:
    tk.tix = tk
    sys.modules["tkinter.tix"] = tk

try:
    from tkinterdnd2 import DND_ALL, TkinterDnD
except ImportError:
    DND_ALL = "all"

    class TkinterDnD:
        class DnDWrapper:
            pass

        @staticmethod
        def _require(self):
            return None


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


COLOR_BG_APP = "#07090F"
COLOR_SIDEBAR = "#0B0E15"
COLOR_SIDEBAR_ACTIVE = "#182238"
COLOR_PANEL = "#111722"
COLOR_PANEL_ALT = "#161D2A"
COLOR_PANEL_DEEP = "#0C111A"
COLOR_INPUT = "#1A2230"
COLOR_BORDER = "#273245"
COLOR_BORDER_SOFT = "#1B2434"
COLOR_TEXT_MAIN = "#F5F7FB"
COLOR_TEXT_SEC = "#96A1B5"
COLOR_TEXT_MUTED = "#657086"
COLOR_ACCENT = "#B9FF5A"
COLOR_ACCENT_DARK = "#78BF35"
COLOR_BLUE = "#62D4FF"
COLOR_PURPLE = "#9B7CFF"
COLOR_ERROR = "#FF6868"
COLOR_WARNING = "#FFB85A"

FONT_HERO = ("Arial", 30, "bold")
FONT_HEADER = ("Arial", 22, "bold")
FONT_SUBHEADER = ("Arial", 17, "bold")
FONT_CARD_TITLE = ("Arial", 20, "bold")
FONT_BODY = ("Arial", 14)
FONT_BODY_BOLD = ("Arial", 14, "bold")
FONT_SMALL = ("Arial", 12)
FONT_SMALL_BOLD = ("Arial", 12, "bold")
FONT_BTN = ("Arial", 15, "bold")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class HeroPanel(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=COLOR_BG_APP,
            bd=0,
            highlightthickness=0,
            height=188,
            **kwargs,
        )
        self.mode = "Images"
        self.selected = 0
        self.profile = "Balanced"
        self.scan_x = 0
        self.after_id = None
        self.bind("<Configure>", lambda _event: self.redraw())
        self.animate()

    def set_state(self, mode, selected, profile):
        self.mode = mode
        self.selected = selected
        self.profile = profile
        self.redraw()

    def redraw(self):
        self.delete("all")
        width = max(self.winfo_width(), 720)
        height = max(self.winfo_height(), 188)

        self.create_rectangle(0, 0, width, height, fill=COLOR_PANEL_DEEP, outline=COLOR_BORDER_SOFT, width=1)
        self.create_rectangle(1, 1, width - 1, 46, fill="#121827", outline="")
        self.create_line(0, 46, width, 46, fill=COLOR_BORDER_SOFT)

        band_width = width // 3
        self.create_polygon(
            width - band_width,
            0,
            width,
            0,
            width,
            height,
            width - band_width - 120,
            height,
            fill="#18233A",
            outline="",
        )
        self.create_polygon(
            width - 260,
            28,
            width - 42,
            28,
            width - 88,
            height - 24,
            width - 334,
            height - 24,
            fill="#10182A",
            outline=COLOR_BORDER_SOFT,
        )
        self.create_line(self.scan_x, 0, self.scan_x + 92, height, fill=COLOR_ACCENT, width=2)

        self.create_text(28, 24, text="COMPRESSION HUB", anchor="w", fill=COLOR_ACCENT, font=FONT_SMALL_BOLD)
        self.create_text(28, 76, text="VB Compress", anchor="w", fill=COLOR_TEXT_MAIN, font=FONT_HERO)
        self.create_text(
            30,
            112,
            text="Launcher-style workspace for image and PDF optimization.",
            anchor="w",
            fill=COLOR_TEXT_SEC,
            font=FONT_BODY,
        )

        self.draw_stat(30, 144, "ACTIVE", self.mode, COLOR_BLUE)
        self.draw_stat(180, 144, "SELECTED", str(self.selected), COLOR_ACCENT)
        self.draw_stat(330, 144, "PROFILE", self.profile, COLOR_PURPLE)

        self.create_text(width - 204, 70, text="READY", anchor="center", fill=COLOR_TEXT_MAIN, font=("Arial", 34, "bold"))
        self.create_text(
            width - 204,
            110,
            text="Drop files, tune profile, launch job.",
            anchor="center",
            fill=COLOR_TEXT_SEC,
            font=FONT_SMALL,
            width=260,
        )

    def draw_stat(self, x, y, label, value, color):
        self.create_rectangle(x, y, x + 126, y + 30, fill="#151C2A", outline=COLOR_BORDER_SOFT)
        self.create_text(x + 12, y + 15, text=label, anchor="w", fill=COLOR_TEXT_MUTED, font=("Arial", 10, "bold"))
        self.create_text(x + 116, y + 15, text=value, anchor="e", fill=color, font=FONT_SMALL_BOLD)

    def animate(self):
        if not self.winfo_exists():
            return
        width = max(self.winfo_width(), 720)
        self.scan_x = (self.scan_x + 14) % (width + 110)
        self.redraw()
        self.after_id = self.after(80, self.animate)


class DropZone(tk.Canvas):
    def __init__(self, parent, on_drop, on_click, eyebrow, title, subtitle):
        super().__init__(
            parent,
            bg=COLOR_PANEL,
            bd=0,
            highlightthickness=0,
            relief="flat",
            height=250,
        )
        self.on_drop_func = on_drop
        self.on_click_func = on_click
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.accent = COLOR_BLUE
        self.fill = COLOR_PANEL

        self.bind("<Enter>", self.on_hover_enter)
        self.bind("<Leave>", self.on_hover_leave)
        self.bind("<Button-1>", lambda _event: self.on_click_func())
        self.bind("<Configure>", lambda _event: self.redraw())

        try:
            self.drop_target_register(DND_ALL)
            self.dnd_bind("<<DragEnter>>", self.on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self.on_drag_leave)
            self.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:
            pass

    def redraw(self):
        self.delete("all")
        width = max(self.winfo_width(), 360)
        height = max(self.winfo_height(), 230)
        self.create_rectangle(2, 2, width - 2, height - 2, fill=self.fill, outline=COLOR_BORDER, width=1)
        self.create_rectangle(16, 16, width - 16, height - 16, outline=self.accent, dash=(8, 7), width=2)
        self.create_rectangle(30, 30, 96, 96, fill="#192338", outline=COLOR_BORDER_SOFT)
        self.create_line(50, 63, 76, 63, fill=self.accent, width=3)
        self.create_line(63, 50, 63, 76, fill=self.accent, width=3)
        self.create_text(116, 42, text=self.eyebrow.upper(), anchor="w", fill=self.accent, font=FONT_SMALL_BOLD)
        self.create_text(116, 74, text=self.title, anchor="w", fill=COLOR_TEXT_MAIN, font=FONT_CARD_TITLE)
        self.create_text(32, 126, text=self.subtitle, anchor="nw", fill=COLOR_TEXT_SEC, font=FONT_BODY, width=width - 64)
        self.create_text(
            32,
            height - 42,
            text="Click to browse or drag files into this panel.",
            anchor="w",
            fill=COLOR_TEXT_MUTED,
            font=FONT_SMALL,
        )

    def on_hover_enter(self, _event):
        self.fill = COLOR_PANEL_ALT
        self.accent = COLOR_ACCENT
        self.redraw()

    def on_hover_leave(self, _event):
        self.fill = COLOR_PANEL
        self.accent = COLOR_BLUE
        self.redraw()

    def on_drag_enter(self, _event):
        self.fill = "#18253A"
        self.accent = COLOR_ACCENT
        self.redraw()

    def on_drag_leave(self, _event):
        self.on_hover_leave(None)

    def on_drop(self, event):
        self.on_hover_leave(None)
        if self.on_drop_func:
            self.on_drop_func(event)


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try:
            self.TkdndVersion = TkinterDnD._require(self)
        except Exception:
            self.TkdndVersion = None

        self.title("VB Compress")
        self.geometry("1120x760")
        self.minsize(980, 680)
        self.configure(fg_color=COLOR_BG_APP)

        self.img_files: list[str] = []
        self.pdf_files: list[str] = []
        self.is_processing = False
        self.active_mode = "Images"

        self.grid_columnconfigure(0, minsize=236)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_shell()
        self.setup_sidebar()
        self.setup_workspace()
        self.switch_mode("Images")
        self.update_dashboard()

    def setup_shell(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=0, width=236)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.workspace = ctk.CTkFrame(self, fg_color=COLOR_BG_APP, corner_radius=0)
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(2, weight=1)

    def setup_sidebar(self):
        self.sidebar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 18))
        brand.grid_columnconfigure(1, weight=1)

        try:
            pil_image = Image.open(resource_path("Logo.png"))
            self.logo_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(38, 38))
            ctk.CTkLabel(brand, text="", image=self.logo_img).grid(row=0, column=0, padx=(0, 12))
        except Exception:
            ctk.CTkLabel(brand, text="VB", font=("Arial", 18, "bold"), text_color=COLOR_ACCENT).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkLabel(brand, text="VB Compress", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="w"
        )
        ctk.CTkLabel(brand, text="Asset optimizer", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).grid(
            row=1, column=1, sticky="w"
        )

        ctk.CTkLabel(self.sidebar, text="LIBRARY", font=FONT_SMALL_BOLD, text_color=COLOR_TEXT_MUTED).grid(
            row=1, column=0, sticky="w", padx=22, pady=(10, 8)
        )
        self.btn_nav_img = self.create_nav_button("Image Queue", lambda: self.switch_mode("Images"))
        self.btn_nav_img.grid(row=2, column=0, sticky="ew", padx=16, pady=4)
        self.btn_nav_pdf = self.create_nav_button("PDF Queue", lambda: self.switch_mode("PDF"))
        self.btn_nav_pdf.grid(row=3, column=0, sticky="ew", padx=16, pady=4)

        ctk.CTkLabel(self.sidebar, text="SESSION", font=FONT_SMALL_BOLD, text_color=COLOR_TEXT_MUTED).grid(
            row=4, column=0, sticky="w", padx=22, pady=(30, 8)
        )
        session = ctk.CTkFrame(self.sidebar, fg_color=COLOR_PANEL, corner_radius=14, border_width=1, border_color=COLOR_BORDER_SOFT)
        session.grid(row=5, column=0, sticky="ew", padx=16)
        session.grid_columnconfigure(0, weight=1)

        self.lbl_sidebar_img_count = self.create_sidebar_metric(session, "Images", "0", 0)
        self.lbl_sidebar_pdf_count = self.create_sidebar_metric(session, "PDFs", "0", 1)
        self.lbl_sidebar_mode = self.create_sidebar_metric(session, "Active", "Images", 2)

        self.sidebar.grid_rowconfigure(6, weight=1)

        engine = ctk.CTkFrame(self.sidebar, fg_color=COLOR_PANEL_DEEP, corner_radius=14, border_width=1, border_color=COLOR_BORDER_SOFT)
        engine.grid(row=7, column=0, sticky="ew", padx=16, pady=(18, 22))
        ctk.CTkLabel(engine, text="ENGINE", font=FONT_SMALL_BOLD, text_color=COLOR_ACCENT).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(engine, text="Pillow + PyMuPDF", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=16)
        ctk.CTkLabel(engine, text="Local processing only", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(2, 14)
        )

    def setup_workspace(self):
        topbar = ctk.CTkFrame(self.workspace, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        topbar.grid_columnconfigure(0, weight=1)

        title_area = ctk.CTkFrame(topbar, fg_color="transparent")
        title_area.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_area, text="Workspace", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_area, text="Tune, compress, and export without leaving the queue.", font=FONT_BODY, text_color=COLOR_TEXT_SEC).pack(
            anchor="w"
        )

        self.lbl_top_status = ctk.CTkLabel(
            topbar,
            text="Ready",
            font=FONT_SMALL_BOLD,
            text_color=COLOR_ACCENT,
            fg_color=COLOR_PANEL,
            corner_radius=16,
            padx=16,
            pady=8,
        )
        self.lbl_top_status.grid(row=0, column=1, sticky="e")

        self.hero = HeroPanel(self.workspace)
        self.hero.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 18))

        self.content = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.content.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.panel_img = ctk.CTkFrame(self.content, fg_color="transparent")
        self.panel_pdf = ctk.CTkFrame(self.content, fg_color="transparent")
        self.panel_img.grid(row=0, column=0, sticky="nsew")
        self.panel_pdf.grid(row=0, column=0, sticky="nsew")

        self.setup_img_ui()
        self.setup_pdf_ui()

    def create_nav_button(self, text, command):
        return ctk.CTkButton(
            self.sidebar,
            text=text,
            command=command,
            anchor="w",
            height=44,
            corner_radius=12,
            font=FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=COLOR_SIDEBAR_ACTIVE,
            text_color=COLOR_TEXT_SEC,
        )

    def create_sidebar_metric(self, parent, label, value, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(12 if row == 0 else 6, 8))
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).grid(row=0, column=0, sticky="w")
        value_label = ctk.CTkLabel(frame, text=value, font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN)
        value_label.grid(row=0, column=1, sticky="e")
        return value_label

    def create_card(self, parent, row, column, *, columnspan=1, rowspan=1):
        card = ctk.CTkFrame(parent, fg_color=COLOR_PANEL, corner_radius=18, border_width=1, border_color=COLOR_BORDER_SOFT)
        card.grid(row=row, column=column, columnspan=columnspan, rowspan=rowspan, sticky="nsew", padx=8, pady=8)
        return card

    def create_section_title(self, parent, title, subtitle=None):
        ctk.CTkLabel(parent, text=title, font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(18, 0))
        if subtitle:
            ctk.CTkLabel(parent, text=subtitle, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(
                anchor="w", padx=20, pady=(2, 12)
            )
        else:
            ctk.CTkLabel(parent, text="", height=8).pack()

    def create_primary_button(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            font=("Arial", 17, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#D6FF8A",
            text_color="#09100B",
            height=54,
            corner_radius=16,
        )

    def create_secondary_button(self, parent, text, command, width=72):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            corner_radius=12,
            fg_color=COLOR_INPUT,
            hover_color=COLOR_SIDEBAR_ACTIVE,
            text_color=COLOR_TEXT_MAIN,
            font=FONT_SMALL_BOLD,
        )

    def setup_img_ui(self):
        self.panel_img.grid_columnconfigure(0, weight=3)
        self.panel_img.grid_columnconfigure(1, weight=2)
        self.panel_img.grid_rowconfigure(0, weight=1)

        queue_card = self.create_card(self.panel_img, 0, 0, rowspan=2)
        queue_card.grid_columnconfigure(0, weight=1)
        queue_card.grid_rowconfigure(1, weight=1)
        self.create_section_title(queue_card, "Image Library", "JPG, PNG, WEBP files and folders.")

        self.drop_img = DropZone(
            queue_card,
            on_drop=self.on_drop_img,
            on_click=self.select_img_files,
            eyebrow="import",
            title="Add image assets",
            subtitle="Build a queue from loose files or a folder tree. Duplicate output names are kept safe automatically.",
        )
        self.drop_img.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        queue_footer = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_footer.pack(fill="x", padx=18, pady=(0, 18))
        queue_footer.grid_columnconfigure(0, weight=1)
        self.lbl_img_status = ctk.CTkLabel(queue_footer, text="No files selected", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_SEC)
        self.lbl_img_status.grid(row=0, column=0, sticky="w")
        self.btn_reset_img = self.create_secondary_button(queue_footer, "Reset", self.reset_img_selection)
        self.btn_reset_img.grid(row=0, column=1, sticky="e")

        settings_card = self.create_card(self.panel_img, 0, 1)
        self.create_section_title(settings_card, "Profile", "Compression settings for the active job.")

        slider_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        slider_row.pack(fill="x", padx=20, pady=(4, 0))
        slider_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(slider_row, text="Quality", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN).grid(row=0, column=0, sticky="w")
        self.lbl_img_quality = ctk.CTkLabel(slider_row, text="80% Balanced", font=FONT_SMALL_BOLD, text_color=COLOR_ACCENT)
        self.lbl_img_quality.grid(row=0, column=1, sticky="e")

        self.slider_img = ctk.CTkSlider(
            settings_card,
            from_=1,
            to=100,
            number_of_steps=99,
            command=self.update_img_label,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_TEXT_MAIN,
            button_hover_color=COLOR_ACCENT,
            fg_color=COLOR_INPUT,
        )
        self.slider_img.set(80)
        self.slider_img.pack(fill="x", padx=20, pady=(10, 18))

        self.do_convert = ctk.BooleanVar(value=False)
        self.chk_convert = ctk.CTkCheckBox(
            settings_card,
            text="Convert format",
            variable=self.do_convert,
            command=self.toggle_convert_ui,
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            fg_color=COLOR_ACCENT_DARK,
            hover_color=COLOR_ACCENT,
            checkmark_color="#071008",
            border_color=COLOR_BORDER,
            corner_radius=6,
            border_width=1,
        )
        self.chk_convert.pack(anchor="w", padx=20, pady=(0, 14))

        self.frame_selectors = ctk.CTkFrame(settings_card, fg_color="transparent")
        combo_style = {
            "fg_color": COLOR_INPUT,
            "border_width": 1,
            "border_color": COLOR_BORDER,
            "button_color": COLOR_INPUT,
            "button_hover_color": COLOR_SIDEBAR_ACTIVE,
            "text_color": COLOR_TEXT_MAIN,
            "dropdown_fg_color": COLOR_PANEL,
            "dropdown_text_color": COLOR_TEXT_MAIN,
            "font": FONT_BODY,
            "corner_radius": 10,
        }
        self.combo_in = ctk.CTkComboBox(self.frame_selectors, values=["All", "PNG", "JPG", "WEBP"], width=104, **combo_style)
        self.combo_in.set("All")
        self.combo_in.pack(side="left")
        ctk.CTkLabel(self.frame_selectors, text="to", font=FONT_BODY, text_color=COLOR_TEXT_MUTED).pack(side="left", padx=10)
        self.combo_out = ctk.CTkComboBox(self.frame_selectors, values=["WEBP", "JPG", "PNG"], width=104, **combo_style)
        self.combo_out.set("WEBP")
        self.combo_out.pack(side="left")

        output_card = self.create_card(self.panel_img, 1, 1)
        self.create_section_title(output_card, "Export", "Destination and job launch.")
        self.entry_img_path = self.create_path_row(output_card, "Result_IMG")

        self.progress_img = ctk.CTkProgressBar(output_card, progress_color=COLOR_ACCENT, fg_color=COLOR_INPUT)
        self.progress_img.set(0)
        self.progress_img.pack(fill="x", padx=20, pady=(10, 0))
        self.lbl_img_progress = ctk.CTkLabel(output_card, text="", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        self.lbl_img_progress.pack(anchor="w", padx=20, pady=(6, 12))

        self.btn_start_img = self.create_primary_button(output_card, "Run Image Job", self.process_img)
        self.btn_start_img.pack(fill="x", padx=20, pady=(0, 20))

    def setup_pdf_ui(self):
        self.panel_pdf.grid_columnconfigure(0, weight=3)
        self.panel_pdf.grid_columnconfigure(1, weight=2)
        self.panel_pdf.grid_rowconfigure(0, weight=1)

        queue_card = self.create_card(self.panel_pdf, 0, 0, rowspan=2)
        queue_card.grid_columnconfigure(0, weight=1)
        queue_card.grid_rowconfigure(1, weight=1)
        self.create_section_title(queue_card, "PDF Library", "Documents, scans, and exported decks.")

        self.drop_pdf = DropZone(
            queue_card,
            on_drop=self.on_drop_pdf,
            on_click=self.select_pdf_files,
            eyebrow="import",
            title="Add PDF documents",
            subtitle="Use Optimize for real documents, or Scan DPI when you want a compact image-based PDF.",
        )
        self.drop_pdf.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        queue_footer = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_footer.pack(fill="x", padx=18, pady=(0, 18))
        queue_footer.grid_columnconfigure(0, weight=1)
        self.lbl_pdf_status = ctk.CTkLabel(queue_footer, text="No file selected", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_status.grid(row=0, column=0, sticky="w")
        self.btn_reset_pdf = self.create_secondary_button(queue_footer, "Reset", self.reset_pdf_selection)
        self.btn_reset_pdf.grid(row=0, column=1, sticky="e")

        settings_card = self.create_card(self.panel_pdf, 0, 1)
        self.create_section_title(settings_card, "Compatibility Profile", "Choose how the PDF should be processed.")

        self.pdf_mode = ctk.StringVar(value="Optimize")
        self.mode_pdf = ctk.CTkSegmentedButton(
            settings_card,
            values=["Optimize", "Scan DPI"],
            variable=self.pdf_mode,
            command=self.update_pdf_mode,
            fg_color=COLOR_INPUT,
            selected_color=COLOR_ACCENT_DARK,
            selected_hover_color=COLOR_ACCENT,
            unselected_color=COLOR_INPUT,
            unselected_hover_color=COLOR_SIDEBAR_ACTIVE,
            text_color=COLOR_TEXT_MAIN,
            font=FONT_BTN,
            height=40,
        )
        self.mode_pdf.pack(fill="x", padx=20, pady=(4, 18))

        dpi_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        dpi_row.pack(fill="x", padx=20, pady=(0, 0))
        dpi_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(dpi_row, text="DPI", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN).grid(row=0, column=0, sticky="w")
        self.lbl_pdf_quality = ctk.CTkLabel(dpi_row, text="", font=FONT_SMALL_BOLD, text_color=COLOR_ACCENT)
        self.lbl_pdf_quality.grid(row=0, column=1, sticky="e")

        self.slider_pdf = ctk.CTkSlider(
            settings_card,
            from_=30,
            to=150,
            number_of_steps=120,
            command=self.update_pdf_label,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_TEXT_MAIN,
            button_hover_color=COLOR_ACCENT,
            fg_color=COLOR_INPUT,
        )
        self.slider_pdf.set(100)
        self.slider_pdf.pack(fill="x", padx=20, pady=(10, 20))
        self.update_pdf_mode("Optimize")

        output_card = self.create_card(self.panel_pdf, 1, 1)
        self.create_section_title(output_card, "Export", "Destination and job launch.")
        self.entry_pdf_path = self.create_path_row(output_card, "Result_PDF")

        self.progress_pdf = ctk.CTkProgressBar(output_card, progress_color=COLOR_ACCENT, fg_color=COLOR_INPUT)
        self.progress_pdf.set(0)
        self.progress_pdf.pack(fill="x", padx=20, pady=(10, 0))
        self.lbl_pdf_progress = ctk.CTkLabel(output_card, text="", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        self.lbl_pdf_progress.pack(anchor="w", padx=20, pady=(6, 12))

        self.btn_start_pdf = self.create_primary_button(output_card, "Run PDF Job", self.process_pdf)
        self.btn_start_pdf.pack(fill="x", padx=20, pady=(0, 20))

    def create_path_row(self, parent, folder_name):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(
            row,
            placeholder_text="Save location...",
            fg_color=COLOR_INPUT,
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_MAIN,
            height=42,
            corner_radius=12,
            font=FONT_BODY,
        )
        entry.insert(0, os.path.join(os.getcwd(), folder_name))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.create_secondary_button(row, "Browse", lambda: self.choose_path(entry), width=86).grid(row=0, column=1)
        return entry

    def switch_mode(self, mode):
        self.active_mode = mode
        if mode == "Images":
            self.panel_img.tkraise()
        else:
            self.panel_pdf.tkraise()
        self.update_nav_styles()
        self.update_dashboard()

    def update_nav_styles(self):
        img_active = self.active_mode == "Images"
        self.btn_nav_img.configure(
            fg_color=COLOR_SIDEBAR_ACTIVE if img_active else "transparent",
            text_color=COLOR_TEXT_MAIN if img_active else COLOR_TEXT_SEC,
        )
        self.btn_nav_pdf.configure(
            fg_color=COLOR_SIDEBAR_ACTIVE if not img_active else "transparent",
            text_color=COLOR_TEXT_MAIN if not img_active else COLOR_TEXT_SEC,
        )

    def update_dashboard(self):
        if not hasattr(self, "hero"):
            return
        image_count = len(self.img_files)
        pdf_count = len(self.pdf_files)
        self.lbl_sidebar_img_count.configure(text=str(image_count))
        self.lbl_sidebar_pdf_count.configure(text=str(pdf_count))
        self.lbl_sidebar_mode.configure(text=self.active_mode)

        if self.active_mode == "Images":
            profile = self.image_profile_label()
            selected = image_count
        else:
            profile = "Scan DPI" if self.pdf_mode.get() == "Scan DPI" else "Optimize"
            selected = pdf_count
        self.hero.set_state(self.active_mode, selected, profile)

    def image_profile_label(self):
        quality = int(self.slider_img.get()) if hasattr(self, "slider_img") else 80
        if hasattr(self, "do_convert") and self.do_convert.get():
            return f"{quality}% -> {self.combo_out.get()}"
        return f"{quality}%"

    def on_drop_img(self, event):
        paths = collect_image_paths(parse_drop_data(event.data))
        if paths:
            self.img_files = self.merge_paths(self.img_files, paths)
            self.lbl_img_status.configure(text=f"{len(self.img_files)} files selected", text_color=COLOR_ACCENT)
            self.update_dashboard()

    def on_drop_pdf(self, event):
        paths = collect_pdf_paths(parse_drop_data(event.data))
        if paths:
            self.pdf_files = self.merge_paths(self.pdf_files, paths)
            self.lbl_pdf_status.configure(text=f"{len(self.pdf_files)} files selected", text_color=COLOR_ACCENT)
            self.update_dashboard()

    def reset_img_selection(self):
        if self.is_processing:
            return
        self.img_files = []
        self.lbl_img_status.configure(text="No files selected", text_color=COLOR_TEXT_SEC)
        self.lbl_img_progress.configure(text="")
        self.progress_img.set(0)
        self.update_dashboard()

    def reset_pdf_selection(self):
        if self.is_processing:
            return
        self.pdf_files = []
        self.lbl_pdf_status.configure(text="No file selected", text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_progress.configure(text="")
        self.progress_pdf.set(0)
        self.update_dashboard()

    def toggle_convert_ui(self):
        if self.do_convert.get():
            self.frame_selectors.pack(anchor="w", padx=20, pady=(0, 18))
        else:
            self.frame_selectors.pack_forget()
        self.update_dashboard()

    def update_img_label(self, value):
        quality = int(value)
        if quality > 85:
            text = f"{quality}% High Quality"
        elif quality > 70:
            text = f"{quality}% Balanced"
        else:
            text = f"{quality}% Max Compression"
        self.lbl_img_quality.configure(text=text)
        self.update_dashboard()

    def update_pdf_label(self, value):
        dpi = int(value)
        if self.pdf_mode.get() == "Optimize":
            self.lbl_pdf_quality.configure(text="Text-safe")
            return
        if dpi < 72:
            text = f"{dpi} DPI Small"
        elif dpi < 110:
            text = f"{dpi} DPI Balanced"
        else:
            text = f"{dpi} DPI Sharp"
        self.lbl_pdf_quality.configure(text=text)
        self.update_dashboard()

    def update_pdf_mode(self, _value):
        if self.pdf_mode.get() == "Optimize":
            self.slider_pdf.configure(state="disabled")
        else:
            self.slider_pdf.configure(state="normal")
        self.update_pdf_label(self.slider_pdf.get())
        self.update_dashboard()

    def choose_path(self, entry):
        directory = filedialog.askdirectory()
        if directory:
            entry.delete(0, "end")
            entry.insert(0, directory)

    def select_img_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ]
        )
        if not files:
            return
        filtered = collect_image_paths(files)
        if filtered:
            self.img_files = filtered
            self.lbl_img_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACCENT)
            self.update_dashboard()
        else:
            messagebox.showinfo("Info", "No valid images selected.")

    def select_pdf_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[
                ("PDF", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        if not files:
            return
        filtered = collect_pdf_paths(files)
        if filtered:
            self.pdf_files = filtered
            self.lbl_pdf_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACCENT)
            self.update_dashboard()
        else:
            messagebox.showinfo("Info", "No valid PDF selected.")

    def process_img(self):
        if self.is_processing:
            return
        if not self.img_files:
            messagebox.showwarning("Warning", "Please select files first.")
            return

        save_dir = self.entry_img_path.get().strip()
        if not save_dir:
            messagebox.showwarning("Warning", "Please choose a save location.")
            return

        quality = int(self.slider_img.get())
        convert_to = self.combo_out.get().lower() if self.do_convert.get() else None
        input_filter = self.combo_in.get().lower()

        def work(progress):
            return compress_images(
                self.img_files,
                save_dir,
                quality=quality,
                convert_to=convert_to,
                input_filter=input_filter,
                progress_callback=progress,
            )

        self.run_background_task(
            button=self.btn_start_img,
            default_text="Run Image Job",
            working_text="Compressing...",
            progress_bar=self.progress_img,
            progress_label=self.lbl_img_progress,
            status_label=self.lbl_img_status,
            output_dir=save_dir,
            item_label="files",
            work=work,
        )

    def process_pdf(self):
        if self.is_processing:
            return
        if not self.pdf_files:
            messagebox.showwarning("Warning", "Please select PDF first.")
            return

        save_dir = self.entry_pdf_path.get().strip()
        if not save_dir:
            messagebox.showwarning("Warning", "Please choose a save location.")
            return

        mode = "rasterize" if self.pdf_mode.get() == "Scan DPI" else "optimize"
        dpi = int(self.slider_pdf.get())

        def work(progress):
            return compress_pdfs(
                self.pdf_files,
                save_dir,
                mode=mode,
                dpi=dpi,
                progress_callback=progress,
            )

        self.run_background_task(
            button=self.btn_start_pdf,
            default_text="Run PDF Job",
            working_text="Processing...",
            progress_bar=self.progress_pdf,
            progress_label=self.lbl_pdf_progress,
            status_label=self.lbl_pdf_status,
            output_dir=save_dir,
            item_label="PDFs",
            work=work,
        )

    def run_background_task(
        self,
        *,
        button,
        default_text,
        working_text,
        progress_bar,
        progress_label,
        status_label,
        output_dir,
        item_label,
        work,
    ):
        self.set_processing_state(True)
        self.lbl_top_status.configure(text="Running", text_color=COLOR_WARNING)
        button.configure(text=working_text)
        progress_bar.set(0)
        progress_label.configure(text="Starting queue...", text_color=COLOR_TEXT_SEC)

        def progress(done, total, source):
            self.after(0, lambda: self.update_progress(progress_bar, progress_label, done, total, source))

        def runner():
            try:
                result = work(progress)
            except Exception:
                error_text = traceback.format_exc()
                self.after(0, lambda: self.finish_with_crash(button, default_text, progress_label, error_text))
                return
            self.after(
                0,
                lambda: self.finish_task(
                    button,
                    default_text,
                    progress_bar,
                    progress_label,
                    status_label,
                    output_dir,
                    item_label,
                    result,
                ),
            )

        threading.Thread(target=runner, daemon=True).start()

    def update_progress(self, progress_bar, progress_label, done, total, source):
        progress = done / total if total else 0
        progress_bar.set(progress)
        progress_label.configure(text=f"{done}/{total}: {Path(source).name}", text_color=COLOR_TEXT_SEC)

    def finish_task(
        self,
        button,
        default_text,
        progress_bar,
        progress_label,
        status_label,
        output_dir,
        item_label,
        result: BatchResult,
    ):
        self.set_processing_state(False)
        self.lbl_top_status.configure(text="Ready", text_color=COLOR_ACCENT)
        button.configure(text=default_text)
        progress_bar.set(1 if result.processed else 0)

        if result.total_errors:
            progress_label.configure(text=f"Done with {result.total_errors} errors", text_color=COLOR_ERROR)
            status_label.configure(text=f"{result.processed} processed, {result.total_errors} errors", text_color=COLOR_ERROR)
            messagebox.showwarning("Done with errors", self.build_result_message(result, output_dir, item_label))
        else:
            progress_label.configure(text=f"Done. Processed {result.processed} {item_label}.", text_color=COLOR_ACCENT)
            status_label.configure(text=f"{result.processed} {item_label} processed", text_color=COLOR_ACCENT)
            messagebox.showinfo("Done", self.build_result_message(result, output_dir, item_label))
        self.update_dashboard()

    def finish_with_crash(self, button, default_text, progress_label, error_text):
        self.set_processing_state(False)
        self.lbl_top_status.configure(text="Error", text_color=COLOR_ERROR)
        button.configure(text=default_text)
        progress_label.configure(text="Processing failed", text_color=COLOR_ERROR)
        print(error_text)
        messagebox.showerror("Error", "Processing failed. See terminal output for details.")

    def set_processing_state(self, is_processing):
        self.is_processing = is_processing
        state = "disabled" if is_processing else "normal"
        widgets = (
            self.btn_start_img,
            self.btn_start_pdf,
            self.btn_reset_img,
            self.btn_reset_pdf,
            self.chk_convert,
            self.mode_pdf,
            self.btn_nav_img,
            self.btn_nav_pdf,
        )
        for widget in widgets:
            widget.configure(state=state)
        if not is_processing:
            self.update_pdf_mode(self.pdf_mode.get())

    def build_result_message(self, result: BatchResult, output_dir, item_label):
        lines = [
            f"Processed: {result.processed} {item_label}",
            f"Skipped: {result.skipped}",
            f"Saved to: {output_dir}",
        ]
        if result.errors:
            lines.append("")
            lines.append("Errors:")
            for error in result.errors[:6]:
                lines.append(f"- {Path(error.source).name}: {error.message}")
            if len(result.errors) > 6:
                lines.append(f"...and {len(result.errors) - 6} more")
        return "\n".join(lines)

    @staticmethod
    def merge_paths(current, incoming):
        merged = list(current)
        seen = {str(Path(path).expanduser().resolve()) for path in merged}
        for path in incoming:
            key = str(Path(path).expanduser().resolve())
            if key not in seen:
                seen.add(key)
                merged.append(path)
        return merged


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as exc:
        print(f"CRASH: {exc}")
        traceback.print_exc()

import sys
import os
import tkinter as tk
import traceback

# --- 🛠 ВАЖНЫЙ ФИКС ДЛЯ PYTHON 3.14 🛠 ---
try:
    import tkinter.tix
except ImportError:
    tk.tix = tk
    sys.modules['tkinter.tix'] = tk
# ----------------------------------------

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF

try:
    from tkinterdnd2 import TkinterDnD, DND_ALL
except ImportError:
    print("\nОШИБКА: Библиотека tkinterdnd2 не найдена.\n")
    DND_ALL = 'all'
    class TkinterDnD:
        class DnDWrapper: pass
        @staticmethod
        def _require(self): pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- ЦВЕТА ---
COLOR_BG_APP = "#01110E"
COLOR_CARD = "#081F1A"
COLOR_ACCENT = "#FFFFFF"
COLOR_ACCENT_HOVER = "#E0E0E0"
COLOR_ACTIVE_TAB = "#03BD8E"
COLOR_ACTIVE_TAB_HOVER = "#029E76"
COLOR_BTN_SEC = "#112924"
COLOR_BTN_SEC_HOVER = "#1A3630"
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_SEC = "#8899A6"
COLOR_BORDER = "#1A3630"
COLOR_DROP_ZONE = "#0E2822"
COLOR_DROP_ACTIVE = "#153830"
COLOR_DROP_DRAG = "#1F4F44"

FONT_HEADER = ("Arial", 28, "bold")
FONT_SUBHEADER = ("Arial", 18, "bold")
FONT_BODY = ("Arial", 14)
FONT_BTN = ("Arial", 15, "bold")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- КЛАСС DROP ZONE ---
class DropZone(tk.Canvas):
    def __init__(self, parent, on_drop, on_click, text="Drop files here", icon="📂"):
        super().__init__(parent, bg=COLOR_DROP_ZONE, bd=0, highlightthickness=0, relief="flat", height=150)
        self.on_drop_func = on_drop
        self.on_click_func = on_click
        self.border = self.create_rectangle(0, 0, 1, 1, outline=COLOR_BORDER, dash=(8, 8), width=2)
        self.text_id = self.create_text(0, 0, text=f"{icon}\n{text}", fill=COLOR_TEXT_SEC, 
                                        font=("Arial", 14), justify="center", width=300)
        
        self.bind('<Enter>', self.on_hover_enter)
        self.bind('<Leave>', self.on_hover_leave)
        self.bind('<Button-1>', lambda e: self.on_click_func())
        self.bind('<Configure>', self.resize)

        try:
            self.drop_target_register(DND_ALL)
            self.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self.on_drag_leave)
            self.dnd_bind('<<Drop>>', self.on_drop)
        except: pass

    def resize(self, event):
        w, h = event.width, event.height
        self.coords(self.border, 5, 5, w-5, h-5)
        self.coords(self.text_id, w/2, h/2)

    def on_hover_enter(self, event):
        self.configure(bg=COLOR_DROP_ACTIVE)
        self.itemconfigure(self.border, outline=COLOR_ACTIVE_TAB)

    def on_hover_leave(self, event):
        self.configure(bg=COLOR_DROP_ZONE)
        self.itemconfigure(self.border, outline=COLOR_BORDER, dash=(8, 8), width=2)
        self.itemconfigure(self.text_id, fill=COLOR_TEXT_SEC)

    def on_drag_enter(self, event):
        self.configure(bg=COLOR_DROP_DRAG)
        self.itemconfigure(self.border, outline=COLOR_ACTIVE_TAB, dash=(4, 4), width=3)
        self.itemconfigure(self.text_id, fill=COLOR_TEXT_MAIN)

    def on_drag_leave(self, event):
        self.on_hover_leave(None)

    def on_drop(self, event):
        self.on_hover_leave(None)
        if self.on_drop_func: self.on_drop_func(event)


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try: self.TkdndVersion = TkinterDnD._require(self)
        except: pass

        self.title("VB Compress")
        # 1. Изменил геометрию
        self.geometry("480x980")
        self.configure(fg_color=COLOR_BG_APP)

        self.img_files = []
        self.pdf_files = []

        try:
            pil_image = Image.open(resource_path("Logo.png"))
            ratio = pil_image.width / pil_image.height
            new_h = 50
            new_w = int(new_h * ratio)
            self.logo_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(new_w, new_h))
            self.lbl_logo = ctk.CTkLabel(self, text="", image=self.logo_img)
            self.lbl_logo.pack(pady=(40, 20), anchor="center")
        except:
            self.lbl_title = ctk.CTkLabel(self, text="VB Compress", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN)
            self.lbl_title.pack(pady=(40, 20), anchor="center")

        tab_width = 360
        self.tabview = ctk.CTkTabview(self, width=tab_width, height=680,
                                      fg_color="transparent",
                                      segmented_button_fg_color=COLOR_BTN_SEC,
                                      segmented_button_selected_color=COLOR_ACTIVE_TAB,
                                      segmented_button_selected_hover_color=COLOR_ACTIVE_TAB_HOVER,
                                      segmented_button_unselected_color=COLOR_BTN_SEC,
                                      segmented_button_unselected_hover_color=COLOR_BTN_SEC_HOVER,
                                      text_color=COLOR_TEXT_MAIN, corner_radius=20)
        self.tabview.pack(pady=0, padx=20, fill="both", expand=True)

        self.tab_img = self.tabview.add("Images")
        self.tab_pdf = self.tabview.add("PDF")
        
        # 2. Делаем вкладки одинаковой ширины
        self.tabview._segmented_button.configure(width=tab_width, height=46, font=FONT_BTN)
        # Принудительно задаем ширину каждой кнопки
        for btn in self.tabview._segmented_button._buttons_dict.values():
            btn.configure(width=(tab_width - 10) / 2) # Делим пополам с учетом небольшого отступа

        self.setup_img_ui()
        self.setup_pdf_ui()

    def create_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=16, border_width=0)
        card.pack(fill="x", pady=10, padx=10)
        return card

    def create_custom_button(self, parent, text, command, primary=False):
        if primary:
            return ctk.CTkButton(parent, text=text, command=command, font=("Arial", 18, "bold"),
                                 fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                                 text_color="#000000", height=65, corner_radius=12)
        else:
            return ctk.CTkButton(parent, text=text, command=command, font=FONT_BTN,
                                 fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                                 text_color=COLOR_TEXT_MAIN, height=50, corner_radius=12)

    # --- ЛОГИКА ---
    def parse_drop_files(self, event_data):
        raw_data = event_data
        files = []
        temp_path = ""
        in_brackets = False
        for char in raw_data:
            if char == '{': in_brackets = True
            elif char == '}':
                in_brackets = False
                files.append(temp_path); temp_path = ""
            elif char == ' ' and not in_brackets:
                if temp_path: files.append(temp_path); temp_path = ""
            else: temp_path += char
        if temp_path: files.append(temp_path)
        return files

    def on_drop_img(self, event):
        paths = self.parse_drop_files(event.data)
        valid_ext = ('.png', '.jpg', '.jpeg', '.webp')
        final_list = []
        for p in paths:
            if os.path.isfile(p):
                if p.lower().endswith(valid_ext): final_list.append(p)
            elif os.path.isdir(p):
                for r, _, f_list in os.walk(p):
                    for f in f_list:
                        if f.lower().endswith(valid_ext): final_list.append(os.path.join(r, f))
        if final_list:
            self.img_files = list(set(self.img_files + final_list))
            self.lbl_img_status.configure(text=f"{len(self.img_files)} files selected", text_color=COLOR_ACTIVE_TAB)

    def on_drop_pdf(self, event):
        paths = self.parse_drop_files(event.data)
        valid_ext = ('.pdf')
        final_list = []
        for p in paths:
            if os.path.isfile(p) and p.lower().endswith(valid_ext): final_list.append(p)
        if final_list:
            self.pdf_files = list(set(self.pdf_files + final_list))
            self.lbl_pdf_status.configure(text=f"{len(self.pdf_files)} files selected", text_color=COLOR_ACTIVE_TAB)

    # 3. Функции сброса
    def reset_img_selection(self):
        self.img_files = []
        self.lbl_img_status.configure(text="No files selected", text_color=COLOR_TEXT_SEC)

    def reset_pdf_selection(self):
        self.pdf_files = []
        self.lbl_pdf_status.configure(text="No file selected", text_color=COLOR_TEXT_SEC)

    # --- UI ---
    def setup_img_ui(self):
        card_files = self.create_card(self.tab_img)
        ctk.CTkLabel(card_files, text="Select Content", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))

        self.drop_img = DropZone(card_files, on_drop=self.on_drop_img, on_click=self.select_img_files, text="Click or Drop images here", icon="📂")
        self.drop_img.pack(fill="x", padx=15, pady=(0, 10))

        # Блок статуса и кнопки сброса
        status_box = ctk.CTkFrame(card_files, fg_color="transparent")
        status_box.pack(fill="x", padx=15, pady=(0, 20))
        
        self.lbl_img_status = ctk.CTkLabel(status_box, text="No files selected", font=FONT_BODY, text_color=COLOR_TEXT_SEC)
        self.lbl_img_status.pack(side="left")

        # Кнопка Reset
        btn_reset = ctk.CTkButton(status_box, text="Reset", width=60, height=24, 
                                  fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                                  font=("Arial", 12), command=self.reset_img_selection)
        btn_reset.pack(side="right")


        card_settings = self.create_card(self.tab_img)
        ctk.CTkLabel(card_settings, text="Preferences", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkLabel(card_settings, text="Quality", font=FONT_BTN, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20)
        self.slider_img = ctk.CTkSlider(card_settings, from_=1, to=100, number_of_steps=100, command=self.update_img_label,
                                        progress_color=COLOR_ACTIVE_TAB, button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER, fg_color=COLOR_BTN_SEC)
        self.slider_img.set(80)
        self.slider_img.pack(fill="x", padx=20, pady=(5, 5))
        self.lbl_img_quality = ctk.CTkLabel(card_settings, text="80% (Recommended)", font=FONT_BODY, text_color=COLOR_TEXT_SEC)
        self.lbl_img_quality.pack(pady=(0, 20))

        self.do_convert = ctk.BooleanVar(value=False)
        self.chk_convert = ctk.CTkCheckBox(card_settings, text="Change Format", variable=self.do_convert, command=self.toggle_convert_ui,
                                           font=FONT_BTN, text_color=COLOR_TEXT_MAIN, fg_color=COLOR_ACTIVE_TAB, hover_color=COLOR_ACTIVE_TAB_HOVER,
                                           checkmark_color="#ffffff", border_color=COLOR_TEXT_SEC, corner_radius=6, border_width=1)
        self.chk_convert.pack(pady=16, padx=24, anchor="w")

        self.frame_selectors = ctk.CTkFrame(card_settings, fg_color="transparent")
        combo_style = {"fg_color": COLOR_BTN_SEC, "border_width": 0, "button_color": COLOR_BTN_SEC, "button_hover_color": COLOR_BTN_SEC_HOVER,
                       "text_color": COLOR_TEXT_MAIN, "dropdown_fg_color": COLOR_CARD, "dropdown_text_color": COLOR_TEXT_MAIN, "font": FONT_BODY, "corner_radius": 8}
        self.combo_in = ctk.CTkComboBox(self.frame_selectors, values=["All", "PNG", "JPG", "WEBP"], width=90, **combo_style)
        self.combo_in.set("All"); self.combo_in.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(self.frame_selectors, text="to", font=FONT_BODY, text_color=COLOR_TEXT_SEC).pack(side="left")
        self.combo_out = ctk.CTkComboBox(self.frame_selectors, values=["WEBP", "JPG", "PNG"], width=90, **combo_style)
        self.combo_out.set("WEBP"); self.combo_out.pack(side="left", padx=(10, 0))

        card_path = self.create_card(self.tab_img)
        self.entry_img_path = ctk.CTkEntry(card_path, placeholder_text="Save location...", fg_color=COLOR_BTN_SEC, border_width=0,
                                           text_color=COLOR_TEXT_MAIN, height=45, corner_radius=12, font=FONT_BODY)
        self.entry_img_path.insert(0, os.path.join(os.getcwd(), "Result_IMG"))
        self.entry_img_path.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=15)
        ctk.CTkButton(card_path, text="...", width=45, height=45, corner_radius=12, fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                      text_color=COLOR_TEXT_MAIN, command=lambda: self.choose_path(self.entry_img_path)).pack(side="right", padx=(0, 15))

        self.btn_start_img = self.create_custom_button(self.tab_img, "Compress Images", self.process_img, primary=True)
        self.btn_start_img.pack(fill="x", pady=20, padx=10, side="bottom")

    def setup_pdf_ui(self):
        card_files = self.create_card(self.tab_pdf)
        ctk.CTkLabel(card_files, text="Select Document", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))

        self.drop_pdf = DropZone(card_files, on_drop=self.on_drop_pdf, on_click=self.select_pdf_files, text="Click or Drop PDF here", icon="📄")
        self.drop_pdf.pack(fill="x", padx=15, pady=(0, 10))

        # Блок статуса и кнопки сброса
        status_box = ctk.CTkFrame(card_files, fg_color="transparent")
        status_box.pack(fill="x", padx=15, pady=(0, 20))

        self.lbl_pdf_status = ctk.CTkLabel(status_box, text="No file selected", font=FONT_BODY, text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_status.pack(side="left")

        btn_reset = ctk.CTkButton(status_box, text="Reset", width=60, height=24, 
                                  fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                                  font=("Arial", 12), command=self.reset_pdf_selection)
        btn_reset.pack(side="right")

        card_settings = self.create_card(self.tab_pdf)
        ctk.CTkLabel(card_settings, text="Compression Level", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        self.slider_pdf = ctk.CTkSlider(card_settings, from_=30, to=150, number_of_steps=120, command=self.update_pdf_label,
                                        progress_color=COLOR_ACTIVE_TAB, button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER, fg_color=COLOR_BTN_SEC)
        self.slider_pdf.set(100)
        self.slider_pdf.pack(fill="x", padx=20, pady=(5, 5))
        self.lbl_pdf_quality = ctk.CTkLabel(card_settings, text="100 DPI (Balanced)", font=FONT_BODY, text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_quality.pack(pady=(0, 20))

        card_path = self.create_card(self.tab_pdf)
        self.entry_pdf_path = ctk.CTkEntry(card_path, placeholder_text="Save location...", fg_color=COLOR_BTN_SEC, border_width=0,
                                           text_color=COLOR_TEXT_MAIN, height=45, corner_radius=12, font=FONT_BODY)
        self.entry_pdf_path.insert(0, os.path.join(os.getcwd(), "Result_PDF"))
        self.entry_pdf_path.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=15)
        ctk.CTkButton(card_path, text="...", width=45, height=45, corner_radius=12, fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                      text_color=COLOR_TEXT_MAIN, command=lambda: self.choose_path(self.entry_pdf_path)).pack(side="right", padx=(0, 15))

        self.btn_start_pdf = self.create_custom_button(self.tab_pdf, "Compress PDF", self.process_pdf, primary=True)
        self.btn_start_pdf.pack(fill="x", pady=20, padx=10, side="bottom")

    def toggle_convert_ui(self):
        if self.do_convert.get(): self.frame_selectors.pack(pady=(0, 15), padx=20, fill="x")
        else: self.frame_selectors.pack_forget()

    def update_img_label(self, value):
        val = int(value)
        text = f"{val}% (High Quality)" if val > 85 else (f"{val}% (Balanced)" if val > 70 else f"{val}% (Max Compression)")
        self.lbl_img_quality.configure(text=text)

    def update_pdf_label(self, value):
        dpi = int(value)
        text = f"{dpi} DPI - Low Quality" if dpi < 72 else (f"{dpi} DPI - Balanced" if dpi < 110 else f"{dpi} DPI - High Quality")
        self.lbl_pdf_quality.configure(text=text)

    def choose_path(self, entry):
        try:
            d = filedialog.askdirectory()
            if d:
                entry.delete(0, "end")
                entry.insert(0, d)
        except: pass

    def select_img_files(self):
        files = filedialog.askopenfilenames()
        if files:
            valid_ext = ('.png', '.jpg', '.jpeg', '.webp')
            filtered = [f for f in files if f.lower().endswith(valid_ext)]
            if filtered:
                self.img_files = list(filtered)
                self.lbl_img_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACTIVE_TAB)
            else: messagebox.showinfo("Info", "No valid images selected.")

    def select_pdf_files(self):
        files = filedialog.askopenfilenames()
        if files:
            valid_ext = ('.pdf')
            filtered = [f for f in files if f.lower().endswith(valid_ext)]
            if filtered:
                self.pdf_files = list(filtered)
                self.lbl_pdf_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACTIVE_TAB)
            else: messagebox.showinfo("Info", "No valid PDF selected.")

    def process_img(self):
        if not self.img_files:
            messagebox.showwarning("Warning", "Please select files first.")
            return

        save_dir = self.entry_img_path.get()
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        quality = int(self.slider_img.get())
        converting = self.do_convert.get()
        target_ext = self.combo_out.get().lower() if converting else None
        input_filter = self.combo_in.get().lower()
        count = 0
        self.btn_start_img.configure(text="Compressing...", state="disabled")
        self.update()

        for fpath in self.img_files:
            if converting and input_filter != "all" and not fpath.lower().endswith(input_filter): continue
            try:
                img = Image.open(fpath)
                current_ext = fpath.split('.')[-1].lower()
                save_ext = target_ext if converting else current_ext
                if save_ext == "jpg": save_ext = "jpeg"
                if save_ext == "jpeg" and img.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, mask=img.split()[-1]); img = bg
                elif save_ext == "jpeg" and img.mode != "RGB": img = img.convert("RGB")

                fname = os.path.splitext(os.path.basename(fpath))[0]
                out = os.path.join(save_dir, f"{fname}_compressed.{save_ext.replace('jpeg', 'jpg')}")
                img.save(out, quality=quality, optimize=True)
                count += 1
                self.update_idletasks()
            except Exception as e: print(f"Error {fpath}: {e}")

        self.btn_start_img.configure(text="Compress Images", state="normal")
        messagebox.showinfo("Done", f"Processed {count} files.")

    def process_pdf(self):
        if not self.pdf_files:
            messagebox.showwarning("Warning", "Please select PDF first.")
            return

        save_dir = self.entry_pdf_path.get()
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        target_dpi = int(self.slider_pdf.get())
        jpg_quality = 60 if target_dpi < 72 else 75
        count = 0
        self.btn_start_pdf.configure(text="Processing...", state="disabled")
        self.update()

        for fpath in self.pdf_files:
            try:
                doc = fitz.open(fpath)
                pdf_images = []
                for page in doc:
                    pix = page.get_pixmap(dpi=target_dpi)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    pdf_images.append(img)
                if pdf_images:
                    fname = os.path.splitext(os.path.basename(fpath))[0]
                    out = os.path.join(save_dir, f"{fname}_compressed.pdf")
                    pdf_images[0].save(out, "PDF", resolution=target_dpi, save_all=True, append_images=pdf_images[1:], quality=jpg_quality)
                    count += 1
                doc.close()
                self.update_idletasks()
            except Exception as e: print(f"Error PDF {fpath}: {e}")

        self.btn_start_pdf.configure(text="Compress PDF", state="normal")
        messagebox.showinfo("Done", f"Processed {count} PDFs.")

if __name__ == "__main__":
    try: app = App(); app.mainloop()
    except Exception as e: print(f"CRASH: {e}"); traceback.print_exc()
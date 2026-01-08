import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from PIL import Image
import fitz
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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

FONT_HEADER = ("Manrope", 28, "bold")
FONT_SUBHEADER = ("Manrope", 18, "bold")
FONT_BODY = ("Manrope", 14)
FONT_BTN = ("Manrope", 15, "bold")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VB Compress")
        self.geometry("480x900")
        self.resizable(False, False)
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
        except Exception as e:
            print(f"Logo error: {e}")
            self.lbl_title = ctk.CTkLabel(self, text="Compress.", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN)
            self.lbl_title.pack(pady=(40, 20), anchor="center")

        tab_width = 440

        self.tabview = ctk.CTkTabview(self,
                                      width=tab_width,
                                      height=620,
                                      fg_color="transparent",
                                      segmented_button_fg_color=COLOR_BTN_SEC,
                                      segmented_button_selected_color=COLOR_ACTIVE_TAB,
                                      segmented_button_selected_hover_color=COLOR_ACTIVE_TAB_HOVER,
                                      segmented_button_unselected_color=COLOR_BTN_SEC,
                                      segmented_button_unselected_hover_color=COLOR_BTN_SEC_HOVER,
                                      text_color=COLOR_TEXT_MAIN,
                                      corner_radius=20)

        self.tabview.pack(pady=0, padx=20, fill="both", expand=True)

        self.tab_img = self.tabview.add("Images")
        self.tab_pdf = self.tabview.add("PDF")

        self.tabview._segmented_button.configure(width=tab_width, height=45, font=FONT_BTN)

        for btn in self.tabview._segmented_button._buttons_dict.values():
            btn.configure(width=(tab_width - 20) / 3, text_color_disabled="#000000")

        self.setup_img_ui()
        self.setup_pdf_ui()

    def create_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=16, border_width=0)
        card.pack(fill="x", pady=10, padx=10)
        return card

    def create_custom_button(self, parent, text, command, primary=False):
        if primary:
            return ctk.CTkButton(parent, text=text, command=command,
                                 font=("Manrope", 18, "bold"),
                                 fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                                 text_color="#000000",
                                 height=65,
                                 corner_radius=12)
        else:
            return ctk.CTkButton(parent, text=text, command=command,
                                 font=FONT_BTN,
                                 fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                                 text_color=COLOR_TEXT_MAIN, height=50, corner_radius=12)

    def setup_img_ui(self):
        card_files = self.create_card(self.tab_img)
        ctk.CTkLabel(card_files, text="Select Content", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w", padx=20, pady=(20, 10))

        btn_box = ctk.CTkFrame(card_files, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(0, 20))

        self.btn_img_file = self.create_custom_button(btn_box, "Choose Files", self.select_img_files, primary=False)
        self.btn_img_file.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_img_folder = self.create_custom_button(btn_box, "Choose Folder", self.select_img_folder, primary=False)
        self.btn_img_folder.pack(side="right", fill="x", expand=True, padx=(5, 0))

        status_box = ctk.CTkFrame(card_files, fg_color="transparent")
        status_box.pack(pady=(0, 20))

        self.lbl_img_status = ctk.CTkLabel(status_box, text="No files selected", font=FONT_BODY,
                                           text_color=COLOR_TEXT_SEC)
        self.lbl_img_status.pack(side="left", padx=(0, 10))

        ctk.CTkButton(status_box, text="Reset", width=60, height=24,
                      fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                      text_color=COLOR_TEXT_MAIN, font=("Manrope", 12),
                      command=self.reset_img_selection).pack(side="left")

        card_settings = self.create_card(self.tab_img)
        ctk.CTkLabel(card_settings, text="Preferences", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(card_settings, text="Quality", font=FONT_BTN, text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20)

        self.slider_img = ctk.CTkSlider(card_settings, from_=1, to=100, number_of_steps=100,
                                        command=self.update_img_label,
                                        progress_color=COLOR_ACTIVE_TAB,
                                        button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER,
                                        fg_color=COLOR_BTN_SEC)
        self.slider_img.set(80)
        self.slider_img.pack(fill="x", padx=20, pady=(5, 5))
        self.lbl_img_quality = ctk.CTkLabel(card_settings, text="80% (Recommended)", font=FONT_BODY,
                                            text_color=COLOR_TEXT_SEC)
        self.lbl_img_quality.pack(pady=(0, 20))

        self.do_convert = ctk.BooleanVar(value=False)
        self.chk_convert = ctk.CTkCheckBox(card_settings, text="Change Format",
                                           variable=self.do_convert, command=self.toggle_convert_ui,
                                           font=FONT_BTN, text_color=COLOR_TEXT_MAIN,
                                           fg_color=COLOR_ACTIVE_TAB, hover_color=COLOR_ACTIVE_TAB_HOVER,
                                           checkmark_color="#ffffff", border_color=COLOR_ACCENT_HOVER,
                                           corner_radius=6, border_width=1)
        self.chk_convert.pack(pady=10, padx=20, anchor="w")

        self.frame_selectors = ctk.CTkFrame(card_settings, fg_color="transparent")

        combo_style = {
            "fg_color": COLOR_BTN_SEC, "border_width": 0, "button_color": COLOR_BTN_SEC,
            "button_hover_color": COLOR_BTN_SEC_HOVER, "text_color": COLOR_TEXT_MAIN,
            "dropdown_fg_color": COLOR_CARD, "dropdown_text_color": COLOR_TEXT_MAIN,
            "font": FONT_BODY, "corner_radius": 8
        }

        self.combo_in = ctk.CTkComboBox(self.frame_selectors, values=["All", "PNG", "JPG", "WEBP"], width=90,
                                        **combo_style)
        self.combo_in.set("All")
        self.combo_in.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.frame_selectors, text="to", font=FONT_BODY, text_color=COLOR_TEXT_SEC).pack(side="left")

        self.combo_out = ctk.CTkComboBox(self.frame_selectors, values=["WEBP", "JPG", "PNG"], width=90, **combo_style)
        self.combo_out.set("WEBP")
        self.combo_out.pack(side="left", padx=(10, 0))

        card_path = self.create_card(self.tab_img)
        self.entry_img_path = ctk.CTkEntry(card_path, placeholder_text="Save location...",
                                           fg_color=COLOR_BTN_SEC, border_width=0, text_color=COLOR_TEXT_MAIN,
                                           height=45, corner_radius=12, font=FONT_BODY)
        self.entry_img_path.insert(0, os.path.join(os.getcwd(), "Result_IMG"))
        self.entry_img_path.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=15)

        ctk.CTkButton(card_path, text="...", width=45, height=45, corner_radius=12,
                      fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER, text_color=COLOR_TEXT_MAIN,
                      command=lambda: self.choose_path(self.entry_img_path)).pack(side="right", padx=(0, 15))

        self.btn_start_img = self.create_custom_button(self.tab_img, "Compress Images", self.process_img, primary=True)
        self.btn_start_img.pack(fill="x", pady=20, padx=10, side="bottom")

    def setup_pdf_ui(self):
        card_files = self.create_card(self.tab_pdf)
        ctk.CTkLabel(card_files, text="Select Document", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w", padx=20, pady=(20, 10))

        self.btn_pdf_file = self.create_custom_button(card_files, "Choose PDF File", self.select_pdf_files, primary=False)
        self.btn_pdf_file.pack(fill="x", padx=15, pady=(0, 20))

        status_box = ctk.CTkFrame(card_files, fg_color="transparent")
        status_box.pack(pady=(0, 20))

        self.lbl_pdf_status = ctk.CTkLabel(status_box, text="No file selected", font=FONT_BODY,
                                           text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_status.pack(side="left", padx=(0, 10))

        ctk.CTkButton(status_box, text="Reset", width=60, height=24,
                      fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER,
                      text_color=COLOR_TEXT_MAIN, font=("Manrope", 12),
                      command=self.reset_pdf_selection).pack(side="left")

        card_settings = self.create_card(self.tab_pdf)
        ctk.CTkLabel(card_settings, text="Compression Level", font=FONT_SUBHEADER, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w", padx=20, pady=(20, 10))

        self.slider_pdf = ctk.CTkSlider(card_settings, from_=30, to=150, number_of_steps=120,
                                        command=self.update_pdf_label,
                                        progress_color=COLOR_ACTIVE_TAB, button_color=COLOR_ACCENT,
                                        button_hover_color=COLOR_ACCENT_HOVER,
                                        fg_color=COLOR_BTN_SEC)
        self.slider_pdf.set(100)
        self.slider_pdf.pack(fill="x", padx=20, pady=(5, 5))
        self.lbl_pdf_quality = ctk.CTkLabel(card_settings, text="100 DPI (Balanced)", font=FONT_BODY,
                                            text_color=COLOR_TEXT_SEC)
        self.lbl_pdf_quality.pack(pady=(0, 20))

        card_path = self.create_card(self.tab_pdf)
        self.entry_pdf_path = ctk.CTkEntry(card_path, placeholder_text="Save location...",
                                           fg_color=COLOR_BTN_SEC, border_width=0, text_color=COLOR_TEXT_MAIN,
                                           height=45, corner_radius=12, font=FONT_BODY)
        self.entry_pdf_path.insert(0, os.path.join(os.getcwd(), "Result_PDF"))
        self.entry_pdf_path.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=15)

        ctk.CTkButton(card_path, text="...", width=45, height=45, corner_radius=12,
                      fg_color=COLOR_BTN_SEC, hover_color=COLOR_BTN_SEC_HOVER, text_color=COLOR_TEXT_MAIN,
                      command=lambda: self.choose_path(self.entry_pdf_path)).pack(side="right", padx=(0, 15))

        self.btn_start_pdf = self.create_custom_button(self.tab_pdf, "Compress PDF", self.process_pdf, primary=True)
        self.btn_start_pdf.pack(fill="x", pady=20, padx=10, side="bottom")

    def toggle_convert_ui(self):
        if self.do_convert.get():
            self.frame_selectors.pack(pady=(0, 15), padx=20, fill="x")
        else:
            self.frame_selectors.pack_forget()

    def update_img_label(self, value):
        val = int(value)
        text = f"{val}% (High Quality)" if val > 85 else (
            f"{val}% (Balanced)" if val > 70 else f"{val}% (Max Compression)")
        self.lbl_img_quality.configure(text=text)

    def update_pdf_label(self, value):
        dpi = int(value)
        if dpi < 72:
            text = f"{dpi} DPI - Low Quality (Small size)"
        elif dpi < 110:
            text = f"{dpi} DPI - Balanced"
        else:
            text = f"{dpi} DPI - High Quality"
        self.lbl_pdf_quality.configure(text=text)

    def choose_path(self, entry):
        try:
            self.update_idletasks()
            d = filedialog.askdirectory()
            if d:
                entry.delete(0, "end")
                entry.insert(0, d)
        except:
            pass

    def select_img_files(self):
        self.update_idletasks()
        files = filedialog.askopenfilenames()
        if files:
            valid_ext = ('.png', '.jpg', '.jpeg', '.webp')
            filtered = [f for f in files if f.lower().endswith(valid_ext)]
            if filtered:
                self.img_files = list(filtered)
                self.lbl_img_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACCENT)
            else:
                messagebox.showinfo("Info", "No valid images selected.")

    def select_img_folder(self):
        self.update_idletasks()
        folder = filedialog.askdirectory()
        if folder:
            f_list = []
            for r, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        f_list.append(os.path.join(r, f))
            self.img_files = f_list
            self.lbl_img_status.configure(text=f"{len(f_list)} files found", text_color=COLOR_ACCENT)

    def select_pdf_files(self):
        self.update_idletasks()
        files = filedialog.askopenfilenames()
        if files:
            valid_ext = ('.pdf')
            filtered = [f for f in files if f.lower().endswith(valid_ext)]
            if filtered:
                self.pdf_files = list(filtered)
                self.lbl_pdf_status.configure(text=f"{len(filtered)} files selected", text_color=COLOR_ACCENT)
            else:
                messagebox.showinfo("Info", "No valid PDF selected.")

    def reset_img_selection(self):
        self.img_files = []
        self.lbl_img_status.configure(text="No files selected", text_color=COLOR_TEXT_SEC)

    def reset_pdf_selection(self):
        self.pdf_files = []
        self.lbl_pdf_status.configure(text="No file selected", text_color=COLOR_TEXT_SEC)

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
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                elif save_ext == "jpeg" and img.mode != "RGB":
                    img = img.convert("RGB")

                fname = os.path.splitext(os.path.basename(fpath))[0]
                out = os.path.join(save_dir, f"{fname}_compressed.{save_ext.replace('jpeg', 'jpg')}")

                img.save(out, quality=quality, optimize=True)
                count += 1
                self.update_idletasks()
            except Exception as e:
                print(f"Error {fpath}: {e}")

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
                    pdf_images[0].save(out, "PDF", resolution=target_dpi,
                                       save_all=True, append_images=pdf_images[1:],
                                       quality=jpg_quality)
                    count += 1
                doc.close()
                self.update_idletasks()
            except Exception as e:
                print(f"Error PDF {fpath}: {e}")

        self.btn_start_pdf.configure(text="Compress PDF", state="normal")
        messagebox.showinfo("Done", f"Processed {count} PDFs.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
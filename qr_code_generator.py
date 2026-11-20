"""A small Windows desktop app for creating and saving QR codes."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ctypes
import io
import struct

import qrcode
from PIL import Image, ImageTk


class QRCodeGenerator:
    PREVIEW_SIZE = 460

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("QR Code Generator")
        self.root.geometry("1020x700")
        self.root.minsize(860, 620)
        self.root.configure(bg="#f4f6f8")
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.qr_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", foreground="#182230", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#101828")
        style.configure("Hint.TLabel", foreground="#667085")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 9))
        style.configure("Accent.TButton", background="#175cd3", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1849a9")])

        outer = ttk.Frame(root, padding=28)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="QR Code Generator", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Turn text or a link into an image you can save.", style="Hint.TLabel").pack(anchor="w", pady=(4, 20))

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        input_panel = ttk.Frame(content, padding=(0, 8, 24, 0))
        input_panel.grid(row=0, column=0, sticky="nsew")
        ttk.Label(input_panel, text="Your information").pack(anchor="w", pady=(0, 8))
        self.text = tk.Text(input_panel, height=9, wrap="word", font=("Segoe UI", 11),
                            relief="solid", borderwidth=1, padx=10, pady=10,
                            highlightthickness=1, highlightbackground="#d0d5dd",
                            highlightcolor="#175cd3")
        self.text.pack(fill="x")
        self.text.bind("<KeyRelease>", self._update_count)
        self.count_label = ttk.Label(input_panel, text="0 characters", style="Hint.TLabel")
        self.count_label.pack(anchor="e", pady=(5, 14))

        self.generate_button = ttk.Button(input_panel, text="Generate QR code", style="Accent.TButton", command=self.generate)
        self.generate_button.pack(anchor="w")
        ttk.Label(input_panel, text="Enter a website, contact details, or any text.", style="Hint.TLabel", wraplength=320).pack(anchor="w", pady=(12, 0))

        preview_panel = ttk.Frame(content, padding=18)
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.configure(style="TFrame")
        ttk.Label(preview_panel, text="Preview").pack(anchor="w", pady=(0, 10))
        self.preview = tk.Label(preview_panel, text="Your QR code will appear here", bg="white",
                                fg="#98a2b3", font=("Segoe UI", 10), relief="solid", borderwidth=1,
                                compound="center")
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", self._resize_preview)
        action_row = ttk.Frame(preview_panel)
        action_row.pack(fill="x", pady=(14, 0))
        action_row.columnconfigure((0, 1), weight=1)
        self.save_button = ttk.Button(action_row, text="Save as PNG or JPEG", command=self.save, state="disabled")
        self.save_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.copy_button = ttk.Button(action_row, text="Copy image", command=self.copy_image, state="disabled")
        self.copy_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        footer = ttk.Label(outer, text="Press Esc to exit", style="Hint.TLabel")
        footer.pack(anchor="e", pady=(14, 0))
        self.text.focus_set()
        root.bind("<Control-Return>", lambda _event: self.generate())

    def _update_count(self, _event: tk.Event) -> None:
        count = len(self.text.get("1.0", "end-1c"))
        self.count_label.configure(text=f"{count:,} character" + ("" if count == 1 else "s"))

    def generate(self) -> None:
        data = self.text.get("1.0", "end-1c").strip()
        if not data:
            messagebox.showinfo("Add some information", "Type text or a link first, then generate your QR code.", parent=self.root)
            self.text.focus_set()
            return
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                               box_size=12, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            self.qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            self.preview.configure(text="")
            self._resize_preview()
            self.save_button.configure(state="normal")
            self.copy_button.configure(state="normal")
        except Exception as exc:
            messagebox.showerror("Could not make QR code", f"The information could not be encoded.\n\n{exc}", parent=self.root)

    def _resize_preview(self, _event: tk.Event | None = None) -> None:
        if self.qr_image is None:
            return
        width = max(1, min(self.PREVIEW_SIZE, self.preview.winfo_width() - 24))
        height = max(1, min(self.PREVIEW_SIZE, self.preview.winfo_height() - 24))
        preview = self.qr_image.copy()
        preview.thumbnail((width, height), Image.Resampling.NEAREST)
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.preview.configure(image=self.preview_photo)

    def copy_image(self) -> None:
        if self.qr_image is None:
            return
        try:
            # Windows image clipboard format CF_DIB contains a BMP image without
            # its 14-byte file header. Clipboard ownership transfers to Windows.
            bmp = io.BytesIO()
            self.qr_image.save(bmp, format="BMP")
            dib = bmp.getvalue()[14:]
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.OpenClipboard.argtypes = [ctypes.c_void_p]
            user32.OpenClipboard.restype = ctypes.c_bool
            user32.EmptyClipboard.restype = ctypes.c_bool
            user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
            user32.SetClipboardData.restype = ctypes.c_void_p
            user32.CloseClipboard.restype = ctypes.c_bool
            kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
            kernel32.GlobalAlloc.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
            kernel32.GlobalFree.restype = ctypes.c_void_p

            handle = kernel32.GlobalAlloc(0x0002, len(dib))  # GMEM_MOVEABLE
            if not handle:
                raise OSError("Windows could not allocate memory for the image.")
            locked = kernel32.GlobalLock(handle)
            if not locked:
                kernel32.GlobalFree(handle)
                raise OSError("Windows could not prepare the image for copying.")
            ctypes.memmove(locked, dib, len(dib))
            kernel32.GlobalUnlock(handle)

            if not user32.OpenClipboard(self.root.winfo_id()):
                kernel32.GlobalFree(handle)
                raise OSError("The clipboard is busy. Please try again.")
            try:
                if not user32.EmptyClipboard() or not user32.SetClipboardData(8, handle):  # CF_DIB
                    kernel32.GlobalFree(handle)
                    raise OSError("Windows could not copy the image to the clipboard.")
                handle = None  # Windows now owns the memory handle.
            finally:
                user32.CloseClipboard()
            messagebox.showinfo("Image copied", "The QR code image is ready to paste.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Could not copy image", str(exc), parent=self.root)

    def save(self) -> None:
        if self.qr_image is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save QR code",
            defaultextension=".png",
            initialfile="qr_code.png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg *.jpeg")],
        )
        if not path:
            return
        try:
            image = self.qr_image
            if path.lower().endswith((".jpg", ".jpeg")):
                image.convert("RGB").save(path, format="JPEG", quality=95)
            else:
                image.save(path, format="PNG")
            messagebox.showinfo("QR code saved", f"Saved to:\n{path}", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Could not save image", str(exc), parent=self.root)


def main() -> None:
    root = tk.Tk()
    QRCodeGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()

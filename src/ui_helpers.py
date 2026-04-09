
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from PIL import Image, ImageTk

# Приложение 3 — руководство по стилю
WHITE = "#FFFFFF"
PAGE_BG = "#FFFFFF"
SECONDARY_BG = "#7FFF00"
ACCENT = "#00FA9A"
DISCOUNT_BG = "#2E8B57"

CARD_SURFACE = "#FFFFFF"
CARD_BORDER = "#C6C6C8"
TEXT_PRIMARY = "#000000"
TEXT_SECONDARY = "#333333"
ACCENT_RING = "#00FA9A"
# Нет на складе (модуль 2): фон карточки товара
OUT_OF_STOCK_BG = "#87CEFA"
PHOTO_PLACEHOLDER_BG = "#EEEEEE"

FONT_UI = ("Times New Roman", 11)
FONT_UI_SM = ("Times New Roman", 10)
FONT_UI_BOLD = ("Times New Roman", 11, "bold")
FONT_UI_TITLE = ("Times New Roman", 12, "bold")
FONT_UI_LARGE = ("Times New Roman", 20, "bold")
FONT_HEADER = ("Times New Roman", 18, "bold")


def configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=FONT_UI, background=PAGE_BG, foreground=TEXT_PRIMARY)
    style.configure("TFrame", background=PAGE_BG)
    # Дополнительный фон — рамки групп (параметры списка, блоки форм)
    style.configure("TLabelframe", background=SECONDARY_BG, bordercolor=CARD_BORDER)
    style.configure("TLabelframe.Label", background=SECONDARY_BG, font=FONT_UI_BOLD, foreground=TEXT_PRIMARY)
    # Экран входа — только белый фон (без дополнительного цвета в рамках)
    style.configure("White.TLabelframe", background=WHITE, bordercolor=CARD_BORDER)
    style.configure("White.TLabelframe.Label", background=WHITE, font=FONT_UI_BOLD, foreground=TEXT_PRIMARY)
    style.configure("TLabel", background=PAGE_BG, foreground=TEXT_PRIMARY, font=FONT_UI)
    style.configure("Header.TLabel", background=PAGE_BG, foreground=TEXT_PRIMARY, font=FONT_HEADER)
    style.configure("TButton", font=FONT_UI, padding=(10, 5))
    # Акцентирование целевого действия
    style.configure("Accent.TButton", background=ACCENT, foreground=TEXT_PRIMARY)
    style.map("Accent.TButton", background=[("active", SECONDARY_BG)])
    style.configure("Treeview", font=FONT_UI, rowheight=26, background=CARD_SURFACE, fieldbackground=CARD_SURFACE)
    style.configure("Treeview.Heading", font=FONT_UI_BOLD, background=PAGE_BG)


def get_strike_font(widget: tk.Misc) -> tkfont.Font:
    font = tkfont.Font(widget, ("Times New Roman", 12, "bold"))
    font.configure(overstrike=1)
    return font


def load_image(path: Path, size: tuple[int, int]) -> ImageTk.PhotoImage:
    """Превью товара: вписать в размер, по центру на нейтральном фоне."""
    image = Image.open(path)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # type: ignore[attr-defined]
    image.thumbnail(size, resample)
    canvas = Image.new("RGBA", size, (240, 240, 240, 255))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    canvas.paste(image, (x, y), image)
    return ImageTk.PhotoImage(canvas)


def load_logo_preserve_aspect(path: Path, max_side: int = 80) -> ImageTk.PhotoImage:
    """Логотип: только пропорциональное уменьшение, без обрезки цвета и без подложки."""
    image = Image.open(path)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # type: ignore[attr-defined]
    image.thumbnail((max_side, max_side), resample)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    return ImageTk.PhotoImage(image)

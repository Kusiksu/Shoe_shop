
from __future__ import annotations

import contextlib
import tkinter as tk
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image

from db import initialize_database, query_one
from importer import build_database
from repositories import (
    delete_order,
    delete_product,
    ensure_lookup,
    get_order,
    get_order_items,
    get_orders,
    get_product,
    get_products,
    get_user_by_credentials,
    insert_order,
    insert_product,
    list_categories,
    list_customers,
    list_manufacturers,
    list_pickup_points,
    list_products_short,
    list_statuses_full,
    list_suppliers,
    list_units,
    next_order_id,
    product_is_used_in_orders,
    update_order,
    update_product,
)
from ui_helpers import (
    ACCENT_RING,
    CARD_BORDER,
    CARD_SURFACE,
    DISCOUNT_BG,
    FONT_UI,
    FONT_UI_BOLD,
    FONT_UI_LARGE,
    FONT_UI_SM,
    FONT_UI_TITLE,
    OUT_OF_STOCK_BG,
    PAGE_BG,
    PHOTO_PLACEHOLDER_BG,
    SECONDARY_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WHITE,
    configure_styles,
    get_strike_font,
    load_image,
    load_logo_preserve_aspect,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
PRODUCT_IMAGES_DIR = RESOURCES_DIR / "products"
PLACEHOLDER_PATH = RESOURCES_DIR / "picture.png"
ACTIVE_WINDOWS = {"product": None, "order": None}


def _bind_mousewheel_canvas(canvas: tk.Canvas) -> None:
    def wheel(event: tk.Event) -> None:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def enter(_e: tk.Event) -> None:
        canvas.bind_all("<MouseWheel>", wheel)

    def leave(_e: tk.Event) -> None:
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", enter)
    canvas.bind("<Leave>", leave)


@dataclass
class Session:
    full_name: str
    role_name: str
    can_search: int
    can_manage_products: int
    can_view_orders: int
    can_manage_orders: int


class ShoeStoreApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ООО «Обувь»")
        self.geometry("1480x900")
        self.minsize(1200, 800)
        self.configure(bg=WHITE)
        with contextlib.suppress(Exception):
            self.iconbitmap(RESOURCES_DIR / "Icon.ico")
        configure_styles(self)
        self.current_frame: tk.Frame | None = None
        self.logo_image = load_logo_preserve_aspect(RESOURCES_DIR / "Icon.png", max_side=80)
        self.set_session(Session("Гость", "Гость", 0, 0, 0, 0))
        self.show_login_page()

    def set_session(self, session: Session) -> None:
        self.session = session

    def switch_frame(self, frame_class, *args) -> None:
        try:
            widget = frame_class(self, *args)
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Ошибка интерфейса",
                f"Не удалось открыть экран.\n\n{exc}\n\nПодробности в консоли (если запуск из cmd).",
            )
            return
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = widget
        self.current_frame.pack(fill="both", expand=True)

    def show_login_page(self) -> None:
        self.set_session(Session("Гость", "Гость", 0, 0, 0, 0))
        self.switch_frame(LoginPage)

    def show_products_page(self) -> None:
        self.switch_frame(ProductListPage)

    def show_orders_page(self) -> None:
        if not self.session.can_view_orders:
            messagebox.showwarning("Предупреждение", "У вас нет прав на просмотр заказов.")
            return
        self.switch_frame(OrderListPage)


class BasePage(ttk.Frame):
    def __init__(self, master: ShoeStoreApp):
        super().__init__(master, padding=14)
        self.app = master
        self.configure(style="TFrame")
        self.build_header()

    def build_header(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="x", pady=(0, 10))
        left = ttk.Frame(container)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, image=self.app.logo_image).pack(side="left", padx=(0, 12))
        text_block = ttk.Frame(left)
        text_block.pack(side="left")
        ttk.Label(text_block, text="ООО «Обувь»", style="Header.TLabel").pack(anchor="w")
        ttk.Label(text_block, text="Информационная система магазина по продаже обуви").pack(anchor="w")
        right = ttk.Frame(container)
        right.pack(side="right")
        ttk.Label(right, text=f"ФИО: {self.app.session.full_name}").pack(anchor="e")
        ttk.Label(right, text=f"Роль: {self.app.session.role_name}").pack(anchor="e")

    def add_nav_buttons(self, include_orders: bool = True) -> None:
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 10))
        ttk.Button(row, text="Назад на экран входа", command=self.app.show_login_page).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Товары", command=self.app.show_products_page).pack(side="left", padx=(0, 6))
        if include_orders and self.app.session.can_view_orders:
            ttk.Button(row, text="Заказы", command=self.app.show_orders_page).pack(side="left")


class LoginPage(BasePage):
    def __init__(self, master: ShoeStoreApp):
        super().__init__(master)
        self.app.title("ООО «Обувь» — Авторизация")

        frame = ttk.Frame(self)
        frame.pack(pady=40)

        card = ttk.LabelFrame(frame, text="Вход в систему", padding=18, style="White.TLabelframe")
        card.pack()
        self.login_var = tk.StringVar()
        self.password_var = tk.StringVar()

        ttk.Label(card, text="Логин").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        ttk.Entry(card, textvariable=self.login_var, width=34).grid(row=0, column=1, padx=4, pady=6)
        ttk.Label(card, text="Пароль").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        ttk.Entry(card, textvariable=self.password_var, width=34, show="*").grid(row=1, column=1, padx=4, pady=6)
        ttk.Button(card, text="Войти", style="Accent.TButton", command=self.login).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 6))
        ttk.Button(card, text="Продолжить как гость", command=self.guest_login).grid(row=3, column=0, columnspan=2, sticky="ew")

        info = ttk.LabelFrame(frame, text="Учётные записи из файла user_import.xlsx", padding=12, style="White.TLabelframe")
        info.pack(fill="x", pady=(16, 0))
        demo_lines = [
            "Администратор: 94d5ous@gmail.com / uzWC67",
            "Менеджер: 1diph5e@tutanota.com / 8ntwUp",
            "Клиент: 5d4zbu@tutanota.com / rwVDh9",
        ]
        for line in demo_lines:
            ttk.Label(info, text=line).pack(anchor="w")

    def login(self) -> None:
        user = get_user_by_credentials(self.login_var.get().strip(), self.password_var.get().strip())
        if not user:
            messagebox.showerror("Ошибка авторизации", "Неверный логин или пароль. Проверьте данные из базы.")
            return
        self.app.set_session(
            Session(
                full_name=user["full_name"],
                role_name=user["role_name"],
                can_search=user["can_search"],
                can_manage_products=user["can_manage_products"],
                can_view_orders=user["can_view_orders"],
                can_manage_orders=user["can_manage_orders"],
            )
        )
        self.app.show_products_page()

    def guest_login(self) -> None:
        self.app.set_session(Session("Гость", "Гость", 0, 0, 0, 0))
        self.app.show_products_page()


class ProductListPage(BasePage):
    def __init__(self, master: ShoeStoreApp):
        super().__init__(master)
        self.app.title("ООО «Обувь» — Список товаров")
        self.add_nav_buttons()
        self.card_images: list = []
        self.selected_product_id: int | None = None

        controls = ttk.LabelFrame(self, text="Параметры списка товаров", padding=10)
        controls.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar()
        self.supplier_var = tk.StringVar(value="Все поставщики")
        self.sort_var = tk.StringVar(value="Без сортировки")

        ttk.Label(controls, text="Поиск").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.search_entry = ttk.Entry(controls, textvariable=self.search_var, width=30, state="normal" if self.app.session.can_search else "disabled")
        self.search_entry.grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(controls, text="Поставщик").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.supplier_combo = ttk.Combobox(
            controls,
            textvariable=self.supplier_var,
            values=["Все поставщики"] + list_suppliers(),
            width=28,
            state="readonly" if self.app.session.can_search else "disabled",
        )
        self.supplier_combo.grid(row=0, column=3, padx=4, pady=4)
        ttk.Label(controls, text="Сортировка").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        self.sort_combo = ttk.Combobox(
            controls,
            textvariable=self.sort_var,
            values=["Без сортировки", "По количеству ↑", "По количеству ↓"],
            width=20,
            state="readonly" if self.app.session.can_search else "disabled",
        )
        self.sort_combo.grid(row=0, column=5, padx=4, pady=4)

        action_row = ttk.Frame(self)
        action_row.pack(fill="x", pady=(0, 8))
        if self.app.session.can_manage_products:
            ttk.Button(action_row, text="Добавить товар", style="Accent.TButton", command=self.open_add_product).pack(side="left", padx=(0, 6))
            ttk.Button(action_row, text="Редактировать выбранный", command=self.open_edit_selected).pack(side="left", padx=(0, 6))
            ttk.Button(action_row, text="Удалить выбранный", command=self.delete_selected).pack(side="left")

        self.counter_var = tk.StringVar()
        ttk.Label(self, textvariable=self.counter_var).pack(anchor="w", pady=(0, 6))

        self._card_by_id: dict[int, tk.Frame] = {}
        self._scroll_canvas: tk.Canvas | None = None
        self._canvas_window: int | None = None
        self.cards_inner: tk.Frame | None = None

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)
        self._scroll_canvas = tk.Canvas(outer, bg=PAGE_BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=sb.set)
        self.cards_inner = tk.Frame(self._scroll_canvas, bg=PAGE_BG)
        self._canvas_window = self._scroll_canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", self._on_products_inner_configure)
        self._scroll_canvas.bind("<Configure>", self._on_products_canvas_configure)
        self._scroll_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        _bind_mousewheel_canvas(self._scroll_canvas)

        # Поиск, фильтр и сортировка без отдельной кнопки «Применить» (модуль 3)
        self.search_var.trace_add("write", lambda *_: self.refresh_products())
        self.supplier_var.trace_add("write", lambda *_: self.refresh_products())
        self.sort_var.trace_add("write", lambda *_: self.refresh_products())

        self.refresh_products()

    def _on_products_inner_configure(self, _event: object) -> None:
        if self._scroll_canvas:
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_products_canvas_configure(self, event: tk.Event) -> None:
        if self._scroll_canvas and self._canvas_window is not None:
            self._scroll_canvas.itemconfig(self._canvas_window, width=event.width)

    def refresh_products(self) -> None:
        if not self.cards_inner:
            return
        try:
            self.update_idletasks()
            tw = self._scroll_canvas.winfo_width() if self._scroll_canvas else 900
            self._card_wrap = max(tw - 280, 320) if tw > 80 else 520

            for child in self.cards_inner.winfo_children():
                child.destroy()
            self._card_by_id.clear()
            self.card_images.clear()

            rows = get_products(self.search_var.get(), self.supplier_var.get(), self.sort_var.get())
            self.counter_var.set(f"Найдено товаров: {len(rows)}")
            for product in rows:
                card = self._build_product_card(product)
                card.pack(fill="x", padx=4, pady=6, in_=self.cards_inner)
                self._card_by_id[product["product_id"]] = card

            self.update_idletasks()
            if self._scroll_canvas:
                self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

            sel = self.selected_product_id
            if sel is not None and sel in self._card_by_id:
                self._set_card_selected(self._card_by_id[sel], True)
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Ошибка списка товаров", f"Не удалось обновить список:\n{exc}")

    def _set_card_selected(self, card: tk.Frame, selected: bool) -> None:
        if selected:
            card.configure(highlightbackground=ACCENT_RING, highlightthickness=2, highlightcolor=ACCENT_RING)
        else:
            card.configure(highlightthickness=0)

    def _build_product_card(self, product: dict) -> tk.Frame:
        # Сначала скидка > 15% (зелёный), иначе нулевой остаток (голубой по ТЗ), иначе белый фон
        if product["discount_percent"] > 15:
            surface = DISCOUNT_BG
            txt_main = "#FFFFFF"
            txt_muted = "#E8F8F0"
        elif product["stock_quantity"] == 0:
            surface = OUT_OF_STOCK_BG
            txt_main = TEXT_PRIMARY
            txt_muted = TEXT_SECONDARY
        else:
            surface = CARD_SURFACE
            txt_main = TEXT_PRIMARY
            txt_muted = TEXT_SECONDARY

        card = tk.Frame(
            self.cards_inner,
            bg=surface,
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        card.grid_columnconfigure(1, weight=1)

        photo_box = tk.Frame(
            card,
            bg=PHOTO_PLACEHOLDER_BG,
            width=148,
            height=118,
            highlightbackground="#C7C7CC",
            highlightthickness=1,
        )
        photo_box.grid(row=0, column=0, padx=(12, 14), pady=12, sticky="nw")
        photo_box.grid_propagate(False)

        image_path = BASE_DIR / product["image_path"]
        if not image_path.exists():
            image_path = PLACEHOLDER_PATH
        image = load_image(image_path, (120, 80))
        self.card_images.append(image)
        image_label = tk.Label(photo_box, image=image, bg=PHOTO_PLACEHOLDER_BG)
        image_label.place(relx=0.5, rely=0.5, anchor="center")

        mid = tk.Frame(card, bg=surface)
        mid.grid(row=0, column=1, sticky="nsew", pady=12)
        line1 = tk.Label(
            mid,
            text=f'{product["category_name"]}  |  {product["product_name"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI_TITLE,
            anchor="w",
        )
        line1.pack(anchor="w")
        tk.Label(
            mid,
            text=f'Артикул: {product["article"]}',
            bg=surface,
            fg=txt_muted,
            font=FONT_UI_SM,
            anchor="w",
        ).pack(anchor="w", pady=(2, 6))

        wrap = getattr(self, "_card_wrap", 520)
        tk.Label(
            mid,
            text=f'Описание товара: {product["description"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI,
            anchor="w",
            justify="left",
            wraplength=wrap,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            mid,
            text=f'Производитель: {product["manufacturer_name"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI,
            anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            mid,
            text=f'Поставщик: {product["supplier_name"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI,
            anchor="w",
        ).pack(anchor="w", pady=(0, 2))

        price_row = tk.Frame(mid, bg=surface)
        price_row.pack(anchor="w", pady=(4, 2))
        if product["discount_percent"] > 0:
            tk.Label(
                price_row,
                text=f'{product["price"]:.2f} ₽',
                fg="#FF3B30" if surface != DISCOUNT_BG else "#FFE5E5",
                bg=surface,
                font=get_strike_font(price_row),
            ).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(
                price_row,
                text=f'{product["final_price"]:.2f} ₽',
                fg=txt_main,
                bg=surface,
                font=FONT_UI_BOLD,
            ).pack(side=tk.LEFT)
        else:
            tk.Label(
                price_row,
                text=f'Цена: {product["price"]:.2f} ₽',
                fg=txt_main,
                bg=surface,
                font=FONT_UI_BOLD,
            ).pack(side=tk.LEFT)

        tk.Label(
            mid,
            text=f'Единица измерения: {product["unit_name"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI,
            anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            mid,
            text=f'Количество на складе: {product["stock_quantity"]}',
            bg=surface,
            fg=txt_main,
            font=FONT_UI_BOLD,
            anchor="w",
        ).pack(anchor="w")

        right = tk.Frame(card, bg=surface, width=128)
        right.grid(row=0, column=2, padx=(8, 12), pady=12, sticky="ne")
        tk.Label(
            right,
            text="Действующая\nскидка",
            bg=surface,
            fg=txt_main,
            font=FONT_UI_SM,
            justify="center",
        ).pack(pady=(4, 0))
        tk.Label(
            right,
            text=f'{product["discount_percent"]}%',
            bg=surface,
            fg=txt_main,
            font=FONT_UI_LARGE,
        ).pack(pady=(4, 0))

        self._bind_tree_clicks(card, product["product_id"])

        return card

    def _bind_tree_clicks(self, root: tk.Widget, product_id: int) -> None:
        def on_click(_e: tk.Event) -> None:
            self.select_product(product_id)
            # Редактирование по одному щелчку (ТЗ модуля 3); второй щелчок по той же карточке снова откроет форму
            if self.app.session.can_manage_products:
                self.open_product_form(product_id)

        def walk(w: tk.Widget) -> None:
            w.bind("<Button-1>", on_click)
            for ch in w.winfo_children():
                walk(ch)

        walk(root)

    def select_product(self, product_id: int) -> None:
        if self.selected_product_id == product_id:
            return
        old = self.selected_product_id
        self.selected_product_id = product_id
        if old is not None and old in self._card_by_id:
            self._set_card_selected(self._card_by_id[old], False)
        if product_id in self._card_by_id:
            self._set_card_selected(self._card_by_id[product_id], True)

    def open_add_product(self) -> None:
        self.open_product_form(None)

    def open_edit_selected(self) -> None:
        if self.selected_product_id is None:
            messagebox.showinfo("Информация", "Сначала выберите товар.")
            return
        self.open_product_form(self.selected_product_id)

    def open_product_form(self, product_id: int | None) -> None:
        # Одно окно товара на приложение (ограничение ТЗ модуля 3)
        existing = ACTIVE_WINDOWS["product"]
        if existing and existing.winfo_exists():
            existing.focus_set()
            return
        ACTIVE_WINDOWS["product"] = ProductForm(self.app, self, product_id)

    def delete_selected(self) -> None:
        if self.selected_product_id is None:
            messagebox.showinfo("Информация", "Сначала выберите товар для удаления.")
            return
        product = get_product(self.selected_product_id)
        if not product:
            return
        if product_is_used_in_orders(self.selected_product_id):
            messagebox.showwarning("Удаление запрещено", "Товар присутствует в заказах, поэтому удалить его нельзя.")
            return
        if not messagebox.askyesno("Подтверждение", f'Удалить товар "{product["product_name"]}"?'):
            return
        delete_product(self.selected_product_id)
        self.selected_product_id = None
        self.refresh_products()


class ProductForm(tk.Toplevel):
    def __init__(self, app: ShoeStoreApp, owner: ProductListPage, product_id: int | None):
        super().__init__(app)
        self.app = app
        self.owner = owner
        self.product_id = product_id
        self.title("ООО «Обувь» — Добавление / редактирование товара")
        self.geometry("860x760")
        self.configure(bg=WHITE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.category_var = tk.StringVar()
        self.manufacturer_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.unit_var = tk.StringVar()
        self.article_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.stock_var = tk.StringVar()
        self.discount_var = tk.StringVar()
        self.image_path: str = ""
        self.original_image_path: str = ""

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        r = 0
        # При добавлении ID не показываем (ТЗ модуля 3); при редактировании — только для чтения
        if product_id is not None:
            ttk.Label(body, text=f"ID товара: {product_id}").grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 10))
            r += 1
        self._add_entry(body, "Артикул", self.article_var, r)
        r += 1
        self._add_entry(body, "Наименование товара", self.name_var, r)
        r += 1
        self._add_combo(body, "Категория товара", self.category_var, list_categories(), r)
        r += 1
        self._add_combo(body, "Производитель", self.manufacturer_var, list_manufacturers(), r)
        r += 1
        self._add_combo(body, "Поставщик", self.supplier_var, list_suppliers(), r)
        r += 1
        self._add_combo(body, "Единица измерения", self.unit_var, list_units(), r)
        r += 1
        self._add_entry(body, "Цена", self.price_var, r)
        r += 1
        self._add_entry(body, "Количество на складе", self.stock_var, r)
        r += 1
        self._add_entry(body, "Действующая скидка", self.discount_var, r)
        r += 1

        ttk.Label(body, text="Описание товара").grid(row=r, column=0, sticky="nw", pady=6, padx=4)
        self.description_text = tk.Text(body, height=8, width=60, font=FONT_UI)
        self.description_text.grid(row=r, column=1, sticky="ew", pady=6, padx=4)
        r += 1

        ttk.Label(body, text="Фото").grid(row=r, column=0, sticky="w", pady=6, padx=4)
        photo_row = ttk.Frame(body)
        photo_row.grid(row=r, column=1, sticky="w", pady=6, padx=4)
        r += 1
        self.image_label_var = tk.StringVar(value="Файл не выбран")
        ttk.Label(photo_row, textvariable=self.image_label_var).pack(side="left", padx=(0, 10))
        ttk.Button(photo_row, text="Выбрать изображение", command=self.choose_image).pack(side="left")

        self.preview_label = ttk.Label(body)
        self.preview_label.grid(row=r, column=1, sticky="w", pady=(4, 12), padx=4)
        r += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Сохранить", style="Accent.TButton", command=self.save).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Отмена", command=self.close_window).pack(side="left")

        body.columnconfigure(1, weight=1)

        if product_id is not None:
            self.load_product()
        else:
            self.image_path = str(PLACEHOLDER_PATH.relative_to(BASE_DIR)).replace("\\", "/")
            self.update_preview(BASE_DIR / self.image_path)

    def _add_entry(self, parent, label_text: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=6, padx=4)
        ttk.Entry(parent, textvariable=variable, width=50).grid(row=row, column=1, sticky="ew", pady=6, padx=4)

    def _add_combo(self, parent, label_text: str, variable: tk.StringVar, values: list[str], row: int) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=6, padx=4)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=47).grid(row=row, column=1, sticky="ew", pady=6, padx=4)

    def load_product(self) -> None:
        product = get_product(self.product_id)
        if not product:
            messagebox.showerror("Ошибка", "Товар не найден.")
            self.close_window()
            return
        self.article_var.set(product["article"])
        self.name_var.set(product["product_name"])
        self.category_var.set(product["category_name"])
        self.manufacturer_var.set(product["manufacturer_name"])
        self.supplier_var.set(product["supplier_name"])
        self.unit_var.set(product["unit_name"])
        self.price_var.set(str(product["price"]))
        self.stock_var.set(str(product["stock_quantity"]))
        self.discount_var.set(str(product["discount_percent"]))
        self.description_text.insert("1.0", product["description"])
        self.image_path = product["image_path"] or str(PLACEHOLDER_PATH.relative_to(BASE_DIR)).replace("\\", "/")
        self.original_image_path = self.image_path
        self.image_label_var.set(self.image_path)
        self.update_preview(BASE_DIR / self.image_path)

    def choose_image(self) -> None:
        filename = filedialog.askopenfilename(
            title="Выберите изображение товара",
            filetypes=[("Изображения", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if not filename:
            return
        try:
            old_custom = BASE_DIR / self.image_path if self.image_path.startswith("resources/products/user_") else None
            image = Image.open(filename)
            image.thumbnail((300, 200))
            target_name = f"user_{Path(filename).stem}.png"
            target_path = PRODUCT_IMAGES_DIR / target_name
            canvas = Image.new("RGB", (300, 200), (240, 240, 240))
            x = (300 - image.width) // 2
            y = (200 - image.height) // 2
            canvas.paste(image, (x, y))
            canvas.save(target_path)
            self.image_path = str(target_path.relative_to(BASE_DIR)).replace("\\", "/")
            self.image_label_var.set(self.image_path)
            self.update_preview(target_path)
            if old_custom and old_custom.exists() and old_custom != target_path:
                old_custom.unlink(missing_ok=True)
        except Exception as error:
            messagebox.showerror("Ошибка", f"Не удалось обработать изображение:\n{error}")

    def update_preview(self, path: Path) -> None:
        try:
            self.preview_image = load_image(path, (200, 130))
            self.preview_label.configure(image=self.preview_image)
        except Exception:
            self.preview_label.configure(text="Предпросмотр недоступен")

    def validate(self) -> bool:
        try:
            price = float(self.price_var.get().replace(",", "."))
            stock = int(self.stock_var.get())
            discount = int(self.discount_var.get())
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Цена должна быть числом, а количество и скидка — целыми числами.")
            return False
        if price < 0 or stock < 0:
            messagebox.showerror("Ошибка ввода", "Цена и количество на складе не могут быть отрицательными.")
            return False
        if not 0 <= discount <= 100:
            messagebox.showerror("Ошибка ввода", "Скидка должна быть в диапазоне от 0 до 100.")
            return False
        required = [self.article_var.get(), self.name_var.get(), self.category_var.get(), self.manufacturer_var.get(), self.supplier_var.get(), self.unit_var.get()]
        if any(not value.strip() for value in required):
            messagebox.showwarning("Предупреждение", "Заполните все обязательные поля.")
            return False
        return True

    def save(self) -> None:
        if not self.validate():
            return
        if not messagebox.askyesno("Подтверждение", "Сохранить изменения товара?"):
            return
        payload = {
            "article": self.article_var.get().strip(),
            "product_name": self.name_var.get().strip(),
            "category_id": ensure_lookup("categories", "category_name", self.category_var.get().strip()),
            "manufacturer_id": ensure_lookup("manufacturers", "manufacturer_name", self.manufacturer_var.get().strip()),
            "supplier_id": ensure_lookup("suppliers", "supplier_name", self.supplier_var.get().strip()),
            "unit_id": ensure_lookup("units", "unit_name", self.unit_var.get().strip()),
            "price": float(self.price_var.get().replace(",", ".")),
            "stock_quantity": int(self.stock_var.get()),
            "discount_percent": int(self.discount_var.get()),
            "description": self.description_text.get("1.0", "end").strip(),
            "image_path": self.image_path or str(PLACEHOLDER_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        }
        try:
            if self.product_id is None:
                insert_product(payload)
            else:
                update_product(self.product_id, payload)
        except Exception as error:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить товар:\n{error}")
            return
        self.owner.refresh_products()
        self.close_window()

    def close_window(self) -> None:
        ACTIVE_WINDOWS["product"] = None
        self.destroy()


class OrderListPage(BasePage):
    def __init__(self, master: ShoeStoreApp):
        super().__init__(master)
        self.app.title("ООО «Обувь» — Заказы")
        self.add_nav_buttons()
        self.selected_order_id: int | None = None
        self._order_card_by_id: dict[int, tk.Frame] = {}
        self._orders_canvas: tk.Canvas | None = None
        self._orders_canvas_window: int | None = None
        self.orders_inner: tk.Frame | None = None

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(0, 8))
        if self.app.session.can_manage_orders:
            ttk.Button(buttons, text="Добавить заказ", style="Accent.TButton", command=lambda: self.open_order_form(None)).pack(side="left", padx=(0, 6))
            ttk.Button(buttons, text="Редактировать выбранный", command=self.open_selected_order).pack(side="left", padx=(0, 6))
            ttk.Button(buttons, text="Удалить выбранный", command=self.delete_selected_order).pack(side="left")

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)
        self._orders_canvas = tk.Canvas(outer, bg=PAGE_BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._orders_canvas.yview)
        self._orders_canvas.configure(yscrollcommand=sb.set)
        self.orders_inner = tk.Frame(self._orders_canvas, bg=PAGE_BG)
        self._orders_canvas_window = self._orders_canvas.create_window((0, 0), window=self.orders_inner, anchor="nw")
        self.orders_inner.bind("<Configure>", self._on_orders_inner_configure)
        self._orders_canvas.bind("<Configure>", self._on_orders_canvas_configure)
        self._orders_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        _bind_mousewheel_canvas(self._orders_canvas)

        self.refresh_orders()

    def _on_orders_inner_configure(self, _event: object) -> None:
        if self._orders_canvas:
            self._orders_canvas.configure(scrollregion=self._orders_canvas.bbox("all"))

    def _on_orders_canvas_configure(self, event: tk.Event) -> None:
        if self._orders_canvas and self._orders_canvas_window is not None:
            self._orders_canvas.itemconfig(self._orders_canvas_window, width=event.width)

    def refresh_orders(self) -> None:
        if not self.orders_inner:
            return
        for child in self.orders_inner.winfo_children():
            child.destroy()
        self._order_card_by_id.clear()
        for row in get_orders():
            card = self._build_order_card(row)
            card.pack(fill="x", padx=4, pady=6, in_=self.orders_inner)
            self._order_card_by_id[int(row["order_id"])] = card
        self.update_idletasks()
        if self._orders_canvas:
            self._orders_canvas.configure(scrollregion=self._orders_canvas.bbox("all"))
        if self.selected_order_id is not None and self.selected_order_id in self._order_card_by_id:
            self._set_order_selected(self._order_card_by_id[self.selected_order_id], True)

    def _set_order_selected(self, card: tk.Frame, selected: bool) -> None:
        if selected:
            card.configure(highlightbackground=ACCENT_RING, highlightthickness=2, highlightcolor=ACCENT_RING)
        else:
            card.configure(highlightthickness=0)

    def _build_order_card(self, row: dict) -> tk.Frame:
        oid = int(row["order_id"])
        surface = CARD_SURFACE
        card = tk.Frame(self.orders_inner, bg=surface, bd=1, relief="solid", highlightthickness=0)
        inner = tk.Frame(card, bg=surface)
        inner.pack(fill="both", expand=True)

        left = tk.Frame(inner, bg=surface)
        left.pack(side=tk.LEFT, fill="both", expand=True)
        tk.Label(
            left,
            text=f'Артикул заказа: {row["order_items_text"]}',
            bg=surface,
            fg=TEXT_PRIMARY,
            font=FONT_UI_TITLE,
            anchor="w",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(
            left,
            text=f'Статус заказа: {row["status_name"]}',
            bg=surface,
            fg=TEXT_PRIMARY,
            font=FONT_UI,
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 4))
        tk.Label(
            left,
            text=f'Адрес пункта выдачи: {row["address"]}',
            bg=surface,
            fg=TEXT_PRIMARY,
            font=FONT_UI,
            anchor="w",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 4))
        tk.Label(
            left,
            text=f'Дата заказа: {row["order_date"]}',
            bg=surface,
            fg=TEXT_PRIMARY,
            font=FONT_UI,
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 4))
        tk.Label(
            left,
            text=f'Клиент: {row["full_name"]}   ·   Код: {row["pickup_code"]}',
            bg=surface,
            fg=TEXT_SECONDARY,
            font=FONT_UI_SM,
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        right = tk.Frame(inner, bg=SECONDARY_BG, width=200, highlightbackground=CARD_BORDER, highlightthickness=1)
        right.pack(side=tk.RIGHT, fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="Дата доставки", bg=SECONDARY_BG, fg=TEXT_SECONDARY, font=FONT_UI_SM).pack(pady=(16, 6))
        tk.Label(right, text=str(row["delivery_date"]), bg=SECONDARY_BG, fg=TEXT_PRIMARY, font=FONT_UI_TITLE).pack(pady=(0, 16))

        self._bind_order_clicks(card, oid)
        return card

    def _bind_order_clicks(self, root: tk.Widget, order_id: int) -> None:
        def on_click(_e: tk.Event) -> None:
            self.select_order(order_id)

        def on_double(_e: tk.Event) -> None:
            if self.app.session.can_manage_orders:
                self.open_order_form(order_id)

        def walk(w: tk.Widget) -> None:
            w.bind("<Button-1>", on_click)
            w.bind("<Double-Button-1>", on_double)
            for ch in w.winfo_children():
                walk(ch)

        walk(root)

    def select_order(self, order_id: int) -> None:
        if self.selected_order_id == order_id:
            return
        old = self.selected_order_id
        self.selected_order_id = order_id
        if old is not None and old in self._order_card_by_id:
            self._set_order_selected(self._order_card_by_id[old], False)
        if order_id in self._order_card_by_id:
            self._set_order_selected(self._order_card_by_id[order_id], True)

    def open_selected_order(self) -> None:
        if self.selected_order_id is None:
            messagebox.showinfo("Информация", "Сначала выберите заказ.")
            return
        self.open_order_form(self.selected_order_id)

    def open_order_form(self, order_id: int | None) -> None:
        # Одно окно заказа на приложение (ограничение ТЗ модуля 3)
        existing = ACTIVE_WINDOWS["order"]
        if existing and existing.winfo_exists():
            existing.focus_set()
            return
        ACTIVE_WINDOWS["order"] = OrderForm(self.app, self, order_id)

    def delete_selected_order(self) -> None:
        if self.selected_order_id is None:
            messagebox.showinfo("Информация", "Сначала выберите заказ.")
            return
        order_id = self.selected_order_id
        if not messagebox.askyesno("Подтверждение", f"Удалить заказ №{order_id}?"):
            return
        delete_order(order_id)
        self.selected_order_id = None
        self.refresh_orders()


class OrderForm(tk.Toplevel):
    def __init__(self, app: ShoeStoreApp, owner: OrderListPage, order_id: int | None):
        super().__init__(app)
        self.app = app
        self.owner = owner
        self.order_id = order_id
        self.title("ООО «Обувь» — Добавление / редактирование заказа")
        self.geometry("920x760")
        self.configure(bg=WHITE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        customers = list_customers()
        pickup_points = list_pickup_points()
        statuses_full = list_statuses_full()
        products = list_products_short()

        self.customer_map = {item["full_name"]: item["user_id"] for item in customers}
        self.pickup_map = {f'{item["pickup_point_id"]}: {item["address"]}': item["pickup_point_id"] for item in pickup_points}
        self.status_map = {item["status_name"]: item["status_id"] for item in statuses_full}
        self.product_map = {f'{item["article"]} — {item["product_name"]}': item["product_id"] for item in products}
        self.product_display_to_article = {f'{item["article"]} — {item["product_name"]}': item["article"] for item in products}
        self.products_by_id = {item["product_id"]: f'{item["article"]} — {item["product_name"]}' for item in products}

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        self.order_id_var = tk.StringVar(value=str(order_id if order_id else next_order_id()))
        self.customer_var = tk.StringVar()
        self.pickup_var = tk.StringVar()
        self.order_date_var = tk.StringVar()
        self.delivery_date_var = tk.StringVar()
        self.code_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._add_entry(body, "Номер заказа", self.order_id_var, 0, readonly=True)
        self._add_combo(body, "ФИО клиента", self.customer_var, list(self.customer_map.keys()), 1)
        self._add_combo(body, "Пункт выдачи", self.pickup_var, list(self.pickup_map.keys()), 2, width=60)
        self._add_entry(body, "Дата заказа", self.order_date_var, 3)
        self._add_entry(body, "Дата доставки", self.delivery_date_var, 4)
        self._add_entry(body, "Код для получения", self.code_var, 5)
        self._add_combo(body, "Статус заказа", self.status_var, list(self.status_map.keys()), 6)

        items_frame = ttk.LabelFrame(body, text="Состав заказа", padding=10)
        items_frame.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        self.item_product_var = tk.StringVar()
        self.item_qty_var = tk.StringVar(value="1")
        ttk.Combobox(items_frame, textvariable=self.item_product_var, values=list(self.product_map.keys()), width=48, state="readonly").grid(row=0, column=0, padx=4, pady=4)
        ttk.Entry(items_frame, textvariable=self.item_qty_var, width=8).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(items_frame, text="Добавить позицию", command=self.add_item).grid(row=0, column=2, padx=4, pady=4)

        self.items_tree = ttk.Treeview(items_frame, columns=("article", "qty"), show="headings", height=10)
        self.items_tree.heading("article", text="Товар")
        self.items_tree.heading("qty", text="Количество")
        self.items_tree.column("article", width=520)
        self.items_tree.column("qty", width=100, anchor="center")
        self.items_tree.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        ttk.Button(items_frame, text="Удалить позицию", command=self.remove_selected_item).grid(row=2, column=0, sticky="w", pady=(8, 0))
        items_frame.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Сохранить", style="Accent.TButton", command=self.save).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Отмена", command=self.close_window).pack(side="left")

        if order_id is not None:
            self.load_order()

    def _add_entry(self, parent, label_text: str, variable: tk.StringVar, row: int, readonly: bool = False) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=4, pady=6)
        state = "readonly" if readonly else "normal"
        ttk.Entry(parent, textvariable=variable, width=54, state=state).grid(row=row, column=1, sticky="ew", padx=4, pady=6)

    def _add_combo(self, parent, label_text: str, variable: tk.StringVar, values: list[str], row: int, width: int = 52) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=4, pady=6)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width).grid(row=row, column=1, sticky="ew", padx=4, pady=6)

    def add_item(self) -> None:
        if not self.item_product_var.get():
            messagebox.showwarning("Предупреждение", "Выберите товар.")
            return
        try:
            qty = int(self.item_qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Количество должно быть положительным целым числом.")
            return
        key = self.item_product_var.get()
        self.items_tree.insert("", "end", values=(key, qty))
        self.item_qty_var.set("1")

    def remove_selected_item(self) -> None:
        selected = self.items_tree.selection()
        if not selected:
            return
        self.items_tree.delete(selected[0])

    def load_order(self) -> None:
        order = get_order(self.order_id)
        if not order:
            messagebox.showerror("Ошибка", "Заказ не найден.")
            self.close_window()
            return
        customers = list_customers()
        customer_name = next((row["full_name"] for row in customers if row["user_id"] == order["customer_id"]), "")
        points = list_pickup_points()
        point_value = next((f'{row["pickup_point_id"]}: {row["address"]}' for row in points if row["pickup_point_id"] == order["pickup_point_id"]), "")

        status_row = query_one("SELECT status_name FROM order_statuses WHERE status_id = ?", [order["status_id"]])
        status_name = status_row["status_name"]

        self.customer_var.set(customer_name)
        self.pickup_var.set(point_value)
        self.order_date_var.set(order["order_date"])
        self.delivery_date_var.set(order["delivery_date"])
        self.code_var.set(order["pickup_code"])
        self.status_var.set(status_name)

        for item in get_order_items(self.order_id):
            product_text = self.products_by_id.get(item["product_id"], f'{item["article"]}')
            self.items_tree.insert("", "end", values=(product_text, item["quantity"]))

    def validate(self) -> bool:
        required = [self.customer_var.get(), self.pickup_var.get(), self.order_date_var.get(), self.delivery_date_var.get(), self.code_var.get(), self.status_var.get()]
        if any(not value.strip() for value in required):
            messagebox.showwarning("Предупреждение", "Заполните все обязательные поля заказа.")
            return False
        if not self.items_tree.get_children():
            messagebox.showwarning("Предупреждение", "Добавьте хотя бы один товар в заказ.")
            return False
        return True

    def collect_items(self) -> list[tuple[int, int]]:
        items: list[tuple[int, int]] = []
        for row_id in self.items_tree.get_children():
            product_text, qty = self.items_tree.item(row_id, "values")
            items.append((self.product_map[product_text], int(qty)))
        return items

    def save(self) -> None:
        if not self.validate():
            return
        payload = {
            "order_id": int(self.order_id_var.get()),
            "customer_id": self.customer_map[self.customer_var.get()],
            "pickup_point_id": self.pickup_map[self.pickup_var.get()],
            "order_date": self.order_date_var.get().strip(),
            "delivery_date": self.delivery_date_var.get().strip(),
            "pickup_code": self.code_var.get().strip(),
            "status_id": self.status_map[self.status_var.get()],
        }
        items = self.collect_items()
        try:
            if self.order_id is None:
                insert_order(payload, items)
            else:
                update_order(self.order_id, payload, items)
        except Exception as error:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить заказ:\n{error}")
            return
        self.owner.refresh_orders()
        self.close_window()

    def close_window(self) -> None:
        ACTIVE_WINDOWS["order"] = None
        self.destroy()


def ensure_data() -> None:
    """При старте: создать БД при отсутствии/пустоте или пересобрать, если нет пользователей/товаров."""

    def _fail(message: str, exc: BaseException) -> None:
        traceback.print_exc()
        root = tk.Tk()
        root.withdraw()
        try:
            messagebox.showerror(
                "Ошибка базы данных",
                f"{message}\n\n{exc}\n\nПроверьте папку input (Excel-файлы задания) и запустите вручную:\n"
                "  cd src\n  python importer.py",
            )
        finally:
            root.destroy()

    db_path = BASE_DIR / "data" / "shoe_store.db"
    try:
        if not db_path.exists() or db_path.stat().st_size == 0:
            build_database()
            return
        initialize_database()

        row = query_one("SELECT COUNT(*) AS cnt FROM users")
        if not row or int(row["cnt"]) == 0:
            build_database()
            return

        row = query_one("SELECT COUNT(*) AS cnt FROM products")
        if not row or int(row["cnt"]) == 0:
            build_database()
    except Exception as exc:
        _fail("Не удалось создать или заполнить базу данных.", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    ensure_data()
    app = ShoeStoreApp()
    app.mainloop()

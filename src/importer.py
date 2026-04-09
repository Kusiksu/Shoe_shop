
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image

from db import DB_PATH, execute, initialize_database, query_one
from repositories import ensure_lookup

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
RESOURCES_DIR = BASE_DIR / "resources"
PRODUCT_IMAGES_DIR = RESOURCES_DIR / "products"
PLACEHOLDER_PATH = RESOURCES_DIR / "picture.png"


def _classify_excel(path: Path) -> str | None:
    """Определить тип файла по структуре (имя на диске может отличаться из‑за кодировки).

    Нужно, чтобы импорт находил «Заказ_import», «Пункты выдачи» и т.д. даже при «битых» именах в архиве.
    """
    try:
        raw = pd.read_excel(path, header=None, nrows=4)
        if raw.shape[1] == 1:
            return "pickup"
    except Exception:
        pass
    try:
        head = pd.read_excel(path, header=0, nrows=1)
        cols = [str(c).strip() for c in head.columns]
        if "Артикул" in cols and "Наименование товара" in cols:
            return "tovar"
        if "Логин" in cols and "ФИО" in cols:
            return "users"
        if "Номер заказа" in cols:
            return "orders"
    except Exception:
        pass
    return None


def resolve_input_excel(kind: str) -> Path:
    """kind: tovar | users | orders | pickup"""
    exact: dict[str, tuple[str, ...]] = {
        "tovar": ("Tovar.xlsx",),
        "users": ("user_import.xlsx",),
        "orders": ("Заказ_import.xlsx",),
        "pickup": ("Пункты выдачи_import.xlsx",),
    }
    for name in exact[kind]:
        path = INPUT_DIR / name
        if path.exists():
            return path
    matches: list[Path] = []
    for path in sorted(INPUT_DIR.glob("*.xlsx")):
        if _classify_excel(path) == kind:
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise FileNotFoundError(
            f"В папке input найдено несколько файлов типа «{kind}»: "
            + ", ".join(p.name for p in matches)
        )
    raise FileNotFoundError(
        f"Не найден Excel для импорта ({kind}) в {INPUT_DIR}. "
        "Ожидаются исходные файлы задания (Tovar, user_import, Заказ, Пункты выдачи)."
    )


def reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    initialize_database()


def seed_roles() -> None:
    rows = [
        ("Гость", 0, 0, 0, 0),
        ("Авторизированный клиент", 0, 0, 0, 0),
        ("Менеджер", 1, 0, 1, 0),
        ("Администратор", 1, 1, 1, 1),
    ]
    for role_name, can_search, can_manage_products, can_view_orders, can_manage_orders in rows:
        execute(
            """
            INSERT OR IGNORE INTO roles (
                role_name, can_search, can_manage_products, can_view_orders, can_manage_orders
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [role_name, can_search, can_manage_products, can_view_orders, can_manage_orders],
        )

    for status_name in ["Новый", "Завершен", "В обработке", "Готов к выдаче", "Отменен"]:
        execute("INSERT OR IGNORE INTO order_statuses (status_name) VALUES (?)", [status_name])


def normalize_role(role_name: str) -> str:
    role_name = str(role_name).strip()
    if role_name == "Авторизированный клиент":
        return "Авторизированный клиент"
    return role_name


def safe_text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def prepare_product_image(filename: str) -> str:
    source = PRODUCT_IMAGES_DIR / filename
    if not filename or not source.exists():
        return str(PLACEHOLDER_PATH.relative_to(BASE_DIR)).replace("\\", "/")
    target_name = f"resized_{filename}"
    target = PRODUCT_IMAGES_DIR / target_name
    image = Image.open(source).convert("RGB")
    image.thumbnail((300, 200))
    canvas = Image.new("RGB", (300, 200), (240, 240, 240))
    x = (300 - image.width) // 2
    y = (200 - image.height) // 2
    canvas.paste(image, (x, y))
    canvas.save(target)
    return str(target.relative_to(BASE_DIR)).replace("\\", "/")


def import_users() -> None:
    frame = pd.read_excel(resolve_input_excel("users"))
    role_ids = {
        row["role_name"]: row["role_id"]
        for row in query_all_local("SELECT role_id, role_name FROM roles")
    }
    for _, row in frame.iterrows():
        execute(
            """
            INSERT INTO users (full_name, login, password, role_id)
            VALUES (?, ?, ?, ?)
            """,
            [
                safe_text(row["ФИО"]),
                safe_text(row["Логин"]),
                safe_text(row["Пароль"]),
                role_ids[normalize_role(row["Роль сотрудника"])],
            ],
        )


def query_all_local(sql: str, params: list[Any] | None = None):
    from db import query_all
    return query_all(sql, params or [])


def import_pickup_points() -> None:
    frame = pd.read_excel(resolve_input_excel("pickup"), header=None)
    for index, row in frame.iterrows():
        execute(
            "INSERT INTO pickup_points (pickup_point_id, address) VALUES (?, ?)",
            [index + 1, safe_text(row.iloc[0])],
        )


def import_products() -> None:
    frame = pd.read_excel(resolve_input_excel("tovar"))
    for _, row in frame.iterrows():
        category_id = ensure_lookup("categories", "category_name", safe_text(row["Категория товара"]))
        manufacturer_id = ensure_lookup("manufacturers", "manufacturer_name", safe_text(row["Производитель"]))
        supplier_id = ensure_lookup("suppliers", "supplier_name", safe_text(row["Поставщик"]))
        unit_id = ensure_lookup("units", "unit_name", safe_text(row["Единица измерения"]))
        execute(
            """
            INSERT INTO products (
                article, product_name, unit_id, price, supplier_id, manufacturer_id, category_id,
                discount_percent, stock_quantity, description, image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                safe_text(row["Артикул"]),
                safe_text(row["Наименование товара"]),
                unit_id,
                float(row["Цена"]),
                supplier_id,
                manufacturer_id,
                category_id,
                int(row["Действующая скидка"]),
                int(row["Кол-во на складе"]),
                safe_text(row["Описание товара"]),
                prepare_product_image(safe_text(row["Фото"])),
            ],
        )


def parse_order_items(order_items_text: str) -> list[tuple[str, int]]:
    parts = [part.strip() for part in order_items_text.split(",")]
    items: list[tuple[str, int]] = []
    for index in range(0, len(parts), 2):
        article = parts[index]
        quantity = int(parts[index + 1])
        items.append((article, quantity))
    return items


def import_orders() -> None:
    frame = pd.read_excel(resolve_input_excel("orders"))
    customer_map = {
        row["full_name"]: row["user_id"]
        for row in query_all_local("SELECT user_id, full_name FROM users")
    }
    status_map = {
        row["status_name"]: row["status_id"]
        for row in query_all_local("SELECT status_id, status_name FROM order_statuses")
    }
    product_map = {
        row["article"]: row["product_id"]
        for row in query_all_local("SELECT product_id, article FROM products")
    }
    for _, row in frame.iterrows():
        order_id = int(row["Номер заказа"])
        execute(
            """
            INSERT INTO orders (
                order_id, customer_id, pickup_point_id, order_date, delivery_date, pickup_code, status_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                order_id,
                customer_map[safe_text(row["ФИО авторизированного клиента"])],
                int(row["Адрес пункта выдачи"]),
                safe_text(row["Дата заказа"]),
                safe_text(row["Дата доставки"]),
                safe_text(row["Код для получения"]),
                status_map[safe_text(row["Статус заказа"])],
            ],
        )
        for article, quantity in parse_order_items(safe_text(row["Артикул заказа"])):
            execute(
                "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                [order_id, product_map[article], quantity],
            )


def build_database() -> None:
    reset_database()
    seed_roles()
    import_users()
    import_pickup_points()
    import_products()
    import_orders()


if __name__ == "__main__":
    build_database()
    print(f"База данных сформирована: {DB_PATH}")

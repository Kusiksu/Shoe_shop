
from __future__ import annotations

from typing import Any

from db import execute, query_all, query_one


ROLE_NAME_MAP = {
    "Гость": "Гость",
    "Авторизированный клиент": "Авторизированный клиент",
    "Клиент": "Авторизированный клиент",
    "Менеджер": "Менеджер",
    "Администратор": "Администратор",
}


def ensure_lookup(table_name: str, column_name: str, value: str) -> int:
    """Возвращает id справочника; при отсутствии значения — вставляет строку (используется при сохранении форм)."""
    value = value.strip()
    row = query_one(
        f"SELECT rowid AS id, {column_name} FROM {table_name} WHERE {column_name} = ?",
        [value],
    )
    if row:
        return int(row["id"])
    return execute(
        f"INSERT INTO {table_name} ({column_name}) VALUES (?)",
        [value],
    )


def get_permissions(role_name: str) -> dict[str, Any]:
    role = query_one("SELECT * FROM roles WHERE role_name = ?", [ROLE_NAME_MAP.get(role_name, role_name)])
    return dict(role) if role else {}


def get_user_by_credentials(login: str, password: str):
    return query_one(
        """
        SELECT users.*, roles.role_name, roles.can_search, roles.can_manage_products,
               roles.can_view_orders, roles.can_manage_orders
        FROM users
        JOIN roles ON roles.role_id = users.role_id
        WHERE users.login = ? AND users.password = ?
        """,
        [login, password],
    )


def list_categories() -> list[str]:
    return [row["category_name"] for row in query_all("SELECT category_name FROM categories ORDER BY category_name")]


def list_suppliers() -> list[str]:
    return [row["supplier_name"] for row in query_all("SELECT supplier_name FROM suppliers ORDER BY supplier_name")]


def list_manufacturers() -> list[str]:
    return [row["manufacturer_name"] for row in query_all("SELECT manufacturer_name FROM manufacturers ORDER BY manufacturer_name")]


def list_units() -> list[str]:
    return [row["unit_name"] for row in query_all("SELECT unit_name FROM units ORDER BY unit_name")]


def list_pickup_points() -> list[dict[str, Any]]:
    return [dict(row) for row in query_all("SELECT pickup_point_id, address FROM pickup_points ORDER BY pickup_point_id")]


def list_statuses() -> list[str]:
    return [row["status_name"] for row in query_all("SELECT status_name FROM order_statuses ORDER BY status_id")]


def list_statuses_full() -> list[dict[str, Any]]:
    return [dict(row) for row in query_all("SELECT status_id, status_name FROM order_statuses ORDER BY status_id")]


def list_customers() -> list[dict[str, Any]]:
    return [
        dict(row) for row in query_all(
            """
            SELECT users.user_id, users.full_name, roles.role_name
            FROM users
            JOIN roles ON roles.role_id = users.role_id
            WHERE roles.role_name <> 'Гость'
            ORDER BY users.full_name
            """
        )
    ]


def next_product_id() -> int:
    row = query_one("SELECT COALESCE(MAX(product_id), 0) + 1 AS next_id FROM products")
    return int(row["next_id"])


def get_products(search_text: str = "", supplier_name: str = "Все поставщики", stock_sort: str = "Без сортировки") -> list[dict[str, Any]]:
    """Каталог: поиск по нескольким текстовым полям, фильтр по поставщику, сортировка по остатку (модуль 3)."""
    sql = """
        SELECT products.product_id, products.article, products.product_name, products.price,
               products.discount_percent, products.stock_quantity, products.description,
               products.image_path, categories.category_name, manufacturers.manufacturer_name,
               suppliers.supplier_name, units.unit_name
        FROM products
        JOIN categories ON categories.category_id = products.category_id
        JOIN manufacturers ON manufacturers.manufacturer_id = products.manufacturer_id
        JOIN suppliers ON suppliers.supplier_id = products.supplier_id
        JOIN units ON units.unit_id = products.unit_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if supplier_name and supplier_name != "Все поставщики":
        sql += " AND suppliers.supplier_name = ?"
        params.append(supplier_name)
    if search_text:
        like = f"%{search_text.strip()}%"
        sql += """
            AND (
                products.article LIKE ?
                OR products.product_name LIKE ?
                OR products.description LIKE ?
                OR categories.category_name LIKE ?
                OR manufacturers.manufacturer_name LIKE ?
                OR suppliers.supplier_name LIKE ?
                OR units.unit_name LIKE ?
            )
        """
        params.extend([like] * 7)
    if stock_sort == "По количеству ↑":
        sql += " ORDER BY products.stock_quantity ASC, products.product_name"
    elif stock_sort == "По количеству ↓":
        sql += " ORDER BY products.stock_quantity DESC, products.product_name"
    else:
        sql += " ORDER BY products.product_id"
    rows = query_all(sql, params)
    result = []
    for row in rows:
        item = dict(row)
        item["final_price"] = round(item["price"] * (100 - item["discount_percent"]) / 100, 2)
        result.append(item)
    return result


def get_product(product_id: int) -> dict[str, Any] | None:
    row = query_one(
        """
        SELECT products.*, categories.category_name, manufacturers.manufacturer_name,
               suppliers.supplier_name, units.unit_name
        FROM products
        JOIN categories ON categories.category_id = products.category_id
        JOIN manufacturers ON manufacturers.manufacturer_id = products.manufacturer_id
        JOIN suppliers ON suppliers.supplier_id = products.supplier_id
        JOIN units ON units.unit_id = products.unit_id
        WHERE products.product_id = ?
        """,
        [product_id],
    )
    return dict(row) if row else None


def insert_product(payload: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO products (
            article, product_name, unit_id, price, supplier_id, manufacturer_id, category_id,
            discount_percent, stock_quantity, description, image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            payload["article"], payload["product_name"], payload["unit_id"], payload["price"], payload["supplier_id"],
            payload["manufacturer_id"], payload["category_id"], payload["discount_percent"], payload["stock_quantity"],
            payload["description"], payload["image_path"],
        ],
    )


def update_product(product_id: int, payload: dict[str, Any]) -> None:
    execute(
        """
        UPDATE products
        SET article = ?, product_name = ?, unit_id = ?, price = ?, supplier_id = ?,
            manufacturer_id = ?, category_id = ?, discount_percent = ?, stock_quantity = ?,
            description = ?, image_path = ?
        WHERE product_id = ?
        """,
        [
            payload["article"], payload["product_name"], payload["unit_id"], payload["price"], payload["supplier_id"],
            payload["manufacturer_id"], payload["category_id"], payload["discount_percent"], payload["stock_quantity"],
            payload["description"], payload["image_path"], product_id,
        ],
    )


def product_is_used_in_orders(product_id: int) -> bool:
    row = query_one("SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", [product_id])
    return row is not None


def delete_product(product_id: int) -> None:
    execute("DELETE FROM products WHERE product_id = ?", [product_id])


def get_orders() -> list[dict[str, Any]]:
    rows = query_all(
        """
        SELECT orders.order_id, orders.order_date, orders.delivery_date, orders.pickup_code,
               pickup_points.address, order_statuses.status_name, users.full_name
        FROM orders
        JOIN pickup_points ON pickup_points.pickup_point_id = orders.pickup_point_id
        JOIN order_statuses ON order_statuses.status_id = orders.status_id
        JOIN users ON users.user_id = orders.customer_id
        ORDER BY orders.order_id
        """
    )
    result = []
    for row in rows:
        item = dict(row)
        items = query_all(
            """
            SELECT products.article, products.product_name, order_items.quantity
            FROM order_items
            JOIN products ON products.product_id = order_items.product_id
            WHERE order_items.order_id = ?
            ORDER BY products.article
            """,
            [item["order_id"]],
        )
        item["order_items_text"] = ", ".join(f'{r["article"]}, {r["quantity"]}' for r in items)
        result.append(item)
    return result


def get_order(order_id: int) -> dict[str, Any] | None:
    row = query_one("SELECT * FROM orders WHERE order_id = ?", [order_id])
    return dict(row) if row else None


def get_order_items(order_id: int) -> list[dict[str, Any]]:
    return [dict(row) for row in query_all(
        """
        SELECT order_items.order_item_id, order_items.product_id, order_items.quantity,
               products.article, products.product_name
        FROM order_items
        JOIN products ON products.product_id = order_items.product_id
        WHERE order_items.order_id = ?
        ORDER BY products.article
        """,
        [order_id],
    )]


def next_order_id() -> int:
    row = query_one("SELECT COALESCE(MAX(order_id), 0) + 1 AS next_id FROM orders")
    return int(row["next_id"])


def list_products_short() -> list[dict[str, Any]]:
    return [dict(row) for row in query_all(
        "SELECT product_id, article, product_name FROM products ORDER BY article"
    )]


def insert_order(payload: dict[str, Any], items: list[tuple[int, int]]) -> None:
    execute(
        """
        INSERT INTO orders (order_id, customer_id, pickup_point_id, order_date, delivery_date, pickup_code, status_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            payload["order_id"], payload["customer_id"], payload["pickup_point_id"],
            payload["order_date"], payload["delivery_date"], payload["pickup_code"], payload["status_id"],
        ],
    )
    for product_id, quantity in items:
        execute(
            "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
            [payload["order_id"], product_id, quantity],
        )


def update_order(order_id: int, payload: dict[str, Any], items: list[tuple[int, int]]) -> None:
    execute(
        """
        UPDATE orders
        SET customer_id = ?, pickup_point_id = ?, order_date = ?, delivery_date = ?, pickup_code = ?, status_id = ?
        WHERE order_id = ?
        """,
        [
            payload["customer_id"], payload["pickup_point_id"], payload["order_date"],
            payload["delivery_date"], payload["pickup_code"], payload["status_id"], order_id,
        ],
    )
    execute("DELETE FROM order_items WHERE order_id = ?", [order_id])
    for product_id, quantity in items:
        execute(
            "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
            [order_id, product_id, quantity],
        )


def delete_order(order_id: int) -> None:
    execute("DELETE FROM orders WHERE order_id = ?", [order_id])

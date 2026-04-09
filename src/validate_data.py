
from __future__ import annotations

from db import query_one, query_all


def main() -> None:
    print("Проверка базы данных")
    checks = {
        "roles": 4,
        "users": 10,
        "pickup_points": 36,
        "products": 30,
        "orders": 10,
        "order_items": 20,
    }
    ok = True
    for table_name, expected in checks.items():
        row = query_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")
        actual = int(row["cnt"])
        status = "OK" if actual == expected else "FAIL"
        print(f"{table_name}: {actual} / ожидается {expected} -> {status}")
        ok &= actual == expected

    product = query_one("SELECT article, product_name, discount_percent, stock_quantity FROM products WHERE article = 'А112Т4'")
    print("Контрольный товар:", dict(product) if product else "не найден")

    order = query_one(
        """
        SELECT orders.order_id, users.full_name, order_statuses.status_name
        FROM orders
        JOIN users ON users.user_id = orders.customer_id
        JOIN order_statuses ON order_statuses.status_id = orders.status_id
        WHERE orders.order_id = 1
        """
    )
    print("Контрольный заказ:", dict(order) if order else "не найден")
    print("Итог:", "Проверка пройдена" if ok else "Есть расхождения")


if __name__ == "__main__":
    main()

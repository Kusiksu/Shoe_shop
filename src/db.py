
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "shoe_store.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = get_connection()
    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def execute(statement: str, parameters: list[Any] | tuple[Any, ...] | None = None) -> int:
    connection = get_connection()
    try:
        cursor = connection.execute(statement, parameters or [])
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def execute_many(statement: str, rows: list[tuple[Any, ...]]) -> None:
    connection = get_connection()
    try:
        connection.executemany(statement, rows)
        connection.commit()
    finally:
        connection.close()


def query_all(statement: str, parameters: list[Any] | tuple[Any, ...] | None = None) -> list[sqlite3.Row]:
    connection = get_connection()
    try:
        return list(connection.execute(statement, parameters or []))
    finally:
        connection.close()


def query_one(statement: str, parameters: list[Any] | tuple[Any, ...] | None = None) -> sqlite3.Row | None:
    connection = get_connection()
    try:
        return connection.execute(statement, parameters or []).fetchone()
    finally:
        connection.close()

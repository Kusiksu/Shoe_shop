# Учебный проект "ООО Обувь"

[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=Kusiksu_Shoe_shop&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Kusiksu_Shoe_shop)
[![Maintainability](https://sonarcloud.io/api/project_badges/measure?project=Kusiksu_Shoe_shop&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Kusiksu_Shoe_shop)

## Что сделано
- база данных SQLite в 3НФ;
- импорт данных из файлов:
  - `input/Tovar.xlsx`
  - `input/user_import.xlsx`
  - `input/Заказ_import.xlsx`
  - `input/Пункты выдачи_import.xlsx`
- приложение на Python + Tkinter;

- роли:
  - гость
  - авторизированный клиент
  - менеджер
  - администратор

- для гостя и клиента:
- авторизация по данным из Excel;
- список товаров с фото, скидкой, остатком и описанием;
- подсветка карточек:
  - скидка > 15% — фон `#2E8B57` (имеет приоритет над остальными правилами);
  - нет товара на складе — фон `#87CEFA`;
  - при наличии скидки старая цена зачёркнута и красная, рядом цена со скидкой;
- экран входа: белый фон (рамки формы без лаймового фона);
- для менеджера:
  - поиск
  - фильтрация по поставщику
  - сортировка по количеству на складе
- для администратора:
  - добавление / редактирование / удаление товаров (редактирование — **щелчок по карточке товара** или кнопка «Редактировать выбранный»);
  - добавление / редактирование / удаление заказов
- отдельные формы редактирования;
- ограничение: одновременно открывается только одно окно редактирования товара и одно окно редактирования заказа;

- `schema.sql`;
- `docs/ER_diagram.pdf`;
- `docs/algorithm_flowchart.pdf`.

## Сверка с исходными Excel
Проверка после импорта:
- users: 10
- products: 30
- pickup_points: 36
- orders: 10
- order_items: 20

Запустить проверку:
```bash
cd src
python validate_data.py
```

## Линтер (статический анализ)

В проекте настроен **[Ruff](https://docs.astral.sh/ruff/)** (стиль, неиспользуемые импорты, типичные ошибки). Конфигурация — в `pyproject.toml`.

Установка инструментов разработки и проверка:

```bash
pip install -r requirements-dev.txt
python -m ruff check src
```

Автоисправление части замечаний: `python -m ruff check src --fix`.

Проверка также запускается в GitHub Actions (файл `.github/workflows/lint.yml`) при push/PR в ветки `main` или `master`.

## SonarCloud

Проект на [SonarCloud](https://sonarcloud.io/) (ключ `Kusiksu_Shoe_shop`, организация `kusiksu`). Бейджи в начале README указывают на этот проект.

## Рефакторинг (выполненный в рамках настройки качества)

- Удалены неиспользуемые импорты и лишняя переменная в форме заказа.
- Установка иконки окна: вместо `try` / `except` / `pass` используется `contextlib.suppress(Exception)` — явнее намерение и проще разбор линтером.
- Загрузка заказа в форму: убраны лишние списки статусов; имя статуса берётся одним запросом; `query_one` импортируется из `db` (как и остальной доступ к БД).

## Запуск
```bash
pip install -r requirements.txt
cd src
python importer.py
python app.py
```

Или в Windows:
```bash
run.bat
```

## Учётные записи для входа
Примеры из файла `user_import.xlsx`:
- Администратор: `94d5ous@gmail.com / uzWC67`
- Менеджер: `1diph5e@tutanota.com / 8ntwUp`
- Клиент: `5d4zbu@tutanota.com / rwVDh9`

## Структура проекта
- `pyproject.toml` — метаданные проекта и настройки **Ruff**
- `requirements-dev.txt` — зависимости для разработки (линтер)
- `.github/workflows/lint.yml` — CI: проверка `ruff` на GitHub
- `src/app.py` — главное приложение
- `src/ui_helpers.py` — стили интерфейса (Приложение 3), загрузка изображений
- `src/importer.py` — создание и заполнение БД из Excel
- `src/repositories.py` — запросы к БД
- `src/validate_data.py` — сверка данных
- `schema.sql` — скрипт базы данных
- `data/shoe_store.db` — готовая БД
- `resources/` — иконка, заглушка, изображения товаров
- `input/` — исходные файлы задания
- `docs/` — PDF-документы

## Замечание по данным
В исходном файле заказов есть дата `30.02.2025`, то есть заведомо невалидная календарная дата. В проекте она импортируется как текст, чтобы полностью сохранить соответствие исходным данным Excel.

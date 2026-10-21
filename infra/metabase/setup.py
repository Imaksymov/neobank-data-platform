"""Провижининг Metabase: первичная настройка, подключение БД, дашборд.

Зачем скриптом, а не кликами: H2-база Metabase живёт в томе, и после
`docker compose down -v` настройка исчезает вместе с ней. Скрипт делает
её воспроизводимой — как и остальная инфраструктура.

Идемпотентен: повторный запуск находит уже созданные объекты по имени
и не плодит дубли.

Запросы карточек лежат в cards/*.sql отдельными файлами, а не строками
здесь, чтобы их проверял sqlfluff: цифры на дашборде — это SQL, который
должен ревьюиться как код.
"""

import os
import sys
from pathlib import Path
from typing import Any, Final

import httpx

CARDS_DIR: Final[Path] = Path(__file__).parent / "cards"
DB_NAME: Final[str] = "NeoBank (berka)"
DASHBOARD_NAME: Final[str] = "NeoBank — обзор портфеля"

# Карточки: файл запроса, подпись, тип визуализации, место на сетке
# (сетка Metabase — 24 колонки) и настройки осей для графиков.
CARDS: Final[list[dict[str, Any]]] = [
    {
        "file": "portfolio_summary.sql",
        "name": "Портфель в цифрах",
        "display": "table",
        "layout": {"col": 0, "row": 0, "size_x": 24, "size_y": 3},
        "settings": {},
    },
    {
        "file": "transactions_monthly.sql",
        "name": "Операции и оборот по месяцам",
        "display": "line",
        "layout": {"col": 0, "row": 3, "size_x": 12, "size_y": 7},
        "settings": {
            "graph.dimensions": ["Месяц"],
            "graph.metrics": ["Операций"],
        },
    },
    {
        "file": "loans_by_status.sql",
        "name": "Кредиты по исходу",
        "display": "bar",
        "layout": {"col": 12, "row": 3, "size_x": 12, "size_y": 7},
        "settings": {
            "graph.dimensions": ["Статус"],
            "graph.metrics": ["Кредитов"],
        },
    },
    {
        "file": "clients_by_district.sql",
        "name": "Топ районов по числу клиентов",
        "display": "table",
        "layout": {"col": 0, "row": 10, "size_x": 24, "size_y": 7},
        "settings": {},
    },
]


class Metabase:
    """Минимальный клиент API Metabase на время провижининга."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def close(self) -> None:
        self.client.close()

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        payload: Any = response.json()
        if not isinstance(payload, dict):
            message = f"Ожидался объект, получено {type(payload).__name__}"
            raise TypeError(message)
        return payload

    def properties(self) -> dict[str, Any]:
        return self._json(self.client.get("/api/session/properties"))

    def setup(self, email: str, password: str, token: str) -> None:
        body = {
            "token": token,
            "user": {
                "first_name": "Admin",
                "last_name": "Local",
                "email": email,
                "password": password,
            },
            "prefs": {"site_name": "NeoBank Data Platform", "allow_tracking": False},
        }
        session = self._json(self.client.post("/api/setup", json=body))
        self._use_session(str(session["id"]))

    def login(self, email: str, password: str) -> None:
        body = {"username": email, "password": password}
        session = self._json(self.client.post("/api/session", json=body))
        self._use_session(str(session["id"]))

    def _use_session(self, session_id: str) -> None:
        self.client.headers["X-Metabase-Session"] = session_id

    def get_list(self, path: str) -> list[dict[str, Any]]:
        response = self.client.get(path)
        response.raise_for_status()
        payload: Any = response.json()
        if isinstance(payload, dict):
            payload = payload.get("data", [])
        if not isinstance(payload, list):
            message = f"Ожидался список, получено {type(payload).__name__}"
            raise TypeError(message)
        return [item for item in payload if isinstance(item, dict)]

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._json(self.client.post(path, json=body))

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._json(self.client.put(path, json=body))


def find_by_name(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("name") == name), None)


def ensure_database(mb: Metabase) -> int:
    """Подключение к Postgres ролью bi_readonly."""
    existing = find_by_name(mb.get_list("/api/database"), DB_NAME)
    if existing is not None:
        print(f"  база уже подключена, id={existing['id']}")
        return int(existing["id"])

    created = mb.post(
        "/api/database",
        {
            "name": DB_NAME,
            "engine": "postgres",
            "details": {
                "host": os.environ.get("METABASE_DB_HOST", "postgres"),
                "port": int(os.environ.get("POSTGRES_PORT", "5432")),
                "dbname": os.environ.get("POSTGRES_DB", "neobank"),
                "user": os.environ.get("BI_DB_USER", "bi_readonly"),
                "password": os.environ.get("BI_DB_PASSWORD", "bi_readonly_local_only"),
                "ssl": False,
            },
            "is_full_sync": True,
        },
    )
    print(f"  база подключена, id={created['id']}")
    return int(created["id"])


def ensure_cards(mb: Metabase, database_id: int) -> list[tuple[int, dict[str, Any]]]:
    existing = mb.get_list("/api/card")
    result: list[tuple[int, dict[str, Any]]] = []

    for spec in CARDS:
        name = str(spec["name"])
        found = find_by_name(existing, name)
        if found is not None:
            print(f"  карточка уже есть: {name}")
            result.append((int(found["id"]), spec))
            continue

        query = (CARDS_DIR / str(spec["file"])).read_text(encoding="utf-8")
        created = mb.post(
            "/api/card",
            {
                "name": name,
                "display": spec["display"],
                "visualization_settings": spec["settings"],
                "dataset_query": {
                    "database": database_id,
                    "type": "native",
                    "native": {"query": query},
                },
            },
        )
        print(f"  карточка создана: {name}")
        result.append((int(created["id"]), spec))

    return result


def ensure_dashboard(mb: Metabase, cards: list[tuple[int, dict[str, Any]]]) -> int:
    existing = find_by_name(mb.get_list("/api/dashboard"), DASHBOARD_NAME)
    if existing is not None:
        print(f"  дашборд уже есть, id={existing['id']}")
        return int(existing["id"])

    dashboard = mb.post("/api/dashboard", {"name": DASHBOARD_NAME})
    dashboard_id = int(dashboard["id"])

    # Отрицательные id — соглашение Metabase для ещё не созданных
    # размещений карточки на дашборде.
    dashcards = [
        {"id": -(index + 1), "card_id": card_id, **spec["layout"]}
        for index, (card_id, spec) in enumerate(cards)
    ]
    mb.put(f"/api/dashboard/{dashboard_id}", {"dashcards": dashcards})
    print(f"  дашборд создан, id={dashboard_id}, карточек: {len(dashcards)}")
    return dashboard_id


def main() -> int:
    base_url = os.environ.get("METABASE_URL", "http://localhost:3000")
    email = os.environ.get("METABASE_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("METABASE_ADMIN_PASSWORD", "neobank_local_2026")

    mb = Metabase(base_url)
    try:
        props = mb.properties()
        if props.get("has-user-setup"):
            print("Metabase уже настроен, вхожу")
            mb.login(email, password)
        else:
            token = props.get("setup-token")
            if not token:
                print("Нет setup-token и нет пользователя — состояние неясно", file=sys.stderr)
                return 1
            print("Первичная настройка Metabase")
            mb.setup(email, password, str(token))

        database_id = ensure_database(mb)
        cards = ensure_cards(mb, database_id)
        dashboard_id = ensure_dashboard(mb, cards)
    finally:
        mb.close()

    print(f"\nГотово: {base_url}/dashboard/{dashboard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

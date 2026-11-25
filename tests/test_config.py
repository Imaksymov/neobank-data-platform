"""Конфигурация загрузчика.

Тесты изолированы от окружения разработчика: переменные очищаются,
файл infra/.env отключается. Иначе тест проходил бы у одного и падал
у другого в зависимости от того, что лежит в его оболочке.
"""

import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import ValidationError

from ingestion.config import (
    LakeSettings,
    LoaderSettings,
    Settings,
    SourceDbSettings,
    load_settings,
)

_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "INGESTION_DB_USER",
    "INGESTION_DB_PASSWORD",
    "INGESTION_CHUNK_SIZE",
    "INGESTION_LOOKBACK_DAYS",
    "USER",
    "HOST",
    "PORT",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _VARS:
        monkeypatch.delenv(name, raising=False)


def source() -> SourceDbSettings:
    return SourceDbSettings(_env_file=None)


def loader() -> LoaderSettings:
    return LoaderSettings(_env_file=None)


def test_defaults_point_to_loader_role_not_superuser() -> None:
    s = source()
    assert s.user == "ingestion_loader"
    assert (s.host, s.port, s.dbname) == ("localhost", 5432, "neobank")


def test_loader_defaults() -> None:
    s = loader()
    assert (s.chunk_size, s.lookback_days) == (100_000, 2)


def test_shell_variables_do_not_hijack_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Регрессия AF-005.

    С populate_by_name=True pydantic-settings искал переменные и по имени
    поля без учёта регистра: USER=postgres давал подключение
    суперпользователем, HOST и PORT уводили загрузчик с паролем на чужой
    хост. Если этот тест упал — флаг вернули.
    """
    monkeypatch.setenv("USER", "postgres")
    monkeypatch.setenv("HOST", "evil.example.com")
    monkeypatch.setenv("PORT", "6543")

    s = source()

    assert s.user == "ingestion_loader"
    assert s.host == "localhost"
    assert s.port == 5432


def test_explicit_aliases_are_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGESTION_DB_USER", "custom_loader")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5433")

    s = source()

    assert (s.user, s.host, s.port) == ("custom_loader", "db.internal", 5433)


@pytest.mark.parametrize(
    ("var", "value"),
    [("INGESTION_CHUNK_SIZE", "0"), ("INGESTION_LOOKBACK_DAYS", "-1")],
    ids=["zero-chunk", "negative-lookback"],
)
def test_invalid_values_fail_at_startup(
    monkeypatch: pytest.MonkeyPatch, var: str, value: str
) -> None:
    # ошибка при старте, а не в середине загрузки
    monkeypatch.setenv(var, value)
    with pytest.raises(ValidationError):
        loader()


def test_password_does_not_leak_through_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGESTION_DB_PASSWORD", "hunter2")
    assert "hunter2" not in repr(source())


@pytest.mark.parametrize("password", ["p@ss/w:rd", "it's", "with space", r"back\slash"])
def test_conninfo_round_trips_dangerous_passwords(
    monkeypatch: pytest.MonkeyPatch, password: str
) -> None:
    # Разбираем строку обратно: экранирование может выглядеть правильным
    # и при этом не восстанавливать значение.
    monkeypatch.setenv("INGESTION_DB_PASSWORD", password)
    assert conninfo_to_dict(source().conninfo())["password"] == password


def test_settings_are_immutable() -> None:
    # mypy заморозку не видит: model_config ссылается на общую константу,
    # а её значение плагин pydantic статически не вычисляет. Константа
    # общая намеренно — там живёт предупреждение AF-005. Поэтому
    # неизменяемость гарантирует этот тест, а не проверка типов.
    s = loader()
    with pytest.raises(ValidationError):
        s.chunk_size = 1


def test_load_settings_assembles_all_groups() -> None:
    # Только структура, не значения: load_settings читает infra/.env, и
    # значения зависят от машины. Значения проверены тестами выше.
    s = load_settings()
    assert isinstance(s, Settings)
    assert isinstance(s.source, SourceDbSettings)
    assert isinstance(s.lake, LakeSettings)
    assert isinstance(s.loader, LoaderSettings)

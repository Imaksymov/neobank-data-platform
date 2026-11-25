"""Структурированное логирование.

structlog запоминает объект потока при настройке, поэтому
configure_logging вызывается внутри теста — когда capsys уже подменил
stderr, — а после теста конфигурация сбрасывается.
"""

import json
from collections.abc import Iterator
from typing import Any

import pytest
import structlog

from ingestion.log import bind_run, configure_logging, get_logger, new_run_id


@pytest.fixture(autouse=True)
def reset_structlog() -> Iterator[None]:
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def records(err: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in err.splitlines() if line.strip()]


def test_every_line_carries_run_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("json")
    run_id = new_run_id()
    bind_run(run_id, "berka")

    get_logger().info("run_started")

    (rec,) = records(capsys.readouterr().err)
    assert rec["run_id"] == str(run_id)
    assert rec["source"] == "berka"
    assert rec["level"] == "info"
    assert rec["timestamp"].endswith("Z"), "время должно быть в UTC"


def test_scoped_fields_disappear_after_scope(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("json")
    bind_run(new_run_id(), "berka")
    log = get_logger()

    with structlog.contextvars.bound_contextvars(table="trans", phase="extract"):
        log.info("inside")
    log.info("outside")

    inside, outside = records(capsys.readouterr().err)
    assert (inside["table"], inside["phase"]) == ("trans", "extract")
    assert "table" not in outside
    assert "phase" not in outside


@pytest.mark.parametrize("field", ["db_password", "conninfo", "secret_key", "api_token", "dsn"])
def test_secrets_are_masked(capsys: pytest.CaptureFixture[str], field: str) -> None:
    configure_logging("json")
    get_logger().info("connecting", **{field: "настоящий-секрет"})

    err = capsys.readouterr().err
    assert "настоящий-секрет" not in err
    assert records(err)[0][field] == "***"


def test_new_run_does_not_inherit_previous_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("json")
    log = get_logger()

    first = new_run_id()
    bind_run(first, "berka")
    structlog.contextvars.bind_contextvars(table="trans")
    log.info("first")

    second = new_run_id()
    bind_run(second, "nbu")
    log.info("second")

    _, rec = records(capsys.readouterr().err)
    assert rec["run_id"] == str(second)
    assert rec["source"] == "nbu"
    assert "table" not in rec, "поле прошлого запуска протекло в новый"


def test_logs_go_to_stderr_not_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("json")
    get_logger().info("event")
    print("вывод программы")

    captured = capsys.readouterr()
    assert captured.out == "вывод программы\n"
    assert len(records(captured.err)) == 1


def test_cyrillic_is_not_escaped(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("json")
    get_logger().info("event", comment="чанк записан")

    assert "чанк записан" in capsys.readouterr().err


def test_console_format_is_human_readable(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("console")
    get_logger().info("run_started", rows=5)

    err = capsys.readouterr().err
    assert "run_started" in err
    with pytest.raises(json.JSONDecodeError):
        json.loads(err)

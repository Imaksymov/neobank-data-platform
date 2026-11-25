"""Структурированное логирование загрузчика.

Каждая строка лога — запись с полями, а не текст: её можно отфильтровать
по run_id и собрать всю историю одного запуска. Поля run_id и source
привязываются через contextvars один раз в начале запуска, поэтому их
не нужно передавать через аргументы каждой функции. Таблицу и фазу
привязывают на время участка кода:

    with structlog.contextvars.bound_contextvars(table="trans", phase="extract"):
        log.info("chunk_written", rows=100_000)

Логи пишутся в stderr: stdout остаётся для вывода программы, и логи не
смешиваются с ним при перенаправлении в файл или конвейер.

Маскирование секретов работает только по именам полей. Секрет внутри
текста сообщения (log.info(f"подключаюсь к {conninfo}")) замаскирован
не будет — секреты в текст сообщения не подставляются вообще.
"""

import logging
import sys
import uuid
from typing import Final, Literal, cast

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, Processor, WrappedLogger

# Подстроки имён полей, значения которых не должны попадать в лог.
_SENSITIVE: Final[tuple[str, ...]] = ("password", "secret", "token", "conninfo", "dsn")
_MASK: Final[str] = "***"


def _redact(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    for key in event_dict:
        if any(part in key.lower() for part in _SENSITIVE):
            event_dict[key] = _MASK
    return event_dict


def configure_logging(
    fmt: Literal["auto", "json", "console"] = "auto",
    level: int = logging.INFO,
) -> None:
    """Настраивает structlog.

    auto: JSON, если вывод не в терминал (CI, оркестратор, файл), и
    читаемый вывод в терминале. Машине — JSON, человеку — текст.
    """
    use_json = fmt == "json" or (fmt == "auto" and not sys.stderr.isatty())

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact,
    ]
    if use_json:
        processors += [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def new_run_id() -> uuid.UUID:
    """Идентификатор запуска.

    uuid4, а не uuid7: uuid7 упорядочен по времени и был бы удобнее как
    ключ, но в стандартной библиотеке он появился только в Python 3.14,
    а проект закреплён на 3.12.
    """
    return uuid.uuid4()


def bind_run(run_id: uuid.UUID, source: str) -> None:
    """Начинает контекст запуска: дальше каждая строка лога несёт эти поля.

    Сначала очищает контекст — иначе поля прошлого запуска в том же
    процессе протекли бы в новый.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(run_id=str(run_id), source=source)


def get_logger() -> FilteringBoundLogger:
    return cast(FilteringBoundLogger, structlog.get_logger())

"""Исключения загрузчика. Контракт — docs/design/ingestion.md, раздел 12.

Иерархия отвечает на один вопрос: можно ли повторить или нужен человек.

    IngestionError
    ├── RetriableError            временный отказ, безопасно повторить
    │   ├── SourceUnavailableError
    │   └── StorageUnavailableError
    └── FatalError                нужен человек
        ├── ConfigError
        ├── SchemaMismatchError
        └── VerificationError

Повторы ловят только RetriableError. Всё остальное, включая исключения,
не унаследованные от IngestionError, считается фатальным: непонятную
ошибку безопаснее остановить, чем повторить.
"""

from collections.abc import Mapping


class IngestionError(Exception):
    """Базовое исключение загрузчика."""

    def __init__(self, message: str, *, table: str | None = None) -> None:
        super().__init__(message)
        self.table = table


class RetriableError(IngestionError):
    """Временный отказ. Повтор отдельной операции безопасен."""


class SourceUnavailableError(RetriableError):
    """Источник недоступен: обрыв соединения, таймаут."""


class StorageUnavailableError(RetriableError):
    """Объектное хранилище недоступно: 503, сетевой сбой."""


class FatalError(IngestionError):
    """Отказ, при котором нужен человек. Не повторяется автоматически."""


class ConfigError(FatalError):
    """Неверная конфигурация или реестр таблиц."""


class SchemaMismatchError(FatalError):
    """Схема источника разошлась с TableSpec.

    Не повторяется и не «подстраивается»: изменение схемы источника —
    событие, о котором должен узнать человек, а молча изменённый тип в
    Parquet — тихая порча данных ниже по потоку.
    """

    def __init__(
        self,
        table: str,
        *,
        column: str,
        expected: str,
        actual: str,
    ) -> None:
        super().__init__(
            f"{table}.{column}: ожидался тип {expected}, в источнике {actual}",
            table=table,
        )
        self.column = column
        self.expected = expected
        self.actual = actual


class VerificationError(FatalError):
    """Сверка источника и озера не сошлась.

    Фатальна намеренно (спецификация, раздел 12, решение 5): если
    причина детерминирована, повтор упадёт снова; если нет — повтор
    может пройти и скрыть дефект. Для банковских данных тихо прошедший
    повтор хуже явной остановки.

    Обе стороны сверки сохраняются целиком: без них разбор начинается
    с попытки воспроизвести, что именно не сошлось.
    """

    def __init__(
        self,
        table: str,
        *,
        source: Mapping[str, object],
        lake: Mapping[str, object],
    ) -> None:
        differing = sorted(k for k in source.keys() | lake.keys() if source.get(k) != lake.get(k))
        super().__init__(
            f"{table}: сверка не сошлась по {', '.join(differing)}",
            table=table,
        )
        self.source = dict(source)
        self.lake = dict(lake)
        self.differing = differing

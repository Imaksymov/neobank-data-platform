"""Модели домена загрузчика. Контракт — docs/design/ingestion.md.

Инварианты здесь обеспечиваются конструктором, а не договорённостью о
поведении кода. Успешный LoadResult с несошедшейся сверкой невозможно
создать — это тот же вывод, что AF-004: защита не должна держаться на
том, что код соблюдает инвариант.
"""

import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Final, Self
from uuid import UUID

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_IDENTIFIER: Final = re.compile(r"^[a-z_][a-z0-9_]*$")
_FROZEN = ConfigDict(frozen=True, extra="forbid")


class LoadMode(StrEnum):
    """Режим загрузки. Значения совпадают с meta.ingestion_table_load.mode.

    BACKFILL — режим конкретного запуска, а не таблицы: им грузится вся
    история при пустом состоянии или явное окно при досыпке. В TableSpec
    допустимы только FULL и INCREMENTAL.
    """

    FULL = "full"
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


class Status(StrEnum):
    """Статус запуска и загрузки таблицы. Совпадает с meta.ingestion_*."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ColumnType(StrEnum):
    """Логические типы колонок. Закрытый набор: всё, чего нет в списке,
    должно стать явным решением, а не выводом типа."""

    INT32 = "int32"
    INT64 = "int64"
    DATE = "date"
    STRING = "string"
    DECIMAL = "decimal"


def _check_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        message = f"недопустимый идентификатор: {value!r}"
        raise ValueError(message)
    return value


class ColumnSpec(BaseModel):
    """Колонка таблицы с явным типом. Никакого вывода типов."""

    model_config = _FROZEN

    name: str
    type: ColumnType
    precision: int | None = Field(default=None, gt=0, le=38)
    scale: int | None = Field(default=None, ge=0)
    nullable: bool = True

    _name = field_validator("name")(_check_identifier)

    @model_validator(mode="after")
    def _decimal_needs_precision(self) -> Self:
        is_decimal = self.type is ColumnType.DECIMAL
        has_params = self.precision is not None or self.scale is not None
        if is_decimal and (self.precision is None or self.scale is None):
            message = f"{self.name}: decimal требует precision и scale"
            raise ValueError(message)
        if not is_decimal and has_params:
            message = f"{self.name}: precision и scale допустимы только для decimal"
            raise ValueError(message)
        if (
            is_decimal
            and self.scale is not None
            and self.precision is not None
            and self.scale > self.precision
        ):
            message = f"{self.name}: scale больше precision"
            raise ValueError(message)
        return self

    # Кавычки обязательны. В pyarrow-stubs Field обобщённый, и mypy требует
    # параметр типа. Но настоящий pyarrow.lib.Field не поддерживает
    # подстановку: без кавычек аннотация вычисляется при определении
    # класса, и модуль падает при импорте с TypeError — а mypy при этом
    # сообщает Success. См. AF-006.
    def to_arrow(self) -> "pa.Field[pa.DataType]":
        arrow_type: pa.DataType
        match self.type:
            case ColumnType.INT32:
                arrow_type = pa.int32()
            case ColumnType.INT64:
                arrow_type = pa.int64()
            case ColumnType.DATE:
                arrow_type = pa.date32()
            case ColumnType.STRING:
                arrow_type = pa.string()
            case ColumnType.DECIMAL:
                assert self.precision is not None and self.scale is not None
                arrow_type = pa.decimal128(self.precision, self.scale)
        return pa.field(self.name, arrow_type, nullable=self.nullable)


class TableSpec(BaseModel):
    """Описание таблицы для загрузки. Реестр — ingestion/tables.yml (неделя 4).

    source — логическое имя источника: оно попадает в путь озера и в
    meta.ingestion_run.source. Физическая схема Postgres берётся из
    конфигурации, чтобы тесты могли подменить источник одноразовой
    копией (спецификация, раздел 15).
    """

    model_config = _FROZEN

    source: str
    table: str
    mode: LoadMode
    columns: tuple[ColumnSpec, ...] = Field(min_length=1)
    primary_key: tuple[str, ...] = Field(min_length=1)
    watermark_column: str | None = None
    money_columns: tuple[str, ...] = ()

    _source = field_validator("source")(_check_identifier)
    _table = field_validator("table")(_check_identifier)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        names = [c.name for c in self.columns]
        by_name = {c.name: c for c in self.columns}
        problems: list[str] = []

        if len(names) != len(set(names)):
            problems.append("имена колонок повторяются")

        if self.mode is LoadMode.BACKFILL:
            problems.append("backfill — режим запуска, а не таблицы")

        missing_pk = [k for k in self.primary_key if k not in by_name]
        if missing_pk:
            problems.append(f"ключ ссылается на несуществующие колонки: {missing_pk}")

        if self.mode is LoadMode.INCREMENTAL:
            wm = self.watermark_column
            if wm is None:
                problems.append("incremental требует watermark_column")
            elif wm not in by_name:
                problems.append(f"watermark_column {wm!r} нет среди колонок")
            elif by_name[wm].type is not ColumnType.DATE:
                # спецификация, раздел 8: все водяные знаки проекта — даты
                problems.append(f"watermark_column {wm!r} должна быть date")
        elif self.watermark_column is not None:
            problems.append("watermark_column допустима только для incremental")

        for col in self.money_columns:
            if col not in by_name:
                problems.append(f"денежная колонка {col!r} не найдена")
            elif by_name[col].type is not ColumnType.DECIMAL:
                # деньги — только decimal: float для денег запрещён CLAUDE.md
                problems.append(f"денежная колонка {col!r} должна быть decimal")

        if problems:
            message = f"{self.source}.{self.table}: " + "; ".join(problems)
            raise ValueError(message)
        return self

    def arrow_schema(self) -> pa.Schema:
        return pa.schema([c.to_arrow() for c in self.columns])


class Checksum(BaseModel):
    """Контрольные суммы одной стороны сверки.

    Суммы — Decimal, и float на входе отвергается явно. Деньги, прошедшие
    через float, уже испорчены: на неделе 2 сумма trans через JSON
    разошлась на 1.13 копейки. В JSON суммы сериализуются строками.
    """

    model_config = _FROZEN

    row_count: int = Field(ge=0)
    sums: dict[str, Decimal] = Field(default_factory=dict)
    min_date: date | None = None
    max_date: date | None = None

    @field_validator("sums", mode="before")
    @classmethod
    def _no_float_money(cls, value: object) -> object:
        if isinstance(value, dict):
            floats = [k for k, v in value.items() if isinstance(v, float)]
            if floats:
                message = f"суммы как float недопустимы: {floats}"
                raise ValueError(message)
        return value


class LoadResult(BaseModel):
    """Результат загрузки одной таблицы в одном запуске.

    Соответствует строке meta.ingestion_table_load.
    """

    model_config = _FROZEN

    run_id: UUID
    table: str
    mode: LoadMode
    status: Status
    window_start: date | None = None
    window_end: date | None = None
    rows_extracted: int = Field(ge=0)
    rows_written: int = Field(ge=0)
    source_checksum: Checksum
    lake_checksum: Checksum
    files: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        problems: list[str] = []

        match self.mode:
            case LoadMode.FULL:
                if self.window_start is not None or self.window_end is not None:
                    problems.append("full не имеет окна")
            case LoadMode.INCREMENTAL:
                if self.window_start is None or self.window_end is None:
                    problems.append("incremental требует обе границы окна")
            case LoadMode.BACKFILL:
                if self.window_end is None:
                    problems.append("backfill требует window_end")

        if (
            self.window_start is not None
            and self.window_end is not None
            and self.window_start > self.window_end
        ):
            problems.append("window_start позже window_end")

        # Успех без сошедшейся сверки — противоречие, а не вариант успеха.
        # Спецификация, раздел 2: сверка — часть определения успеха.
        if self.status is Status.SUCCEEDED:
            if self.rows_extracted != self.rows_written:
                problems.append(
                    f"succeeded при extracted={self.rows_extracted}, written={self.rows_written}"
                )
            if self.source_checksum != self.lake_checksum:
                problems.append("succeeded при несошедшейся сверке")
            # Только в одну сторону. Пустое окно без файлов — норма, а для
            # статичного источника самый частый случай: каждый инкремент
            # после первого извлекает ноль строк. Запретить надо обратное —
            # строки числятся записанными, а файлов нет.
            if self.rows_written > 0 and not self.files:
                problems.append(f"succeeded: {self.rows_written} строк без файлов")

        if problems:
            message = f"{self.table}: " + "; ".join(problems)
            raise ValueError(message)
        return self

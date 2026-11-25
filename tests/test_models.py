"""Модели домена: инварианты обеспечиваются конструктором.

Каждый отказ проверяется по тексту причины, а не по самому факту ошибки:
валидатор, отклоняющий не по той причине, иначе выглядел бы рабочим.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ingestion.models import (
    Checksum,
    ColumnSpec,
    ColumnType,
    LoadMode,
    LoadResult,
    Status,
    TableSpec,
)


def col(name: str, type_: ColumnType, **kw: Any) -> ColumnSpec:
    return ColumnSpec(name=name, type=type_, **kw)


@pytest.fixture
def trans_spec() -> dict[str, Any]:
    return {
        "source": "berka",
        "table": "trans",
        "mode": LoadMode.INCREMENTAL,
        "columns": (
            col("trans_id", ColumnType.INT32, nullable=False),
            col("date", ColumnType.DATE, nullable=False),
            col("amount", ColumnType.DECIMAL, precision=12, scale=2),
            col("operation", ColumnType.STRING),
        ),
        "primary_key": ("trans_id",),
        "watermark_column": "date",
        "money_columns": ("amount",),
    }


@pytest.fixture
def checksum() -> Checksum:
    return Checksum(row_count=1_056_320, sums={"amount": Decimal("6257793560.30")})


@pytest.fixture
def ok_result(checksum: Checksum) -> dict[str, Any]:
    return {
        "run_id": uuid4(),
        "table": "trans",
        "mode": LoadMode.INCREMENTAL,
        "status": Status.SUCCEEDED,
        "window_start": date(2026, 11, 21),
        "window_end": date(2026, 11, 23),
        "rows_extracted": 10,
        "rows_written": 10,
        "source_checksum": checksum,
        "lake_checksum": checksum,
        "files": ("part-00000.parquet",),
    }


# --- TableSpec ------------------------------------------------------------


def test_valid_trans_spec(trans_spec: dict[str, Any]) -> None:
    TableSpec(**trans_spec)


def test_reserved_word_is_a_valid_table_name(trans_spec: dict[str, Any]) -> None:
    # order — зарезервированное слово, но допустимый идентификатор:
    # имя источника сохранено намеренно (docs/models/source_berka.md)
    TableSpec(**{**trans_spec, "table": "order"})


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"watermark_column": None}, "требует watermark_column"),
        ({"watermark_column": "trans_id"}, "должна быть date"),
        ({"money_columns": ("operation",)}, "должна быть decimal"),
        ({"mode": LoadMode.BACKFILL}, "режим запуска"),
        ({"primary_key": ("nope",)}, "несуществующие"),
        ({"table": "trans; drop table x"}, "недопустимый идентификатор"),
        ({"mode": LoadMode.FULL}, "только для incremental"),
        ({"watermark_column": "nope"}, "нет среди колонок"),
        ({"money_columns": ("nope",)}, "не найдена"),
        (
            {"columns": (col("x", ColumnType.INT32), col("x", ColumnType.DATE))},
            "повторяются",
        ),
    ],
    ids=[
        "incremental-without-watermark",
        "watermark-not-date",
        "money-not-decimal",
        "backfill-as-table-mode",
        "pk-missing-column",
        "unsafe-identifier",
        "full-with-watermark",
        "watermark-column-missing",
        "money-column-missing",
        "duplicate-column-names",
    ],
)
def test_table_spec_rejects(
    trans_spec: dict[str, Any], change: dict[str, Any], reason: str
) -> None:
    with pytest.raises(ValidationError, match=reason):
        TableSpec(**{**trans_spec, **change})


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({}, "требует precision"),
        ({"precision": 2, "scale": 5}, "scale больше"),
    ],
    ids=["decimal-without-precision", "scale-above-precision"],
)
def test_decimal_column_rejects(kwargs: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValidationError, match=reason):
        col("x", ColumnType.DECIMAL, **kwargs)


def test_precision_only_allowed_for_decimal() -> None:
    with pytest.raises(ValidationError, match="допустимы только для decimal"):
        col("x", ColumnType.INT32, precision=10)


# --- схема Arrow ----------------------------------------------------------


def test_arrow_schema_keeps_decimal_precision(trans_spec: dict[str, Any]) -> None:
    schema = TableSpec(**trans_spec).arrow_schema()
    assert str(schema.field("amount").type) == "decimal128(12, 2)"


@pytest.mark.parametrize(
    ("type_", "arrow"),
    [
        (ColumnType.INT32, "int32"),
        (ColumnType.INT64, "int64"),
        (ColumnType.DATE, "date32[day]"),
        (ColumnType.STRING, "string"),
    ],
)
def test_column_types_map_to_arrow(type_: ColumnType, arrow: str) -> None:
    assert str(col("x", type_).to_arrow().type) == arrow


def test_arrow_schema_keeps_nullability(trans_spec: dict[str, Any]) -> None:
    schema = TableSpec(**trans_spec).arrow_schema()
    assert schema.field("trans_id").nullable is False
    assert schema.field("amount").nullable is True


# --- Checksum -------------------------------------------------------------


def test_checksum_rejects_float_money() -> None:
    # Сырой внешний ввод — через model_validate: типизированный конструктор
    # float сюда статически не пропустил бы, а из JSON он приходит именно так.
    with pytest.raises(ValidationError, match="float недопустимы"):
        Checksum.model_validate({"row_count": 1, "sums": {"amount": 0.1}})


def test_checksum_parses_string_exactly() -> None:
    # Строка — как сумма приходит из базы или из JSON метаданных.
    raw = {"row_count": 1, "sums": {"amount": "6257793560.30"}}
    assert Checksum.model_validate(raw).sums["amount"] == Decimal("6257793560.30")


def test_checksum_serializes_money_as_string(checksum: Checksum) -> None:
    # в JSON нет десятичного типа: число стало бы float
    dumped = checksum.model_dump(mode="json")
    assert dumped["sums"] == {"amount": "6257793560.30"}
    assert isinstance(json.loads(json.dumps(dumped))["sums"]["amount"], str)


# --- LoadResult -----------------------------------------------------------


def test_valid_succeeded_result(ok_result: dict[str, Any]) -> None:
    LoadResult(**ok_result)


def test_empty_window_without_files_is_success(ok_result: dict[str, Any]) -> None:
    # Статичный источник: каждый инкремент после первого извлекает
    # ноль строк, и успешный запуск без файлов — самый частый случай.
    LoadResult(**{**ok_result, "rows_extracted": 0, "rows_written": 0, "files": ()})


def test_backfill_needs_only_upper_bound(ok_result: dict[str, Any]) -> None:
    # window_start=None — без нижней границы: вся история при пустом состоянии
    LoadResult(**{**ok_result, "mode": LoadMode.BACKFILL, "window_start": None})


def test_backfill_without_upper_bound_is_rejected(ok_result: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="backfill требует window_end"):
        LoadResult(**{**ok_result, "mode": LoadMode.BACKFILL, "window_end": None})


def test_failed_result_may_have_mismatched_checksums(ok_result: dict[str, Any]) -> None:
    # Иначе было бы нечем записать сам провал.
    other = Checksum(row_count=1_056_320, sums={"amount": Decimal("6257793560.31")})
    LoadResult(**{**ok_result, "status": Status.FAILED, "lake_checksum": other})


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (
            {
                "lake_checksum": Checksum(
                    row_count=1_056_320, sums={"amount": Decimal("6257793560.31")}
                )
            },
            "несошедшейся",
        ),
        ({"rows_written": 9}, "extracted=10"),
        ({"files": ()}, "строк без файлов"),
        ({"window_start": None}, "обе границы"),
        ({"window_start": date(2026, 12, 1)}, "позже window_end"),
        ({"mode": LoadMode.FULL}, "full не имеет окна"),
        ({"rows_writen": 10}, "Extra inputs"),
    ],
    ids=[
        "success-with-one-kopeck-mismatch",
        "success-with-row-mismatch",
        "success-rows-without-files",
        "incremental-without-window",
        "window-reversed",
        "full-with-window",
        "typo-in-field-name",
    ],
)
def test_load_result_rejects(
    ok_result: dict[str, Any], change: dict[str, Any], reason: str
) -> None:
    with pytest.raises(ValidationError, match=reason):
        LoadResult(**{**ok_result, **change})

"""Исключения: иерархия отвечает на вопрос «повторить или звать человека»."""

import pytest
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_none

from ingestion.errors import (
    FatalError,
    IngestionError,
    RetriableError,
    SchemaMismatchError,
    SourceUnavailableError,
    StorageUnavailableError,
    VerificationError,
)


@pytest.mark.parametrize("exc", [SourceUnavailableError, StorageUnavailableError])
def test_transient_failures_are_retriable(exc: type[IngestionError]) -> None:
    assert issubclass(exc, RetriableError)


def test_verification_failure_is_fatal() -> None:
    assert issubclass(VerificationError, FatalError)


def test_fatal_and_retriable_are_disjoint() -> None:
    assert not issubclass(FatalError, RetriableError)
    assert not issubclass(RetriableError, FatalError)


def test_verification_error_names_what_differs() -> None:
    err = VerificationError(
        "trans",
        source={"row_count": 10, "amount": "100.00", "max_date": "2026-11-23"},
        lake={"row_count": 10, "amount": "100.01", "max_date": "2026-11-23"},
    )
    assert err.differing == ["amount"]
    assert str(err) == "trans: сверка не сошлась по amount"


def test_verification_error_keeps_both_sides() -> None:
    # без обеих сторон разбор начинается с попытки воспроизвести расхождение
    err = VerificationError("trans", source={"amount": "100.00"}, lake={"amount": "100.01"})
    assert err.source == {"amount": "100.00"}
    assert err.lake == {"amount": "100.01"}


def test_schema_mismatch_message() -> None:
    err = SchemaMismatchError(
        "trans", column="amount", expected="decimal128(12, 2)", actual="double"
    )
    assert str(err) == "trans.amount: ожидался тип decimal128(12, 2), в источнике double"
    assert err.table == "trans"


def _attempts(exc: Exception) -> int:
    """Сколько раз повторяющая обёртка вызовет операцию, бросающую exc."""
    calls = 0

    @retry(
        retry=retry_if_exception_type(RetriableError),
        stop=stop_after_attempt(3),
        wait=wait_none(),
        reraise=True,
    )
    def operation() -> None:
        nonlocal calls
        calls += 1
        raise exc

    with pytest.raises(type(exc)):
        operation()
    return calls


def test_retriable_error_is_retried() -> None:
    assert _attempts(SourceUnavailableError("обрыв соединения")) == 3


def test_fatal_error_is_not_retried() -> None:
    assert _attempts(VerificationError("trans", source={}, lake={"a": 1})) == 1


def test_unknown_error_is_not_retried() -> None:
    # непонятную ошибку безопаснее остановить, чем повторить
    assert _attempts(ValueError("неожиданное")) == 1

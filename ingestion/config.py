"""Конфигурация загрузчика.

Значения читаются из переменных окружения и файла infra/.env — того же,
что читает docker-compose, поэтому один файл обслуживает и окружение,
и загрузчик.

Общие с compose только адреса: хост, порт, имя базы. Учётные данные у
загрузчика свои. POSTGRES_USER в compose — суперпользователь, и взять
его по умолчанию значило бы нарушить раздел 13 спецификации с первого
запуска. Поэтому умолчания указывают на роль ingestion_loader: пока она
не создана, подключение упадёт с отказом — безопасный отказ лучше, чем
молча работающий суперпользователь.
"""

from pathlib import Path
from typing import Final, Literal

from psycopg.conninfo import make_conninfo
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE: Final[Path] = Path(__file__).resolve().parents[1] / "infra" / ".env"

# populate_by_name здесь запрещён. С ним pydantic-settings ищет переменную
# окружения не только по псевдониму, но и по имени поля без учёта регистра:
# поле user находит $USER оболочки, host — $HOST, port — $PORT. Проверено:
# при USER=postgres загрузчик подключался суперпользователем, а при
# HOST=evil.example.com уходил на чужой хост со своим паролем. PORT
# выставляют многие платформы сами (Cloud Run — PORT=8080). См. AF-005.
# Поэтому значения задаются только через псевдонимы, и в тестах тоже —
# через переменные окружения, а не через аргументы конструктора.
_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=ENV_FILE,
    extra="ignore",
    frozen=True,
)


class SourceDbSettings(BaseSettings):
    """Postgres-источник. Загрузчик только читает его."""

    model_config = _SETTINGS_CONFIG

    host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    dbname: str = Field(default="neobank", validation_alias="POSTGRES_DB")
    user: str = Field(default="ingestion_loader", validation_alias="INGESTION_DB_USER")
    password: SecretStr = Field(
        default=SecretStr("ingestion_loader_local_only"),
        validation_alias="INGESTION_DB_PASSWORD",
    )

    def conninfo(self) -> str:
        """Строка подключения в формате ключ=значение.

        Не URL: в URL пароль с символами @, / или : требует экранирования,
        и ошибка в нём даёт подключение не туда, а не понятную ошибку.
        make_conninfo экранирует сам.
        """
        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password.get_secret_value(),
        )


class LakeSettings(BaseSettings):
    """Объектное хранилище (MinIO). Пользователь загрузчика — с недели 4."""

    model_config = _SETTINGS_CONFIG

    endpoint: str = Field(default="http://localhost:9000", validation_alias="MINIO_ENDPOINT")
    access_key: str = Field(default="ingestion_loader", validation_alias="INGESTION_S3_ACCESS_KEY")
    secret_key: SecretStr = Field(
        default=SecretStr("ingestion_loader_local_only"),
        validation_alias="INGESTION_S3_SECRET_KEY",
    )
    bucket: str = Field(default="raw", validation_alias="INGESTION_RAW_BUCKET")


class LoaderSettings(BaseSettings):
    """Параметры поведения загрузчика."""

    model_config = _SETTINGS_CONFIG

    chunk_size: int = Field(default=100_000, gt=0, validation_alias="INGESTION_CHUNK_SIZE")
    lookback_days: int = Field(default=2, ge=0, validation_alias="INGESTION_LOOKBACK_DAYS")
    log_format: Literal["auto", "json", "console"] = Field(
        default="auto", validation_alias="INGESTION_LOG_FORMAT"
    )


class Settings(BaseModel):
    """Вся конфигурация, неизменяемая после загрузки."""

    model_config = ConfigDict(frozen=True)

    source: SourceDbSettings
    lake: LakeSettings
    loader: LoaderSettings


def load_settings() -> Settings:
    """Читает окружение один раз. Ошибка валидации — сразу, при старте."""
    return Settings(
        source=SourceDbSettings(),
        lake=LakeSettings(),
        loader=LoaderSettings(),
    )

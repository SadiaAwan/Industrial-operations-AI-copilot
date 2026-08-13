"""Idempotently create the isolated local MLflow PostgreSQL database."""

from psycopg import connect, sql

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    admin_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    with connect(admin_url, autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (settings.mlflow_database_name,),
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(settings.mlflow_database_name)
                )
            )
            print(f"Created MLflow database: {settings.mlflow_database_name}")
        else:
            print(f"MLflow database already exists: {settings.mlflow_database_name}")


if __name__ == "__main__":
    main()

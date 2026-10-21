import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ("ingredients", "recipes", "recipe_ingredients", "pantry_items", "alembic_version")


def offline_sql(database_url: str) -> str:
    """`alembic upgrade head --sql` çıktısı; veritabanına bağlanmaz."""
    env = {**os.environ, "DATABASE_URL": database_url, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def test_postgres_migration_enables_rls_on_every_public_table():
    sql = offline_sql("postgresql://user:pw@localhost:6543/postgres")

    for table in TABLES:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, table
    # alembic_version önce oluşturulmalı, sonra RLS açılmalı
    assert sql.index("CREATE TABLE alembic_version") < sql.index(
        "ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY"
    )


def test_sqlite_migration_skips_postgres_only_statements():
    sql = offline_sql("sqlite:///./unused_for_offline.db")

    assert "ROW LEVEL SECURITY" not in sql
    assert "CREATE TABLE recipes" in sql

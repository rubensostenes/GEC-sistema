"""Gera database/schema_postgres.sql a partir de database/schema.sql.

O GEC sempre foi escrito em SQL "SQLite-flavored" (AUTOINCREMENT, datetime('now','localtime')).
Este script faz a tradução mecânica para a sintaxe do Postgres, para uso no Cloud SQL.
Rode de novo sempre que schema.sql mudar:

    python scripts/gerar_schema_postgres.py
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ORIGEM = BASE_DIR / "database" / "schema.sql"
DESTINO = BASE_DIR / "database" / "schema_postgres.sql"

AGORA_LOCAL = "to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')"


def converter(sql: str) -> str:
    sql = re.sub(r"^PRAGMA .*;\s*\n?", "", sql, flags=re.MULTILINE)
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("datetime('now', 'localtime')", AGORA_LOCAL)
    # "CREATE INDEX IF NOT EXISTS" e "CREATE TABLE IF NOT EXISTS" já são válidos no Postgres.
    return sql


def main():
    sql = ORIGEM.read_text(encoding="utf-8")
    convertido = converter(sql)
    cabecalho = (
        "-- GERADO AUTOMATICAMENTE a partir de schema.sql por scripts/gerar_schema_postgres.py\n"
        "-- Não edite este arquivo diretamente — edite schema.sql e rode o script de novo.\n\n"
    )
    DESTINO.write_text(cabecalho + convertido, encoding="utf-8")
    print(f"Gerado: {DESTINO}")


if __name__ == "__main__":
    main()

"""Gera database/schema_postgres.sql a partir de database/schema.sql.

O GEC sempre foi escrito em SQL "SQLite-flavored" (AUTOINCREMENT, datetime('now','localtime')).
Este script faz a tradução mecânica para a sintaxe do Postgres, para uso em
Postgres gerenciado (Neon, Cloud SQL etc.). Rode de novo sempre que schema.sql mudar:

    python scripts/gerar_schema_postgres.py

Sobre chaves estrangeiras: o SQLite não valida nada na hora do CREATE TABLE,
então o schema.sql pode referenciar tabelas criadas depois (usuarios ->
unidades) ou até em ciclo (setores.responsavel_id -> colaboradores e
colaboradores.unidade_id -> unidades). O Postgres valida na criação, então este
script REMOVE as cláusulas REFERENCES dos CREATE TABLE e as reemite como
ALTER TABLE ... ADD CONSTRAINT no final do arquivo — assim a ordem das tabelas
nunca importa.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ORIGEM = BASE_DIR / "database" / "schema.sql"
DESTINO = BASE_DIR / "database" / "schema_postgres.sql"

AGORA_LOCAL = "to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')"

# REFERENCES tabela(col) [ON DELETE acao] [ON UPDATE acao]
_RE_FK = re.compile(
    r"\s*REFERENCES\s+(\w+)\s*\([^)]*\)"
    r"(\s+ON\s+DELETE\s+(?:CASCADE|SET\s+NULL|SET\s+DEFAULT|NO\s+ACTION|RESTRICT))?"
    r"(\s+ON\s+UPDATE\s+(?:CASCADE|SET\s+NULL|SET\s+DEFAULT|NO\s+ACTION|RESTRICT))?"
)
_RE_CREATE = re.compile(r"CREATE TABLE IF NOT EXISTS (\w+)\s*\(")


def converter(sql: str) -> str:
    sql = re.sub(r"^PRAGMA .*;\s*\n?", "", sql, flags=re.MULTILINE)
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("datetime('now', 'localtime')", AGORA_LOCAL)
    sql = re.sub(r"\bBLOB\b", "BYTEA", sql)  # tipo binário: BLOB (SQLite) -> BYTEA (Postgres)
    sql = sql.replace(
        "date('now', 'localtime')",
        "to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')",
    )

    # Tira as FKs inline dos CREATE TABLE, anotando (tabela, coluna, referência).
    fks = []  # (tabela, coluna, trecho_fk_com_barra_e_espaco_inicial)
    tabela_atual = None
    linhas = []
    for linha in sql.split("\n"):
        m = _RE_CREATE.search(linha)
        if m:
            tabela_atual = m.group(1)
        if tabela_atual and "REFERENCES" in linha:
            coluna = linha.strip().split()[0]
            nova_linha = _RE_FK.sub("", linha, count=1)
            fks.append((tabela_atual, coluna, linha[len(nova_linha.rstrip("\n")) :].strip()))
            # _RE_FK.sub não devolve o trecho removido; recuperamos por busca direta:
            achou = _RE_FK.search(linha)
            fks[-1] = (tabela_atual, coluna, achou.group(0).strip())
            linha = nova_linha
        linhas.append(linha)
    sql = "\n".join(linhas)

    if fks:
        comandos = [
            "",
            "-- ============================================================",
            "-- CHAVES ESTRANGEIRAS — emitidas no final porque o Postgres",
            "-- valida a existência da tabela referenciada na criação (e o",
            "-- schema original do SQLite depende de ordem/tem ciclos).",
            "-- ============================================================",
        ]
        usados = set()
        for tabela, coluna, trecho in fks:
            nome = f"fk_{tabela}_{coluna}"
            base, n = nome, 2
            while nome in usados:
                nome = f"{base}_{n}"
                n += 1
            usados.add(nome)
            comandos.append(
                f"ALTER TABLE {tabela} ADD CONSTRAINT {nome} "
                f"FOREIGN KEY ({coluna}) {trecho};"
            )
        sql += "\n" + "\n".join(comandos)

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

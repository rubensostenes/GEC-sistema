import os
import re
import sqlite3
from pathlib import Path

from flask import current_app, g

USANDO_POSTGRES = bool(os.environ.get("DATABASE_URL"))

if USANDO_POSTGRES:
    import psycopg2
    import psycopg2.extras


class _CursorPostgres:
    """Faz um cursor do psycopg2 se comportar como um cursor do sqlite3.

    Isso permite manter TODAS as queries do app (escritas com `?` e lidas como
    sqlite3.Row) sem alteração, trocando só a conexão por trás.
    """

    _RE_INSERT = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)", re.IGNORECASE)

    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None

    @staticmethod
    def _traduzir(sql):
        sql = sql.replace("?", "%s")
        sql = sql.replace("datetime('now', 'localtime')", "to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')")
        return sql

    def execute(self, sql, params=()):
        sql_traduzido = self._traduzir(sql)
        eh_insert = self._RE_INSERT.match(sql)
        if eh_insert and "RETURNING" not in sql_traduzido.upper():
            sql_traduzido += " RETURNING id"
        try:
            self._cur.execute(sql_traduzido, params)
        except Exception:
            # Sem isso, uma falha (ex: UNIQUE) deixaria a conexão "travada" até
            # um rollback explícito — diferente do SQLite, onde cada statement
            # falha isoladamente. As rotas do app só fazem `except Exception: flash(...)`,
            # então garantimos aqui que a conexão volta a um estado limpo.
            self._cur.connection.rollback()
            raise
        if eh_insert:
            try:
                self.lastrowid = self._cur.fetchone()["id"]
            except (TypeError, KeyError, psycopg2.ProgrammingError):
                self.lastrowid = None
        return self

    def executescript(self, sql):
        # PRAGMA não existe no Postgres — schema_postgres.sql já vem sem elas.
        self._cur.execute(sql)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur)


class _ConexaoPostgres:
    """Faz uma conexão psycopg2 se comportar como uma conexão sqlite3 (get_db() a usa assim)."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = _CursorPostgres(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        return cur.execute(sql, params)

    def executescript(self, sql):
        cur = self._conn.cursor()
        cur.execute(sql)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _conectar():
    if USANDO_POSTGRES:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        return _ConexaoPostgres(conn)
    conexao = sqlite3.connect(current_app.config["DATABASE_PATH"])
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def get_db():
    if "db" not in g:
        g.db = _conectar()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


COLUNAS_NOVAS = {
    "anexos": [("revisado", "INTEGER NOT NULL DEFAULT 0")],
    "ordens_servico": [
        ("aguardando_aprovacao_orcamento", "INTEGER NOT NULL DEFAULT 0"),
        ("valor_orcamento", "REAL"),
        ("centro_custo_id", "INTEGER REFERENCES centros_custo(id) ON DELETE SET NULL"),
        ("label_id", "INTEGER REFERENCES labels(id) ON DELETE SET NULL"),
        ("plano_manutencao_id", "INTEGER REFERENCES planos_manutencao(id) ON DELETE SET NULL"),
        ("certificado_numero", "TEXT"),
        ("certificado_situacao", "TEXT"),
        ("certificado_validade", "TEXT"),
    ],
    "equipamentos": [
        ("tag", "TEXT"),
        ("data_instalacao", "TEXT"),
        ("valor_reposicao", "REAL"),
        ("de_terceiros", "INTEGER NOT NULL DEFAULT 0"),
        ("proprietario_terceiro", "TEXT"),
        ("eh_padrao_calibracao", "INTEGER NOT NULL DEFAULT 0"),
        ("certificado_rastreabilidade", "TEXT"),
        ("orgao_certificador", "TEXT"),
        ("data_validade_rastreabilidade", "TEXT"),
        ("label_id", "INTEGER REFERENCES labels(id) ON DELETE SET NULL"),
    ],
    "usuarios": [
        ("grupo_id", "INTEGER REFERENCES grupos_usuarios(id) ON DELETE SET NULL"),
    ],
    "setores": [
        ("codigo", "TEXT"),
        ("responsavel_id", "INTEGER REFERENCES colaboradores(id) ON DELETE SET NULL"),
        ("eh_almoxarifado", "INTEGER NOT NULL DEFAULT 0"),
        ("codigo_integracao", "TEXT"),
        ("localizacao", "TEXT"),
        ("contato", "TEXT"),
        ("telefone", "TEXT"),
        ("ramal", "TEXT"),
        ("pais", "TEXT"),
        ("cep", "TEXT"),
        ("logradouro", "TEXT"),
        ("numero", "TEXT"),
        ("complemento", "TEXT"),
        ("bairro", "TEXT"),
        ("cidade", "TEXT"),
        ("estado", "TEXT"),
        ("observacao", "TEXT"),
    ],
    "almoxarifados": [
        ("setor_id", "INTEGER REFERENCES setores(id) ON DELETE SET NULL"),
    ],
    "procedimentos_manutencao": [
        ("codigo", "TEXT"),
        ("titulo_relatorio", "TEXT"),
        ("procedimento_generico", "INTEGER NOT NULL DEFAULT 0"),
        ("ativo", "INTEGER NOT NULL DEFAULT 1"),
        ("versao", "TEXT NOT NULL DEFAULT '1.0'"),
        ("publicado", "INTEGER NOT NULL DEFAULT 0"),
        ("data_publicacao", "TEXT"),
    ],
    "procedimento_itens": [
        ("bloco_id", "INTEGER REFERENCES procedimento_blocos(id) ON DELETE CASCADE"),
        ("ativo", "INTEGER NOT NULL DEFAULT 1"),
    ],
    "centros_custo": [
        ("codigo", "TEXT"),
    ],
}


def _colunas_existentes_postgres(db, tabela):
    cur = db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", (tabela,)
    )
    return {linha["column_name"] for linha in cur.fetchall()}


def _migrar_colunas(db):
    """Adiciona colunas novas a tabelas já existentes, sem afetar dados atuais."""
    for tabela, colunas in COLUNAS_NOVAS.items():
        if USANDO_POSTGRES:
            existentes = _colunas_existentes_postgres(db, tabela)
        else:
            existentes = {linha[1] for linha in db.execute(f"PRAGMA table_info({tabela})")}
        for nome, definicao in colunas:
            if nome not in existentes:
                db.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def init_db(app):
    if USANDO_POSTGRES:
        db = _conectar()
        schema_path = str(Path(app.config["SCHEMA_PATH"]).parent / "schema_postgres.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            db.executescript(f.read())
        _migrar_colunas(db)
        db.commit()
        db.close()
        return

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(app.config["DATABASE_PATH"])
    with open(app.config["SCHEMA_PATH"], "r", encoding="utf-8") as f:
        conexao.executescript(f.read())
    _migrar_colunas(conexao)
    conexao.commit()
    conexao.close()


def init_app(app):
    app.teardown_appcontext(close_db)

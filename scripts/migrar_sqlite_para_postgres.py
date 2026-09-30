"""Copia todos os dados do database/gec.db (SQLite) para o Postgres do Cloud SQL.

Uso (depois de já ter criado as tabelas rodando o app uma vez com DATABASE_URL
apontando pro Postgres vazio, ou executando database/schema_postgres.sql manualmente):

    set DATABASE_URL=postgresql://usuario:senha@host:5432/gec
    python scripts/migrar_sqlite_para_postgres.py

Idempotência: NÃO é seguro rodar duas vezes sobre um Postgres que já tem dados
(vai duplicar / dar erro de UNIQUE). Rode uma vez só, contra um banco vazio.
"""
import os
import sqlite3
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = BASE_DIR / "database" / "gec.db"

# Mesma ordem de criação do schema.sql — usada só para a mensagem de progresso
# ficar em ordem lógica; a integridade referencial durante a carga é garantida
# desligando os triggers de FK (ver abaixo), não pela ordem da lista.
TABELAS = [
    "usuarios", "tokens_acesso", "unidades", "setores", "setor_centro_custo",
    "setor_usuarios_liberados", "equipamentos", "ordens_servico", "requisicoes_servico",
    "pecas_estoque", "ordem_servico_pecas", "anexos", "ordem_servico_historico",
    "fornecedores", "contratos_manutencao", "colaboradores", "apontamentos_horas",
    "manuais", "fabricantes", "modelos", "plano_descricoes", "reservas_equipamento",
    "transportes_equipamento", "contadores_equipamento", "solicitacoes_compra",
    "pedidos_compra", "pedido_compra_itens", "entradas_estoque", "entrada_estoque_itens",
    "almoxarifados", "transferencias_estoque", "baixas_estoque", "inventarios",
    "inventario_itens", "centros_custo", "grupos_consumo", "tabelas_consumo",
    "informacoes_consumo", "metas_consumo", "grupos_usuarios", "empresa",
    "alertas_gerais", "unidades_medida", "feriados", "labels", "parametros_locais",
    "parametros_globais", "parametros_calibracao", "config_senha", "config_listagem",
    "acessos_falhos", "log_acessos", "log_dados_sistema", "procedimentos_manutencao",
    "procedimento_blocos", "procedimento_itens", "modelo_procedimentos",
    "mensagens_chat", "assinaturas", "sensores", "leituras_sensor",
    "preferencias_notificacao", "agendamentos_relatorio", "ideias", "ideia_votos",
    "planos_manutencao", "plano_manutencao_checklist",
]


def main():
    pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        sys.exit("Defina DATABASE_URL antes de rodar este script.")
    if not SQLITE_PATH.exists():
        sys.exit(f"Não achei {SQLITE_PATH}")

    sconn = sqlite3.connect(str(SQLITE_PATH))
    sconn.row_factory = sqlite3.Row
    pconn = psycopg2.connect(pg_url)
    pcur = pconn.cursor()

    tabelas_existentes = {
        t
        for t in TABELAS
        if sconn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()
    }

    print("Desligando triggers de FK para a carga em massa...")
    for t in tabelas_existentes:
        pcur.execute(f"ALTER TABLE {t} DISABLE TRIGGER ALL")

    total_geral = 0
    for t in TABELAS:
        if t not in tabelas_existentes:
            continue
        linhas = sconn.execute(f"SELECT * FROM {t}").fetchall()
        if not linhas:
            print(f"  {t}: 0 linhas")
            continue
        colunas = linhas[0].keys()
        colunas_sql = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(colunas))
        sql = f"INSERT INTO {t} ({colunas_sql}) VALUES ({placeholders})"
        dados = [tuple(linha[c] for c in colunas) for linha in linhas]
        psycopg2.extras.execute_batch(pcur, sql, dados, page_size=500)
        total_geral += len(linhas)
        print(f"  {t}: {len(linhas)} linhas")

    print("Religando triggers de FK...")
    for t in tabelas_existentes:
        pcur.execute(f"ALTER TABLE {t} ENABLE TRIGGER ALL")

    print("Ajustando sequências SERIAL para continuar depois do maior id importado...")
    for t in tabelas_existentes:
        pcur.execute(f"SELECT MAX(id) FROM {t}")
        maior_id = pcur.fetchone()[0]
        if maior_id is not None:
            pcur.execute(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, true)", (t, maior_id)
            )

    pconn.commit()
    pcur.close()
    pconn.close()
    sconn.close()
    print(f"\nConcluído. {total_geral} linhas migradas no total.")


if __name__ == "__main__":
    main()

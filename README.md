# GEC-sistema

Sistema web de Gestão de Equipamentos e Consumo (Flask + SQLite/Postgres).

## Rodar localmente (modo clássico)

- **Windows:** dê dois cliques em `iniciar.bat` (instala dependências e abre em http://localhost:5000)
- **Linux/Mac:** `pip install -r requirements.txt && python app.py`

Sem variáveis de ambiente: banco SQLite em `database/gec.db`, anexos em
`static/uploads`. O primeiro usuário registrado em `/auth/registrar` vira
administrador.

## Deploy na Vercel (serverless)

Guia completo em **[DEPLOY_VERCEL.md](DEPLOY_VERCEL.md)**. Resumo:

- Banco: **Neon Postgres** (free) via variável `DATABASE_URL` — o `db.py`
  traduz as queries automaticamente
- Anexos: gravados no banco (tabela `arquivos_storage`) com
  `GEC_STORAGE_BACKEND=db`
- Entrypoint: `api/index.py` + `vercel.json` (prontos neste repo)

## Estrutura

| Caminho | O que é |
|---|---|
| `app.py` | Fábrica da aplicação Flask (13 blueprints) |
| `db.py` | Camada de dados: SQLite ⇄ Postgres com a mesma query |
| `database/schema.sql` | 68 tabelas (fonte da verdade) |
| `scripts/gerar_schema_postgres.py` | Regenera `schema_postgres.sql` (edite schema.sql e rode) |
| `scripts/migrar_sqlite_para_postgres.py` | Leva dados do SQLite local pro Postgres |
| `firestore_app/` | Migração p/ Firestore (desenho em andamento, não usado no deploy) |

# Deploy do GEC na Vercel + Neon (Postgres)

Este deploy usa **Vercel (Hobby)** + **Neon Postgres (free tier)**. Os anexos
(fotos, laudos, manuais) ficam gravados **no próprio banco** (tabela
`arquivos_storage`) porque o filesystem do Vercel é efêmero.

---

## 1. Criar o banco no Neon (grátis)

1. Crie uma conta em <https://neon.tech> (pode logar com GitHub).
2. Crie um projeto (ex.: `gec`). Região sugerida: `AWS US East (Ohio)` ou a
   mais barata disponível.
3. Copie a **connection string** do painel (botão *Connect*). Ela é parecida com:
   ```
   postgresql://usuario:senha@ep-xxxx-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   Guarde — é a `DATABASE_URL`. Se o painel oferecer "*Pooled connection*",
   prefira essa (aguenta melhor os acessos curtos do serverless).

## 2. Gerar a SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Publicar na Vercel

1. Faça push deste repositório pro GitHub (se ainda não estiver).
2. Em <https://vercel.com> → **Add New… → Project** → importe o repositório.
3. Em **Configure Project**:
   - Framework Preset: **Other**
   - Build Command: *(vazio)* · Output Directory: *(vazio)*
   - Em **Environment Variables**, adicione:

   | Nome | Valor |
   |---|---|
   | `DATABASE_URL` | connection string do Neon (passo 1) |
   | `GEC_SECRET_KEY` | chave gerada no passo 2 |
   | `GEC_STORAGE_BACKEND` | `db` |
   | `GEC_ORG_NOME` | *(opcional)* nome da organização |

4. Clique em **Deploy**. Na primeira visita ao site, o sistema cria as 68
   tabelas sozinho (leva alguns segundos).
5. Abra `/auth/registrar`: **o primeiro usuário criado vira administrador**.

> Alternativa via terminal: `npm i -g vercel && vercel` na raiz do projeto
> (as variáveis de ambiente são configuráveis com `vercel env add`).

## 4. Trabalhar com dados locais existentes

Se o seu `database/gec.db` (SQLite) já tem cadastros e você quiser levá-los:

```bash
set DATABASE_URL=postgresql://...   # Windows (cmd)
export DATABASE_URL=postgresql://...  # Linux/Mac
python scripts/migrar_sqlite_para_postgres.py
```

O script copia **todas as tabelas**, incluindo o conteúdo dos anexos para
`arquivos_storage`. Rode **uma única vez**, contra o banco vazio.

## 5. Atualizações de código

Só fazer push no GitHub: a Vercel redespliega sozinha. Se `schema.sql` ganhar
tabelas/colunas novas, o sistema aplica as colunas novas no próximo cold start
(`db.COLUNAS_NOVAS`) — e tabelas novas entram quando o banco é recriado. Para
forçar a criação de tabela nova num banco que já existe, rode
`database/schema_postgres.sql` manualmente no console SQL do Neon
(o script é idempotente — só `CREATE TABLE IF NOT EXISTS`).

---

## Limites e observações do plano grátis

| Limitação | Impacto no GEC |
|---|---|
| **Body de 4,5 MB** por request (limite da Vercel) | Uploads maiores que isso falham com erro 413. Fotos e PDFs pequenos ok; evite anexar arquivos muito grandes |
| **Cold start** (~1–3 s na 1ª visita após inatividade) | Perceptível só no primeiro acesso do dia/período |
| **Funções de até 10 s** (Hobby) | As telas do GEC respondem em milissegundos; ok pra uso normal |
| **Sem execução em segundo plano** | O "Agendador de relatórios" (agendamentos_relatorio) continua existindo, mas quem envia/executa é a visita do usuário ao sistema |
| **Neon autosuspend** (banco "dorme" após 5 min sem uso) | Só adiciona ~0,5 s ao primeiro acesso; não pausa como o Supabase |
| **Hobby = uso não-comercial** | Não use para a fundação/empresa no plano grátis |

## Como rodar localmente (como sempre funcionou)

```
iniciar.bat            (Windows)
python app.py          (qualquer SO, com pip install -r requirements.txt)
```

Sem variáveis de ambiente, o sistema usa SQLite em `database/gec.db` e grava
anexos em `static/uploads` — exatamente como antes.

## Como testar localmente com Postgres (opcional, simula a Vercel)

```python
# roda o app + um Postgres temporário, sem instalar nada
import pgserver, os
os.environ["DATABASE_URL"] = pgserver.get_server("/tmp/pgdata_gec").get_uri()
os.environ["GEC_STORAGE_BACKEND"] = "db"
from app import app
app.run(debug=True)
```

## Arquivos que fazem a mágica do deploy

| Arquivo | Papel |
|---|---|
| `api/index.py` | Entrypoint WSGI que o Vercel executa |
| `vercel.json` | Manda todas as rotas pra função Python |
| `.vercelignore` | Deixa o bundle enxuto (.venv, .git, POCs) |
| `db.py` → `_traduzir_sql` | Traduz queries SQLite→Postgres na hora (`?`→`%s`, `datetime('now',...)`→`to_char(...)`, `strftime`→`to_char`) |
| `db.py` → `init_db` | No Postgres, só roda o schema completo se o banco estiver vazio (cold start rápido) |
| `utils.py` → `salvar_arquivo` | Com `GEC_STORAGE_BACKEND=db`, grava o anexo no banco em vez de disco |
| `scripts/gerar_schema_postgres.py` | Regenera `schema_postgres.sql` (FKs viram `ALTER TABLE` no final, `BLOB`→`BYTEA`) |

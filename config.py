import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    NOME_ORGANIZACAO = os.environ.get("GEC_ORG_NOME", "Fundação Altino Ventura")
    SECRET_KEY = os.environ.get("GEC_SECRET_KEY", "dev-secret-key-troque-em-producao-0192837465")
    DATABASE_PATH = os.environ.get("GEC_DATABASE_PATH", str(BASE_DIR / "database" / "gec.db"))
    SCHEMA_PATH = str(BASE_DIR / "database" / "schema.sql")
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    # "fs" (padrão): grava em static/uploads — local/docker.
    # "db": grava na tabela arquivos_storage e serve via /static/uploads/<nome> —
    # usado em deploy serverless (Vercel), onde o filesystem é efêmero.
    STORAGE_BACKEND = os.environ.get("GEC_STORAGE_BACKEND", "fs")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB por upload
    EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx", "xls", "xlsx"}

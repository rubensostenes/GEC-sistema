import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    NOME_ORGANIZACAO = os.environ.get("GEC_ORG_NOME", "Fundação Altino Ventura")
    SECRET_KEY = os.environ.get("GEC_SECRET_KEY", "dev-secret-key-troque-em-producao-0192837465")
    DATABASE_PATH = os.environ.get("GEC_DATABASE_PATH", str(BASE_DIR / "database" / "gec.db"))
    SCHEMA_PATH = str(BASE_DIR / "database" / "schema.sql")
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB por upload
    EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx", "xls", "xlsx"}

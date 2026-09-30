import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename


def extensao_permitida(nome_arquivo):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in current_app.config["EXTENSOES_PERMITIDAS"]
    )


def salvar_arquivo(arquivo):
    """Salva um arquivo enviado por upload e retorna (nome_original, caminho_relativo)."""
    if not arquivo or not arquivo.filename:
        return None, None
    if not extensao_permitida(arquivo.filename):
        raise ValueError("Tipo de arquivo não permitido.")

    nome_original = secure_filename(arquivo.filename)
    extensao = nome_original.rsplit(".", 1)[1].lower()
    nome_unico = f"{uuid.uuid4().hex}.{extensao}"
    caminho_relativo = f"uploads/{nome_unico}"

    if current_app.config.get("STORAGE_BACKEND") == "db":
        # Guarda o conteúdo na tabela arquivos_storage (mesma transação da
        # chamadora, que faz commit depois). A leitura é feita pela rota
        # /static/uploads/<nome> registrada em app.py.
        from db import get_db

        db = get_db()
        db.execute(
            "INSERT INTO arquivos_storage (nome, nome_original, conteudo) VALUES (?, ?, ?)",
            (nome_unico, nome_original, arquivo.read()),
        )
        return nome_original, caminho_relativo

    pasta = Path(current_app.config["UPLOAD_FOLDER"])
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_completo = pasta / nome_unico
    arquivo.save(caminho_completo)

    return nome_original, caminho_relativo


def gerar_numero_os(db):
    ano = datetime.now().year
    ultimo = db.execute(
        "SELECT numero FROM ordens_servico WHERE numero LIKE ? ORDER BY id DESC LIMIT 1",
        (f"OS-{ano}-%",),
    ).fetchone()
    if ultimo is None:
        proximo = 1
    else:
        proximo = int(ultimo["numero"].split("-")[-1]) + 1
    return f"OS-{ano}-{proximo:04d}"


PREFIXOS_PROCEDIMENTO = {"preventiva": "PTMP", "calibracao": "PTCA", "inspecao": "INSP"}


def gerar_codigo_procedimento(db, tipo):
    prefixo = PREFIXOS_PROCEDIMENTO.get(tipo, "PROC")
    ultimo = db.execute(
        "SELECT codigo FROM procedimentos_manutencao WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefixo}%",),
    ).fetchone()
    if ultimo is None or not ultimo["codigo"]:
        proximo = 1
    else:
        try:
            proximo = int(ultimo["codigo"][len(prefixo):]) + 1
        except ValueError:
            proximo = 1
    return f"{prefixo}{proximo:04d}"


def somar_meses(data_str, meses):
    if not data_str or not meses:
        return None
    try:
        d = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    mes = d.month - 1 + int(meses)
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, 28)
    return date(ano, mes, dia).isoformat()


def dias_ate(data_str):
    if not data_str:
        return None
    try:
        d = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - date.today()).days

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import admin_required
from db import get_db

bp = Blueprint("configuracao", __name__, url_prefix="/configuracao")


def _registrar_log(db, entidade, acao, detalhe=None):
    db.execute(
        "INSERT INTO log_dados_sistema (usuario_id, entidade, acao, detalhe) VALUES (?,?,?,?)",
        (current_user.id, entidade, acao, detalhe),
    )


# ===================== GRUPOS DE USUÁRIOS =====================
@bp.route("/grupos-usuarios", methods=["GET", "POST"])
@login_required
@admin_required
def grupos_usuarios():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if nome:
            try:
                db.execute(
                    "INSERT INTO grupos_usuarios (nome, descricao) VALUES (?, ?)",
                    (nome, request.form.get("descricao", "").strip()),
                )
                db.commit()
                flash("Grupo cadastrado.", "sucesso")
            except Exception:
                flash("Já existe um grupo com este nome.", "erro")
        return redirect(url_for("configuracao.grupos_usuarios"))

    lista = db.execute(
        """SELECT g.*, (SELECT COUNT(*) FROM usuarios u WHERE u.grupo_id = g.id) AS total_usuarios
           FROM grupos_usuarios g ORDER BY g.nome"""
    ).fetchall()
    return render_template("configuracao/grupos_usuarios.html", grupos=lista)


# ===================== EMPRESA =====================
@bp.route("/empresa", methods=["GET", "POST"])
@login_required
@admin_required
def empresa():
    db = get_db()
    registro = db.execute("SELECT * FROM empresa ORDER BY id LIMIT 1").fetchone()

    if request.method == "POST":
        dados = (
            request.form.get("nome", "").strip(),
            request.form.get("cnpj", "").strip(),
            request.form.get("endereco", "").strip(),
            request.form.get("telefone", "").strip(),
            request.form.get("email", "").strip(),
        )
        if registro:
            db.execute(
                """UPDATE empresa SET nome=?, cnpj=?, endereco=?, telefone=?, email=?,
                   atualizado_em=datetime('now','localtime') WHERE id=?""",
                dados + (registro["id"],),
            )
        else:
            db.execute("INSERT INTO empresa (nome, cnpj, endereco, telefone, email) VALUES (?,?,?,?,?)", dados)
        _registrar_log(db, "empresa", "atualizar", dados[0])
        db.commit()
        flash("Dados da empresa atualizados.", "sucesso")
        return redirect(url_for("configuracao.empresa"))

    return render_template("configuracao/empresa.html", empresa=registro)


# ===================== ALERTA GERAL =====================
@bp.route("/alertas", methods=["GET", "POST"])
@login_required
@admin_required
def alertas():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO alertas_gerais (titulo, mensagem, criado_por) VALUES (?,?,?)",
            (request.form.get("titulo", "").strip(), request.form.get("mensagem", "").strip(), current_user.id),
        )
        db.commit()
        flash("Alerta publicado para todos os usuários.", "sucesso")
        return redirect(url_for("configuracao.alertas"))

    lista = db.execute("SELECT * FROM alertas_gerais ORDER BY criado_em DESC").fetchall()
    return render_template("configuracao/alertas.html", alertas=lista)


@bp.route("/alertas/<int:alerta_id>/alternar", methods=["POST"])
@login_required
@admin_required
def alternar_alerta(alerta_id):
    db = get_db()
    alerta = db.execute("SELECT * FROM alertas_gerais WHERE id = ?", (alerta_id,)).fetchone()
    if alerta:
        db.execute("UPDATE alertas_gerais SET ativo = ? WHERE id = ?", (0 if alerta["ativo"] else 1, alerta_id))
        db.commit()
        flash("Alerta atualizado.", "sucesso")
    return redirect(url_for("configuracao.alertas"))


# ===================== CATÁLOGOS: UNIDADES DE MEDIDA, FERIADOS, LABELS =====================
@bp.route("/unidades-medida", methods=["GET", "POST"])
@login_required
@admin_required
def unidades_medida():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        simbolo = request.form.get("simbolo", "").strip()
        if nome and simbolo:
            try:
                db.execute("INSERT INTO unidades_medida (nome, simbolo) VALUES (?, ?)", (nome, simbolo))
                db.commit()
                flash("Unidade de medida cadastrada.", "sucesso")
            except Exception:
                flash("Já existe uma unidade de medida com este nome.", "erro")
        return redirect(url_for("configuracao.unidades_medida"))

    lista = db.execute("SELECT * FROM unidades_medida ORDER BY nome").fetchall()
    return render_template("configuracao/unidades_medida.html", unidades_medida=lista)


@bp.route("/feriados", methods=["GET", "POST"])
@login_required
@admin_required
def feriados():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO feriados (data, descricao, unidade_id) VALUES (?,?,?)",
                (request.form.get("data"), request.form.get("descricao", "").strip(), request.form.get("unidade_id") or None),
            )
            db.commit()
            flash("Feriado cadastrado.", "sucesso")
        except Exception:
            flash("Já existe um feriado nesta data para esta unidade.", "erro")
        return redirect(url_for("configuracao.feriados"))

    lista = db.execute(
        """SELECT f.*, u.nome AS unidade_nome FROM feriados f
           LEFT JOIN unidades u ON u.id = f.unidade_id ORDER BY f.data"""
    ).fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    return render_template("configuracao/feriados.html", feriados=lista, unidades=unidades)


@bp.route("/labels", methods=["GET", "POST"])
@login_required
@admin_required
def labels():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if nome:
            try:
                db.execute(
                    "INSERT INTO labels (nome, cor) VALUES (?, ?)", (nome, request.form.get("cor", "#2f80c4"))
                )
                db.commit()
                flash("Label cadastrada.", "sucesso")
            except Exception:
                flash("Já existe uma label com este nome.", "erro")
        return redirect(url_for("configuracao.labels"))

    lista = db.execute("SELECT * FROM labels ORDER BY nome").fetchall()
    return render_template("configuracao/labels.html", labels=lista)


# ===================== PARÂMETROS =====================
@bp.route("/parametros-locais", methods=["GET", "POST"])
@login_required
@admin_required
def parametros_locais():
    db = get_db()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO parametros_locais (unidade_id, chave, valor) VALUES (?,?,?)",
                (request.form.get("unidade_id"), request.form.get("chave", "").strip(), request.form.get("valor", "").strip()),
            )
            db.commit()
            flash("Parâmetro salvo.", "sucesso")
        except Exception:
            flash("Já existe esse parâmetro para esta unidade.", "erro")
        return redirect(url_for("configuracao.parametros_locais"))

    lista = db.execute(
        """SELECT p.*, u.nome AS unidade_nome FROM parametros_locais p
           JOIN unidades u ON u.id = p.unidade_id ORDER BY u.nome, p.chave"""
    ).fetchall()
    return render_template("configuracao/parametros_locais.html", parametros=lista, unidades=unidades)


@bp.route("/parametros-globais", methods=["GET", "POST"])
@login_required
@admin_required
def parametros_globais():
    return _parametros_genericos(
        "parametros_globais", "configuracao.parametros_globais", "Parâmetros Globais", "Configurações gerais do sistema"
    )


@bp.route("/parametros-calibracao", methods=["GET", "POST"])
@login_required
@admin_required
def parametros_calibracao():
    return _parametros_genericos(
        "parametros_calibracao",
        "configuracao.parametros_calibracao",
        "Parâmetros de Calibração",
        "Tolerâncias e regras padrão usadas nos planos de calibração",
    )


def _parametros_genericos(tabela, endpoint, titulo, subtitulo):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                f"INSERT INTO {tabela} (chave, valor, descricao) VALUES (?,?,?)",
                (request.form.get("chave", "").strip(), request.form.get("valor", "").strip(), request.form.get("descricao", "").strip()),
            )
            db.commit()
            flash("Parâmetro salvo.", "sucesso")
        except Exception:
            flash("Já existe um parâmetro com esta chave.", "erro")
        return redirect(url_for(endpoint))

    lista = db.execute(f"SELECT * FROM {tabela} ORDER BY chave").fetchall()
    return render_template("configuracao/parametros_genericos.html", parametros=lista, titulo=titulo, subtitulo=subtitulo)


# ===================== CONFIGURAÇÕES DE SENHA E LISTAGEM =====================
@bp.route("/senha", methods=["GET", "POST"])
@login_required
@admin_required
def config_senha():
    db = get_db()
    registro = db.execute("SELECT * FROM config_senha ORDER BY id LIMIT 1").fetchone()

    if request.method == "POST":
        dados = (
            int(request.form.get("comprimento_minimo", 6) or 6),
            1 if request.form.get("exigir_numero") else 0,
            1 if request.form.get("exigir_maiusculo") else 0,
            request.form.get("dias_expiracao") or None,
        )
        if registro:
            db.execute(
                "UPDATE config_senha SET comprimento_minimo=?, exigir_numero=?, exigir_maiusculo=?, dias_expiracao=? WHERE id=?",
                dados + (registro["id"],),
            )
        else:
            db.execute(
                "INSERT INTO config_senha (comprimento_minimo, exigir_numero, exigir_maiusculo, dias_expiracao) VALUES (?,?,?,?)",
                dados,
            )
        db.commit()
        flash("Política de senha atualizada e já é aplicada na criação e troca de senhas.", "sucesso")
        return redirect(url_for("configuracao.config_senha"))

    return render_template("configuracao/config_senha.html", config=registro)


@bp.route("/listagem", methods=["GET", "POST"])
@login_required
@admin_required
def config_listagem():
    db = get_db()
    registro = db.execute("SELECT * FROM config_listagem ORDER BY id LIMIT 1").fetchone()

    if request.method == "POST":
        itens = int(request.form.get("itens_por_pagina", 25) or 25)
        if registro:
            db.execute("UPDATE config_listagem SET itens_por_pagina = ? WHERE id = ?", (itens, registro["id"]))
        else:
            db.execute("INSERT INTO config_listagem (itens_por_pagina) VALUES (?)", (itens,))
        db.commit()
        flash("Configuração de listagem salva. (Ainda não aplicada às tabelas — hoje elas mostram tudo sem paginação.)", "sucesso")
        return redirect(url_for("configuracao.config_listagem"))

    return render_template("configuracao/config_listagem.html", config=registro)


# ===================== LICENÇAS, ACESSOS E LOGS =====================
@bp.route("/licencas")
@login_required
@admin_required
def licencas():
    db = get_db()
    total_usuarios = db.execute("SELECT COUNT(*) AS c FROM usuarios WHERE ativo = 1").fetchone()["c"]
    por_cargo = db.execute("SELECT cargo, COUNT(*) AS total FROM usuarios WHERE ativo = 1 GROUP BY cargo").fetchall()
    return render_template("configuracao/licencas.html", total_usuarios=total_usuarios, por_cargo=por_cargo)


@bp.route("/acessos-falhos")
@login_required
@admin_required
def acessos_falhos():
    db = get_db()
    lista = db.execute("SELECT * FROM acessos_falhos ORDER BY criado_em DESC LIMIT 200").fetchall()
    return render_template("configuracao/acessos_falhos.html", acessos=lista)


@bp.route("/log-dados")
@login_required
@admin_required
def log_dados():
    db = get_db()
    lista = db.execute(
        """SELECT l.*, u.nome AS usuario_nome FROM log_dados_sistema l
           LEFT JOIN usuarios u ON u.id = l.usuario_id ORDER BY l.criado_em DESC LIMIT 200"""
    ).fetchall()
    return render_template("configuracao/log_dados.html", eventos=lista)


@bp.route("/log-acessos")
@login_required
@admin_required
def log_acessos():
    db = get_db()
    lista = db.execute(
        """SELECT l.*, u.nome AS usuario_nome, u.email FROM log_acessos l
           LEFT JOIN usuarios u ON u.id = l.usuario_id ORDER BY l.criado_em DESC LIMIT 200"""
    ).fetchall()
    return render_template("configuracao/log_acessos.html", acessos=lista)

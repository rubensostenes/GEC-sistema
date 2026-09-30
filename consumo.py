from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from db import get_db

bp = Blueprint("consumo", __name__, url_prefix="/consumo")


# ===================== GRUPOS DE TABELAS DE ACOMPANHAMENTO =====================
@bp.route("/grupos", methods=["GET", "POST"])
@login_required
def grupos():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if nome:
            try:
                db.execute(
                    "INSERT INTO grupos_consumo (nome, descricao) VALUES (?, ?)",
                    (nome, request.form.get("descricao", "").strip()),
                )
                db.commit()
                flash("Grupo cadastrado.", "sucesso")
            except Exception:
                flash("Já existe um grupo com este nome.", "erro")
        return redirect(url_for("consumo.grupos"))
    lista = db.execute(
        """SELECT g.*, (SELECT COUNT(*) FROM tabelas_consumo t WHERE t.grupo_id = g.id) AS total_tabelas
           FROM grupos_consumo g ORDER BY g.nome"""
    ).fetchall()
    return render_template("consumo/grupos.html", grupos=lista)


# ===================== TABELAS DE ACOMPANHAMENTO DE CONSUMO =====================
@bp.route("/tabelas")
@login_required
def tabelas():
    db = get_db()
    lista = db.execute(
        """SELECT t.*, g.nome AS grupo_nome, u.nome AS unidade_nome FROM tabelas_consumo t
           LEFT JOIN grupos_consumo g ON g.id = t.grupo_id
           LEFT JOIN unidades u ON u.id = t.unidade_id
           WHERE t.ativo = 1 ORDER BY t.nome"""
    ).fetchall()
    return render_template("consumo/tabelas.html", tabelas=lista)


@bp.route("/tabelas/nova", methods=["GET", "POST"])
@login_required
def nova_tabela():
    db = get_db()
    grupos_lista = db.execute("SELECT id, nome FROM grupos_consumo ORDER BY nome").fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        db.execute(
            "INSERT INTO tabelas_consumo (grupo_id, nome, unidade_id, unidade_medida) VALUES (?,?,?,?)",
            (
                request.form.get("grupo_id") or None,
                request.form.get("nome", "").strip(),
                request.form.get("unidade_id") or None,
                request.form.get("unidade_medida", "un").strip(),
            ),
        )
        db.commit()
        flash("Tabela de acompanhamento cadastrada.", "sucesso")
        return redirect(url_for("consumo.tabelas"))
    return render_template("consumo/form_tabela.html", grupos=grupos_lista, unidades=unidades)


# ===================== INFORMAÇÕES DE CONSUMO (leituras periódicas) =====================
@bp.route("/informacoes", methods=["GET", "POST"])
@login_required
def informacoes():
    db = get_db()
    tabelas_lista = db.execute("SELECT id, nome, unidade_medida FROM tabelas_consumo WHERE ativo = 1 ORDER BY nome").fetchall()

    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO informacoes_consumo (tabela_id, periodo, valor, observacao) VALUES (?,?,?,?)",
                (
                    request.form.get("tabela_id"),
                    request.form.get("periodo"),
                    float(request.form.get("valor", "0") or 0),
                    request.form.get("observacao", "").strip(),
                ),
            )
            db.commit()
            flash("Consumo registrado.", "sucesso")
        except Exception:
            flash("Já existe um registro de consumo para esta tabela neste período.", "erro")
        return redirect(url_for("consumo.informacoes"))

    lista = db.execute(
        """SELECT i.*, t.nome AS tabela_nome, t.unidade_medida FROM informacoes_consumo i
           JOIN tabelas_consumo t ON t.id = i.tabela_id ORDER BY i.periodo DESC LIMIT 100"""
    ).fetchall()
    return render_template("consumo/informacoes.html", informacoes=lista, tabelas=tabelas_lista)


# ===================== METAS DE CONSUMO =====================
@bp.route("/metas", methods=["GET", "POST"])
@login_required
def metas():
    db = get_db()
    tabelas_lista = db.execute("SELECT id, nome, unidade_medida FROM tabelas_consumo WHERE ativo = 1 ORDER BY nome").fetchall()

    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO metas_consumo (tabela_id, periodo, valor_meta) VALUES (?,?,?)",
                (request.form.get("tabela_id"), request.form.get("periodo"), float(request.form.get("valor_meta", "0") or 0)),
            )
            db.commit()
            flash("Meta cadastrada.", "sucesso")
        except Exception:
            flash("Já existe uma meta para esta tabela neste período.", "erro")
        return redirect(url_for("consumo.metas"))

    lista = db.execute(
        """SELECT m.*, t.nome AS tabela_nome, t.unidade_medida FROM metas_consumo m
           JOIN tabelas_consumo t ON t.id = m.tabela_id ORDER BY m.periodo DESC LIMIT 100"""
    ).fetchall()
    return render_template("consumo/metas.html", metas=lista, tabelas=tabelas_lista)


# ===================== RELATÓRIOS =====================
@bp.route("/relatorios")
@login_required
def relatorios():
    db = get_db()
    comparativo = db.execute(
        """SELECT t.nome AS tabela_nome, t.unidade_medida, i.periodo, i.valor AS realizado, m.valor_meta
           FROM informacoes_consumo i
           JOIN tabelas_consumo t ON t.id = i.tabela_id
           LEFT JOIN metas_consumo m ON m.tabela_id = i.tabela_id AND m.periodo = i.periodo
           ORDER BY i.periodo DESC LIMIT 100"""
    ).fetchall()
    return render_template("consumo/relatorios.html", comparativo=comparativo)

import time

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db

bp = Blueprint("ajuda", __name__, url_prefix="/ajuda")


@bp.route("/manual")
@login_required
def manual():
    return render_template("ajuda/manual.html")


@bp.route("/documentacao")
@login_required
def documentacao():
    from db import USANDO_POSTGRES

    db = get_db()
    if USANDO_POSTGRES:
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = 'public'"
    else:
        sql = "SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    total_tabelas = db.execute(sql).fetchone()["c"]
    return render_template("ajuda/documentacao.html", total_tabelas=total_tabelas)


@bp.route("/sobre")
@login_required
def sobre():
    return render_template("ajuda/sobre.html")


@bp.route("/area-cliente")
@login_required
def area_cliente():
    return render_template(
        "ajuda/em_construcao.html",
        titulo="Área do Cliente",
        descricao="O GEC é um sistema próprio, feito sob medida — não existe uma empresa fornecedora externa com portal de suporte/contrato para acessar aqui.",
    )


# ===================== TESTE DE VELOCIDADE =====================
@bp.route("/teste-velocidade")
@login_required
def teste_velocidade():
    return render_template("ajuda/teste_velocidade.html")


@bp.route("/teste-velocidade/ping")
@login_required
def ping():
    inicio = time.perf_counter()
    db = get_db()
    db.execute("SELECT COUNT(*) FROM equipamentos").fetchone()
    duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)
    return jsonify({"servidor_ms": duracao_ms})


# ===================== BANCO DE IDEIAS =====================
@bp.route("/ideias", methods=["GET", "POST"])
@login_required
def ideias():
    db = get_db()
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        if not titulo:
            flash("Dê um título para a ideia.", "erro")
        else:
            db.execute(
                "INSERT INTO ideias (usuario_id, titulo, descricao) VALUES (?,?,?)",
                (current_user.id, titulo, request.form.get("descricao", "").strip()),
            )
            db.commit()
            flash("Ideia registrada. Obrigado pela contribuição!", "sucesso")
        return redirect(url_for("ajuda.ideias"))

    lista = db.execute(
        """SELECT i.*, u.nome AS autor_nome,
                  (SELECT COUNT(*) FROM ideia_votos v WHERE v.ideia_id = i.id) AS total_votos,
                  EXISTS(SELECT 1 FROM ideia_votos v WHERE v.ideia_id = i.id AND v.usuario_id = ?) AS ja_votei
           FROM ideias i LEFT JOIN usuarios u ON u.id = i.usuario_id
           ORDER BY total_votos DESC, i.criado_em DESC""",
        (current_user.id,),
    ).fetchall()
    return render_template("ajuda/ideias.html", ideias=lista)


@bp.route("/ideias/<int:ideia_id>/votar", methods=["POST"])
@login_required
def votar_ideia(ideia_id):
    db = get_db()
    try:
        db.execute("INSERT INTO ideia_votos (ideia_id, usuario_id) VALUES (?,?)", (ideia_id, current_user.id))
        db.commit()
    except Exception:
        pass
    return redirect(url_for("ajuda.ideias"))


@bp.route("/ideias/<int:ideia_id>/status", methods=["POST"])
@login_required
def atualizar_status_ideia(ideia_id):
    if not current_user.is_admin:
        flash("Apenas administradores podem mudar o status de uma ideia.", "erro")
        return redirect(url_for("ajuda.ideias"))
    db = get_db()
    novo_status = request.form.get("status")
    if novo_status in ("nova", "em_analise", "aprovada", "rejeitada", "implementada"):
        db.execute("UPDATE ideias SET status = ? WHERE id = ?", (novo_status, ideia_id))
        db.commit()
    return redirect(url_for("ajuda.ideias"))

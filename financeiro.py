from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from db import get_db

bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")


@bp.route("/")
@login_required
def resumo():
    db = get_db()

    total_mes = db.execute(
        """SELECT COALESCE(SUM(custo_pecas + custo_mao_obra), 0) AS total FROM ordens_servico
           WHERE strftime('%Y-%m', data_abertura) = strftime('%Y-%m','now','localtime')"""
    ).fetchone()["total"]

    total_geral = db.execute(
        "SELECT COALESCE(SUM(custo_pecas + custo_mao_obra), 0) AS total FROM ordens_servico"
    ).fetchone()["total"]

    total_pecas = db.execute("SELECT COALESCE(SUM(custo_pecas), 0) AS total FROM ordens_servico").fetchone()["total"]
    total_mao_obra = db.execute("SELECT COALESCE(SUM(custo_mao_obra), 0) AS total FROM ordens_servico").fetchone()["total"]

    por_unidade = db.execute(
        """SELECT u.nome, COALESCE(SUM(os.custo_pecas + os.custo_mao_obra), 0) AS total
           FROM ordens_servico os
           JOIN equipamentos e ON e.id = os.equipamento_id
           JOIN unidades u ON u.id = e.unidade_id
           GROUP BY u.id HAVING total > 0 ORDER BY total DESC"""
    ).fetchall()

    maiores_custos = db.execute(
        """SELECT os.numero, os.id, os.tipo, os.data_abertura, e.nome AS equipamento_nome,
                  (os.custo_pecas + os.custo_mao_obra) AS custo_total
           FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           WHERE (os.custo_pecas + os.custo_mao_obra) > 0
           ORDER BY custo_total DESC LIMIT 10"""
    ).fetchall()

    return render_template(
        "financeiro/resumo.html",
        total_mes=total_mes,
        total_geral=total_geral,
        total_pecas=total_pecas,
        total_mao_obra=total_mao_obra,
        por_unidade=por_unidade,
        maiores_custos=maiores_custos,
    )


@bp.route("/consumo")
@login_required
def consumo():
    db = get_db()
    termo = request.args.get("q", "").strip()

    sql = """SELECT osp.*, p.nome AS peca_nome, p.unidade_medida, os.numero AS os_numero,
                     os.data_abertura, e.nome AS equipamento_nome
              FROM ordem_servico_pecas osp
              JOIN pecas_estoque p ON p.id = osp.peca_id
              JOIN ordens_servico os ON os.id = osp.ordem_servico_id
              LEFT JOIN equipamentos e ON e.id = os.equipamento_id
              WHERE 1=1"""
    params = []
    if termo:
        sql += " AND (p.nome LIKE ? OR os.numero LIKE ? OR e.nome LIKE ?)"
        curinga = f"%{termo}%"
        params += [curinga, curinga, curinga]
    sql += " ORDER BY os.data_abertura DESC"

    consumos = db.execute(sql, params).fetchall()

    mais_consumidas = db.execute(
        """SELECT p.nome, p.unidade_medida, SUM(osp.quantidade) AS total_consumido
           FROM ordem_servico_pecas osp JOIN pecas_estoque p ON p.id = osp.peca_id
           GROUP BY p.id ORDER BY total_consumido DESC LIMIT 8"""
    ).fetchall()

    return render_template(
        "financeiro/consumo.html", consumos=consumos, mais_consumidas=mais_consumidas, termo=termo
    )


# ===================== CENTROS DE CUSTO / LUCRO =====================
@bp.route("/centros-custo", methods=["GET", "POST"])
@login_required
def centros_custo():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if nome:
            try:
                db.execute(
                    "INSERT INTO centros_custo (nome, unidade_id, tipo) VALUES (?,?,?)",
                    (nome, request.form.get("unidade_id") or None, request.form.get("tipo", "custo")),
                )
                db.commit()
                flash("Centro cadastrado.", "sucesso")
            except Exception:
                flash("Já existe um centro com este nome.", "erro")
        return redirect(url_for("financeiro.centros_custo"))

    lista = db.execute(
        """SELECT c.*, u.nome AS unidade_nome,
                  (SELECT COALESCE(SUM(custo_pecas + custo_mao_obra), 0) FROM ordens_servico WHERE centro_custo_id = c.id) AS total_gasto
           FROM centros_custo c LEFT JOIN unidades u ON u.id = c.unidade_id ORDER BY c.nome"""
    ).fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    return render_template("financeiro/centros_custo.html", centros=lista, unidades=unidades)


# ===================== CADASTROS BÁSICOS =====================
@bp.route("/cadastros-basicos")
@login_required
def cadastros_basicos():
    return render_template("financeiro/cadastros_basicos.html")


# ===================== RELATÓRIOS =====================
@bp.route("/relatorios")
@login_required
def relatorios():
    return render_template("financeiro/relatorios.html")

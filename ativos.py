from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db

bp = Blueprint("ativos", __name__, url_prefix="/equipamentos-gestao")


# ===================== BUSCA DE EQUIPAMENTOS (avançada) =====================
@bp.route("/busca")
@login_required
def busca():
    db = get_db()
    fabricantes = db.execute("SELECT id, nome FROM fabricantes WHERE ativo = 1 ORDER BY nome").fetchall()
    categorias = db.execute(
        "SELECT DISTINCT categoria FROM equipamentos WHERE categoria IS NOT NULL ORDER BY categoria"
    ).fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    return render_template("ativos/busca.html", fabricantes=fabricantes, categorias=categorias, unidades=unidades)


# ===================== PLANO DE DESCRIÇÕES =====================
@bp.route("/plano-descricoes", methods=["GET", "POST"])
@login_required
def plano_descricoes():
    db = get_db()
    if request.method == "POST":
        categoria = request.form.get("categoria", "").strip()
        descricao_padrao = request.form.get("descricao_padrao", "").strip()
        if categoria and descricao_padrao:
            try:
                db.execute(
                    "INSERT INTO plano_descricoes (categoria, descricao_padrao) VALUES (?, ?)",
                    (categoria, descricao_padrao),
                )
                db.commit()
                flash("Descrição padrão cadastrada.", "sucesso")
            except Exception:
                flash("Já existe uma descrição padrão para esta categoria.", "erro")
        return redirect(url_for("ativos.plano_descricoes"))

    lista = db.execute("SELECT * FROM plano_descricoes ORDER BY categoria").fetchall()
    return render_template("ativos/plano_descricoes.html", planos=lista)


# ===================== FABRICANTES =====================
@bp.route("/fabricantes")
@login_required
def fabricantes():
    db = get_db()
    lista = db.execute(
        """SELECT f.*, (SELECT COUNT(*) FROM modelos m WHERE m.fabricante_id = f.id) AS total_modelos
           FROM fabricantes f ORDER BY f.nome"""
    ).fetchall()
    return render_template("ativos/fabricantes.html", fabricantes=lista)


@bp.route("/fabricantes/novo", methods=["GET", "POST"])
@login_required
def novo_fabricante():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Informe o nome do fabricante.", "erro")
            return render_template("ativos/form_fabricante.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO fabricantes (nome, site, contato, telefone) VALUES (?,?,?,?)",
                (nome, request.form.get("site", "").strip(), request.form.get("contato", "").strip(),
                 request.form.get("telefone", "").strip()),
            )
            db.commit()
            flash("Fabricante cadastrado.", "sucesso")
        except Exception:
            flash("Já existe um fabricante com este nome.", "erro")
            return render_template("ativos/form_fabricante.html")
        return redirect(url_for("ativos.fabricantes"))
    return render_template("ativos/form_fabricante.html")


# ===================== MODELOS =====================
@bp.route("/modelos")
@login_required
def modelos():
    db = get_db()
    lista = db.execute(
        """SELECT mo.*, f.nome AS fabricante_nome FROM modelos mo
           LEFT JOIN fabricantes f ON f.id = mo.fabricante_id ORDER BY mo.nome"""
    ).fetchall()
    return render_template("ativos/modelos.html", modelos=lista)


@bp.route("/modelos/novo", methods=["GET", "POST"])
@login_required
def novo_modelo():
    db = get_db()
    fabricantes_lista = db.execute("SELECT id, nome FROM fabricantes WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Informe o nome do modelo.", "erro")
            return render_template("ativos/form_modelo.html", fabricantes=fabricantes_lista)
        db.execute(
            """INSERT INTO modelos (fabricante_id, nome, categoria, padrao_preferencial) VALUES (?,?,?,?)""",
            (
                request.form.get("fabricante_id") or None,
                nome,
                request.form.get("categoria", "").strip(),
                1 if request.form.get("padrao_preferencial") else 0,
            ),
        )
        db.commit()
        flash("Modelo cadastrado.", "sucesso")
        return redirect(url_for("ativos.modelos"))
    return render_template("ativos/form_modelo.html", fabricantes=fabricantes_lista)


@bp.route("/novos-modelos-fabricantes")
@login_required
def novos_modelos_fabricantes():
    return render_template("ativos/novos_modelos_fabricantes.html")


# ===================== CUSTO DE SUBSTITUIÇÃO =====================
@bp.route("/custo-substituicao")
@login_required
def custo_substituicao():
    db = get_db()
    equipamentos = db.execute(
        """SELECT e.id, e.nome, e.patrimonio, u.nome AS unidade_nome, e.valor_aquisicao, e.valor_reposicao
           FROM equipamentos e LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.status != 'baixado' AND e.valor_reposicao IS NOT NULL
           ORDER BY e.valor_reposicao DESC"""
    ).fetchall()
    total_reposicao = sum(e["valor_reposicao"] for e in equipamentos)
    sem_valor = db.execute(
        "SELECT COUNT(*) AS c FROM equipamentos WHERE status != 'baixado' AND valor_reposicao IS NULL"
    ).fetchone()["c"]
    return render_template(
        "ativos/custo_substituicao.html", equipamentos=equipamentos, total_reposicao=total_reposicao, sem_valor=sem_valor
    )


# ===================== RESERVA DE EQUIPAMENTOS =====================
@bp.route("/reservas")
@login_required
def reservas():
    db = get_db()
    lista = db.execute(
        """SELECT r.*, e.nome AS equipamento_nome FROM reservas_equipamento r
           JOIN equipamentos e ON e.id = r.equipamento_id
           WHERE r.status IN ('reservado', 'em_uso') ORDER BY r.data_inicio"""
    ).fetchall()
    return render_template("ativos/reservas.html", reservas=lista)


@bp.route("/reservas/nova", methods=["GET", "POST"])
@login_required
def nova_reserva():
    db = get_db()
    equipamentos = db.execute("SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO reservas_equipamento (equipamento_id, solicitante, data_inicio, data_fim, observacao, criado_por)
               VALUES (?,?,?,?,?,?)""",
            (
                request.form.get("equipamento_id"),
                request.form.get("solicitante", "").strip(),
                request.form.get("data_inicio"),
                request.form.get("data_fim"),
                request.form.get("observacao", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Reserva registrada.", "sucesso")
        return redirect(url_for("ativos.reservas"))
    return render_template("ativos/form_reserva.html", equipamentos=equipamentos)


@bp.route("/reservas/<int:reserva_id>/devolver", methods=["POST"])
@login_required
def devolver_reserva(reserva_id):
    db = get_db()
    db.execute("UPDATE reservas_equipamento SET status = 'devolvido' WHERE id = ?", (reserva_id,))
    db.commit()
    flash("Equipamento devolvido.", "sucesso")
    return redirect(url_for("ativos.reservas"))


# ===================== TRANSPORTE DE EQUIPAMENTOS =====================
@bp.route("/transportes")
@login_required
def transportes():
    db = get_db()
    lista = db.execute(
        """SELECT t.*, e.nome AS equipamento_nome FROM transportes_equipamento t
           JOIN equipamentos e ON e.id = t.equipamento_id ORDER BY t.data_transporte DESC"""
    ).fetchall()
    return render_template("ativos/transportes.html", transportes=lista)


@bp.route("/transportes/novo", methods=["GET", "POST"])
@login_required
def novo_transporte():
    db = get_db()
    equipamentos = db.execute("SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO transportes_equipamento (equipamento_id, origem, destino, data_transporte, responsavel, observacao, criado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (
                request.form.get("equipamento_id"),
                request.form.get("origem", "").strip(),
                request.form.get("destino", "").strip(),
                request.form.get("data_transporte"),
                request.form.get("responsavel", "").strip(),
                request.form.get("observacao", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Transporte registrado.", "sucesso")
        return redirect(url_for("ativos.transportes"))
    return render_template("ativos/form_transporte.html", equipamentos=equipamentos)


@bp.route("/transportes/<int:transporte_id>/concluir", methods=["POST"])
@login_required
def concluir_transporte(transporte_id):
    db = get_db()
    db.execute("UPDATE transportes_equipamento SET status = 'concluido' WHERE id = ?", (transporte_id,))
    db.commit()
    flash("Transporte marcado como concluído.", "sucesso")
    return redirect(url_for("ativos.transportes"))


# ===================== EQUIPAMENTOS DE TERCEIROS =====================
@bp.route("/terceiros")
@login_required
def terceiros():
    db = get_db()
    lista = db.execute(
        """SELECT e.*, u.nome AS unidade_nome FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.de_terceiros = 1 ORDER BY e.nome"""
    ).fetchall()
    return render_template("ativos/terceiros.html", equipamentos=lista)


# ===================== PADRÕES DE CALIBRAÇÃO =====================
@bp.route("/padroes-preferenciais")
@login_required
def padroes_preferenciais():
    db = get_db()
    lista = db.execute(
        """SELECT e.*, u.nome AS unidade_nome FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.eh_padrao_calibracao = 1 ORDER BY e.nome"""
    ).fetchall()
    return render_template("ativos/padroes.html", equipamentos=lista, modo="preferenciais")


@bp.route("/rastreabilidade-padroes")
@login_required
def rastreabilidade_padroes():
    db = get_db()
    lista = db.execute(
        """SELECT e.*, u.nome AS unidade_nome FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.eh_padrao_calibracao = 1 ORDER BY e.data_validade_rastreabilidade"""
    ).fetchall()
    return render_template("ativos/padroes.html", equipamentos=lista, modo="rastreabilidade", hoje=date.today().isoformat())


# ===================== CONTADORES =====================
@bp.route("/contadores", methods=["GET", "POST"])
@login_required
def contadores():
    db = get_db()
    if request.method == "POST":
        equipamento_id = request.form.get("equipamento_id")
        tipo_contador = request.form.get("tipo_contador", "").strip()
        valor_atual = request.form.get("valor_atual", "0")
        existente = db.execute(
            "SELECT id FROM contadores_equipamento WHERE equipamento_id = ? AND tipo_contador = ?",
            (equipamento_id, tipo_contador),
        ).fetchone()
        if existente:
            db.execute(
                "UPDATE contadores_equipamento SET valor_atual = ?, atualizado_em = datetime('now','localtime'), atualizado_por = ? WHERE id = ?",
                (float(valor_atual), current_user.id, existente["id"]),
            )
        else:
            db.execute(
                """INSERT INTO contadores_equipamento (equipamento_id, tipo_contador, valor_atual, unidade_medida, atualizado_por)
                   VALUES (?,?,?,?,?)""",
                (equipamento_id, tipo_contador, float(valor_atual), request.form.get("unidade_medida", "ciclos"), current_user.id),
            )
        db.commit()
        flash("Contador atualizado.", "sucesso")
        return redirect(url_for("ativos.contadores"))

    equipamentos = db.execute("SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome").fetchall()
    lista = db.execute(
        """SELECT c.*, e.nome AS equipamento_nome FROM contadores_equipamento c
           JOIN equipamentos e ON e.id = c.equipamento_id ORDER BY c.atualizado_em DESC"""
    ).fetchall()
    return render_template("ativos/contadores.html", equipamentos=equipamentos, contadores=lista)


# ===================== EQUIPAMENTOS SEM DATA DE INSTALAÇÃO =====================
@bp.route("/sem-data-instalacao")
@login_required
def sem_data_instalacao():
    db = get_db()
    lista = db.execute(
        """SELECT e.*, u.nome AS unidade_nome FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.data_instalacao IS NULL AND e.status != 'baixado' ORDER BY e.nome"""
    ).fetchall()
    return render_template("ativos/sem_data_instalacao.html", equipamentos=lista)


@bp.route("/cadastros-basicos")
@login_required
def cadastros_basicos():
    return render_template("ativos/cadastros_basicos.html")

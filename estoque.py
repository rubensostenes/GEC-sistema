from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db
from gestao import _csv_response

bp = Blueprint("estoque", __name__, url_prefix="/estoque")


# ===================== SOLICITAÇÕES DE COMPRA =====================
@bp.route("/solicitacoes")
@login_required
def solicitacoes():
    db = get_db()
    lista = db.execute(
        """SELECT s.*, p.nome AS peca_nome, u.nome AS solicitante_nome FROM solicitacoes_compra s
           LEFT JOIN pecas_estoque p ON p.id = s.peca_id
           LEFT JOIN usuarios u ON u.id = s.solicitante_id
           ORDER BY CASE s.status WHEN 'pendente' THEN 0 ELSE 1 END, s.criado_em DESC"""
    ).fetchall()
    return render_template("estoque/solicitacoes.html", solicitacoes=lista)


@bp.route("/solicitacoes/nova", methods=["GET", "POST"])
@login_required
def nova_solicitacao():
    db = get_db()
    pecas = db.execute("SELECT id, nome FROM pecas_estoque ORDER BY nome").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO solicitacoes_compra (peca_id, descricao, quantidade, justificativa, solicitante_id)
               VALUES (?,?,?,?,?)""",
            (
                request.form.get("peca_id") or None,
                request.form.get("descricao", "").strip(),
                float(request.form.get("quantidade", "1") or 1),
                request.form.get("justificativa", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Solicitação de compra registrada.", "sucesso")
        return redirect(url_for("estoque.solicitacoes"))
    return render_template("estoque/form_solicitacao.html", pecas=pecas)


@bp.route("/solicitacoes/<int:solicitacao_id>/status", methods=["POST"])
@login_required
def atualizar_status_solicitacao(solicitacao_id):
    db = get_db()
    novo_status = request.form.get("status")
    if novo_status in ("aprovada", "rejeitada", "comprada"):
        db.execute("UPDATE solicitacoes_compra SET status = ? WHERE id = ?", (novo_status, solicitacao_id))
        db.commit()
        flash("Status da solicitação atualizado.", "sucesso")
    return redirect(url_for("estoque.solicitacoes"))


# ===================== PEDIDOS DE COMPRA =====================
@bp.route("/pedidos")
@login_required
def pedidos():
    db = get_db()
    lista = db.execute(
        """SELECT p.*, f.nome AS fornecedor_nome,
                  (SELECT COALESCE(SUM(quantidade * valor_unitario), 0) FROM pedido_compra_itens WHERE pedido_id = p.id) AS total
           FROM pedidos_compra p LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
           ORDER BY p.data_pedido DESC"""
    ).fetchall()
    return render_template("estoque/pedidos.html", pedidos=lista)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
@login_required
def novo_pedido():
    db = get_db()
    fornecedores = db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        ano = __import__("datetime").date.today().year
        ultimo = db.execute(
            "SELECT numero FROM pedidos_compra WHERE numero LIKE ? ORDER BY id DESC LIMIT 1", (f"PC-{ano}-%",)
        ).fetchone()
        proximo = int(ultimo["numero"].split("-")[-1]) + 1 if ultimo else 1
        numero = f"PC-{ano}-{proximo:04d}"
        cursor = db.execute(
            "INSERT INTO pedidos_compra (numero, fornecedor_id, observacao, criado_por) VALUES (?,?,?,?)",
            (numero, request.form.get("fornecedor_id") or None, request.form.get("observacao", "").strip(), current_user.id),
        )
        db.commit()
        flash(f"Pedido {numero} criado. Adicione os itens.", "sucesso")
        return redirect(url_for("estoque.detalhe_pedido", pedido_id=cursor.lastrowid))
    return render_template("estoque/form_pedido.html", fornecedores=fornecedores)


@bp.route("/pedidos/<int:pedido_id>")
@login_required
def detalhe_pedido(pedido_id):
    db = get_db()
    pedido = db.execute(
        """SELECT p.*, f.nome AS fornecedor_nome FROM pedidos_compra p
           LEFT JOIN fornecedores f ON f.id = p.fornecedor_id WHERE p.id = ?""",
        (pedido_id,),
    ).fetchone()
    if pedido is None:
        flash("Pedido não encontrado.", "erro")
        return redirect(url_for("estoque.pedidos"))
    itens = db.execute(
        """SELECT i.*, p.nome AS peca_nome FROM pedido_compra_itens i
           LEFT JOIN pecas_estoque p ON p.id = i.peca_id WHERE i.pedido_id = ?""",
        (pedido_id,),
    ).fetchall()
    pecas = db.execute("SELECT id, nome FROM pecas_estoque ORDER BY nome").fetchall()
    return render_template("estoque/detalhe_pedido.html", pedido=pedido, itens=itens, pecas=pecas)


@bp.route("/pedidos/<int:pedido_id>/item", methods=["POST"])
@login_required
def adicionar_item_pedido(pedido_id):
    db = get_db()
    db.execute(
        "INSERT INTO pedido_compra_itens (pedido_id, peca_id, descricao, quantidade, valor_unitario) VALUES (?,?,?,?,?)",
        (
            pedido_id,
            request.form.get("peca_id") or None,
            request.form.get("descricao", "").strip(),
            float(request.form.get("quantidade", "1") or 1),
            float(request.form.get("valor_unitario", "0") or 0),
        ),
    )
    db.commit()
    flash("Item adicionado ao pedido.", "sucesso")
    return redirect(url_for("estoque.detalhe_pedido", pedido_id=pedido_id))


@bp.route("/pedidos/<int:pedido_id>/status", methods=["POST"])
@login_required
def atualizar_status_pedido(pedido_id):
    db = get_db()
    novo_status = request.form.get("status")
    if novo_status in ("aberto", "enviado", "recebido", "cancelado"):
        db.execute("UPDATE pedidos_compra SET status = ? WHERE id = ?", (novo_status, pedido_id))
        db.commit()
        flash("Status do pedido atualizado.", "sucesso")
    return redirect(url_for("estoque.detalhe_pedido", pedido_id=pedido_id))


# ===================== ENTRADAS / NOTAS FISCAIS =====================
@bp.route("/entradas")
@login_required
def entradas():
    db = get_db()
    lista = db.execute(
        """SELECT e.*, f.nome AS fornecedor_nome,
                  (SELECT COALESCE(SUM(quantidade * valor_unitario), 0) FROM entrada_estoque_itens WHERE entrada_id = e.id) AS total
           FROM entradas_estoque e LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
           ORDER BY e.data_entrada DESC"""
    ).fetchall()
    return render_template("estoque/entradas.html", entradas=lista)


@bp.route("/entradas/nova", methods=["GET", "POST"])
@login_required
def nova_entrada():
    db = get_db()
    fornecedores = db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        cursor = db.execute(
            "INSERT INTO entradas_estoque (numero_nota, fornecedor_id, observacao, criado_por) VALUES (?,?,?,?)",
            (
                request.form.get("numero_nota", "").strip(),
                request.form.get("fornecedor_id") or None,
                request.form.get("observacao", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Entrada criada. Adicione os itens recebidos.", "sucesso")
        return redirect(url_for("estoque.detalhe_entrada", entrada_id=cursor.lastrowid))
    return render_template("estoque/form_entrada.html", fornecedores=fornecedores)


@bp.route("/entradas/<int:entrada_id>")
@login_required
def detalhe_entrada(entrada_id):
    db = get_db()
    entrada = db.execute(
        """SELECT e.*, f.nome AS fornecedor_nome FROM entradas_estoque e
           LEFT JOIN fornecedores f ON f.id = e.fornecedor_id WHERE e.id = ?""",
        (entrada_id,),
    ).fetchone()
    if entrada is None:
        flash("Entrada não encontrada.", "erro")
        return redirect(url_for("estoque.entradas"))
    itens = db.execute(
        """SELECT i.*, p.nome AS peca_nome, p.unidade_medida FROM entrada_estoque_itens i
           JOIN pecas_estoque p ON p.id = i.peca_id WHERE i.entrada_id = ?""",
        (entrada_id,),
    ).fetchall()
    pecas = db.execute("SELECT id, nome FROM pecas_estoque ORDER BY nome").fetchall()
    return render_template("estoque/detalhe_entrada.html", entrada=entrada, itens=itens, pecas=pecas)


@bp.route("/entradas/<int:entrada_id>/item", methods=["POST"])
@login_required
def adicionar_item_entrada(entrada_id):
    db = get_db()
    peca_id = request.form.get("peca_id")
    quantidade = float(request.form.get("quantidade", "1") or 1)
    valor_unitario = float(request.form.get("valor_unitario", "0") or 0)

    db.execute(
        "INSERT INTO entrada_estoque_itens (entrada_id, peca_id, quantidade, valor_unitario) VALUES (?,?,?,?)",
        (entrada_id, peca_id, quantidade, valor_unitario),
    )
    db.execute(
        "UPDATE pecas_estoque SET quantidade = quantidade + ?, atualizado_em = datetime('now','localtime') WHERE id = ?",
        (quantidade, peca_id),
    )
    db.commit()
    flash("Item recebido e adicionado ao estoque.", "sucesso")
    return redirect(url_for("estoque.detalhe_entrada", entrada_id=entrada_id))


# ===================== TRANSFERÊNCIAS ENTRE ALMOXARIFADOS =====================
@bp.route("/transferencias")
@login_required
def transferencias():
    db = get_db()
    lista = db.execute(
        """SELECT t.*, p.nome AS peca_nome, o.nome AS origem_nome, d.nome AS destino_nome
           FROM transferencias_estoque t
           JOIN pecas_estoque p ON p.id = t.peca_id
           LEFT JOIN almoxarifados o ON o.id = t.origem_id
           LEFT JOIN almoxarifados d ON d.id = t.destino_id
           ORDER BY t.data_transferencia DESC"""
    ).fetchall()
    return render_template("estoque/transferencias.html", transferencias=lista)


@bp.route("/transferencias/nova", methods=["GET", "POST"])
@login_required
def nova_transferencia():
    db = get_db()
    pecas = db.execute("SELECT id, nome, quantidade FROM pecas_estoque ORDER BY nome").fetchall()
    almoxarifados = db.execute("SELECT id, nome FROM almoxarifados WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO transferencias_estoque (peca_id, quantidade, origem_id, destino_id, responsavel, observacao, criado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (
                request.form.get("peca_id"),
                float(request.form.get("quantidade", "1") or 1),
                request.form.get("origem_id") or None,
                request.form.get("destino_id") or None,
                request.form.get("responsavel", "").strip(),
                request.form.get("observacao", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Transferência registrada.", "sucesso")
        return redirect(url_for("estoque.transferencias"))
    return render_template("estoque/form_transferencia.html", pecas=pecas, almoxarifados=almoxarifados)


# ===================== BAIXAS DIVERSAS =====================
@bp.route("/baixas")
@login_required
def baixas():
    db = get_db()
    lista = db.execute(
        """SELECT b.*, p.nome AS peca_nome, p.unidade_medida, u.nome AS responsavel_nome
           FROM baixas_estoque b JOIN pecas_estoque p ON p.id = b.peca_id
           LEFT JOIN usuarios u ON u.id = b.responsavel_id
           ORDER BY b.data_baixa DESC"""
    ).fetchall()
    return render_template("estoque/baixas.html", baixas=lista)


@bp.route("/baixas/nova", methods=["GET", "POST"])
@login_required
def nova_baixa():
    db = get_db()
    pecas = db.execute("SELECT id, nome, quantidade, unidade_medida FROM pecas_estoque ORDER BY nome").fetchall()
    if request.method == "POST":
        peca_id = request.form.get("peca_id")
        quantidade = float(request.form.get("quantidade", "1") or 1)
        peca = db.execute("SELECT * FROM pecas_estoque WHERE id = ?", (peca_id,)).fetchone()
        if peca is None or peca["quantidade"] < quantidade:
            flash("Quantidade em estoque insuficiente para esta baixa.", "erro")
            return render_template("estoque/form_baixa.html", pecas=pecas)

        db.execute(
            "INSERT INTO baixas_estoque (peca_id, quantidade, motivo, responsavel_id) VALUES (?,?,?,?)",
            (peca_id, quantidade, request.form.get("motivo", "").strip(), current_user.id),
        )
        db.execute(
            "UPDATE pecas_estoque SET quantidade = quantidade - ?, atualizado_em = datetime('now','localtime') WHERE id = ?",
            (quantidade, peca_id),
        )
        db.commit()
        flash("Baixa registrada.", "sucesso")
        return redirect(url_for("estoque.baixas"))
    return render_template("estoque/form_baixa.html", pecas=pecas)


# ===================== INVENTÁRIOS =====================
@bp.route("/inventarios")
@login_required
def inventarios():
    db = get_db()
    lista = db.execute("SELECT * FROM inventarios ORDER BY data_inventario DESC").fetchall()
    return render_template("estoque/inventarios.html", inventarios=lista)


@bp.route("/inventarios/novo", methods=["POST"])
@login_required
def novo_inventario():
    db = get_db()
    cursor = db.execute(
        "INSERT INTO inventarios (descricao, criado_por) VALUES (?, ?)",
        (request.form.get("descricao", "").strip(), current_user.id),
    )
    inventario_id = cursor.lastrowid
    pecas = db.execute("SELECT id, quantidade FROM pecas_estoque").fetchall()
    for peca in pecas:
        db.execute(
            "INSERT INTO inventario_itens (inventario_id, peca_id, quantidade_sistema) VALUES (?,?,?)",
            (inventario_id, peca["id"], peca["quantidade"]),
        )
    db.commit()
    flash("Inventário aberto com a posição atual do sistema.", "sucesso")
    return redirect(url_for("estoque.detalhe_inventario", inventario_id=inventario_id))


@bp.route("/inventarios/<int:inventario_id>")
@login_required
def detalhe_inventario(inventario_id):
    db = get_db()
    inventario = db.execute("SELECT * FROM inventarios WHERE id = ?", (inventario_id,)).fetchone()
    if inventario is None:
        flash("Inventário não encontrado.", "erro")
        return redirect(url_for("estoque.inventarios"))
    itens = db.execute(
        """SELECT i.*, p.nome AS peca_nome, p.unidade_medida FROM inventario_itens i
           JOIN pecas_estoque p ON p.id = i.peca_id WHERE i.inventario_id = ? ORDER BY p.nome""",
        (inventario_id,),
    ).fetchall()
    return render_template("estoque/detalhe_inventario.html", inventario=inventario, itens=itens)


@bp.route("/inventarios/<int:inventario_id>/contagem", methods=["POST"])
@login_required
def registrar_contagem(inventario_id):
    db = get_db()
    for chave, valor in request.form.items():
        if chave.startswith("contagem_") and valor.strip():
            item_id = chave.replace("contagem_", "")
            db.execute(
                "UPDATE inventario_itens SET quantidade_contada = ? WHERE id = ? AND inventario_id = ?",
                (float(valor), item_id, inventario_id),
            )
    db.commit()
    flash("Contagem salva.", "sucesso")
    return redirect(url_for("estoque.detalhe_inventario", inventario_id=inventario_id))


@bp.route("/inventarios/<int:inventario_id>/fechar", methods=["POST"])
@login_required
def fechar_inventario(inventario_id):
    db = get_db()
    itens = db.execute(
        "SELECT * FROM inventario_itens WHERE inventario_id = ? AND quantidade_contada IS NOT NULL", (inventario_id,)
    ).fetchall()
    for item in itens:
        if item["quantidade_contada"] != item["quantidade_sistema"]:
            db.execute(
                "UPDATE pecas_estoque SET quantidade = ?, atualizado_em = datetime('now','localtime') WHERE id = ?",
                (item["quantidade_contada"], item["peca_id"]),
            )
    db.execute("UPDATE inventarios SET status = 'fechado' WHERE id = ?", (inventario_id,))
    db.commit()
    flash("Inventário fechado e estoque ajustado conforme a contagem.", "sucesso")
    return redirect(url_for("estoque.inventarios"))


# ===================== ALMOXARIFADOS =====================
@bp.route("/almoxarifados", methods=["GET", "POST"])
@login_required
def almoxarifados():
    db = get_db()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if nome:
            try:
                db.execute(
                    "INSERT INTO almoxarifados (nome, unidade_id) VALUES (?, ?)",
                    (nome, request.form.get("unidade_id") or None),
                )
                db.commit()
                flash("Almoxarifado cadastrado.", "sucesso")
            except Exception:
                flash("Já existe um almoxarifado com este nome.", "erro")
        return redirect(url_for("estoque.almoxarifados"))
    lista = db.execute(
        """SELECT a.*, u.nome AS unidade_nome FROM almoxarifados a
           LEFT JOIN unidades u ON u.id = a.unidade_id ORDER BY a.nome"""
    ).fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    return render_template("estoque/almoxarifados.html", almoxarifados=lista, unidades=unidades)


# ===================== CADASTROS BÁSICOS E RELATÓRIOS =====================
@bp.route("/cadastros-basicos")
@login_required
def cadastros_basicos():
    return render_template("estoque/cadastros_basicos.html")


@bp.route("/relatorios")
@login_required
def relatorios():
    return render_template("estoque/relatorios.html")


@bp.route("/relatorios/produtos.csv")
@login_required
def exportar_produtos_csv():
    db = get_db()
    linhas = db.execute(
        "SELECT codigo, nome, unidade_medida, quantidade, quantidade_minima, custo_unitario, fornecedor, localizacao FROM pecas_estoque ORDER BY nome"
    ).fetchall()
    return _csv_response(
        "produtos.csv",
        ["Código", "Nome", "Unidade", "Quantidade", "Qtd. mínima", "Custo unitário", "Fornecedor", "Localização"],
        linhas,
    )

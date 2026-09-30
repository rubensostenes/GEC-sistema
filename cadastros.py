from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from auth import CARGO_LABELS, CARGOS_VALIDOS, admin_required
from db import get_db

bp = Blueprint("cadastros", __name__, url_prefix="/cadastros")


# ===================== UNIDADES =====================
@bp.route("/unidades")
@login_required
def unidades():
    db = get_db()
    lista = db.execute(
        """SELECT u.*, (SELECT COUNT(*) FROM equipamentos e WHERE e.unidade_id = u.id) AS total_equipamentos
           FROM unidades u ORDER BY u.nome"""
    ).fetchall()
    return render_template("cadastros/unidades.html", unidades=lista)


@bp.route("/unidades/nova", methods=["GET", "POST"])
@login_required
@admin_required
def nova_unidade():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        endereco = request.form.get("endereco", "").strip()
        if not nome:
            flash("Informe o nome da unidade.", "erro")
            return render_template("cadastros/form_unidade.html", unidade=None)
        db = get_db()
        try:
            db.execute("INSERT INTO unidades (nome, endereco) VALUES (?, ?)", (nome, endereco))
            db.commit()
            flash("Unidade cadastrada com sucesso.", "sucesso")
        except Exception:
            flash("Já existe uma unidade com este nome.", "erro")
            return render_template("cadastros/form_unidade.html", unidade=None)
        return redirect(url_for("cadastros.unidades"))
    return render_template("cadastros/form_unidade.html", unidade=None)


@bp.route("/unidades/<int:unidade_id>/setores")
@login_required
def setores(unidade_id):
    db = get_db()
    unidade = db.execute("SELECT * FROM unidades WHERE id = ?", (unidade_id,)).fetchone()
    if unidade is None:
        flash("Unidade não encontrada.", "erro")
        return redirect(url_for("cadastros.unidades"))

    lista = db.execute(
        """SELECT s.*, c.nome AS responsavel_nome FROM setores s
           LEFT JOIN colaboradores c ON c.id = s.responsavel_id
           WHERE s.unidade_id = ? ORDER BY s.nome""",
        (unidade_id,),
    ).fetchall()
    return render_template("cadastros/setores.html", unidade=unidade, setores=lista)


def _dados_apoio_setor(db):
    return {
        "colaboradores": db.execute("SELECT id, nome FROM colaboradores WHERE ativo = 1 ORDER BY nome").fetchall(),
        "centros_custo": db.execute("SELECT id, nome FROM centros_custo WHERE ativo = 1 ORDER BY nome").fetchall(),
        "usuarios": db.execute("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome").fetchall(),
    }


def _ler_formulario_setor(request):
    def vazio_para_none(campo):
        valor = (request.form.get(campo) or "").strip()
        return valor if valor else None

    return {
        "nome": (request.form.get("nome") or "").strip(),
        "codigo": vazio_para_none("codigo"),
        "cor": vazio_para_none("cor"),
        "responsavel_id": vazio_para_none("responsavel_id"),
        "eh_almoxarifado": 1 if request.form.get("eh_almoxarifado") else 0,
        "codigo_integracao": vazio_para_none("codigo_integracao"),
        "localizacao": vazio_para_none("localizacao"),
        "contato": vazio_para_none("contato"),
        "telefone": vazio_para_none("telefone"),
        "ramal": vazio_para_none("ramal"),
        "pais": vazio_para_none("pais"),
        "cep": vazio_para_none("cep"),
        "logradouro": vazio_para_none("logradouro"),
        "numero": vazio_para_none("numero"),
        "complemento": vazio_para_none("complemento"),
        "bairro": vazio_para_none("bairro"),
        "cidade": vazio_para_none("cidade"),
        "estado": vazio_para_none("estado"),
        "observacao": vazio_para_none("observacao"),
    }


def _sincronizar_almoxarifado(db, setor_id, unidade_id, nome, eh_almoxarifado):
    existente = db.execute("SELECT id FROM almoxarifados WHERE setor_id = ?", (setor_id,)).fetchone()
    if eh_almoxarifado and not existente:
        try:
            db.execute("INSERT INTO almoxarifados (nome, unidade_id, setor_id) VALUES (?,?,?)", (nome, unidade_id, setor_id))
        except Exception:
            pass
    elif eh_almoxarifado and existente:
        db.execute("UPDATE almoxarifados SET nome = ? WHERE id = ?", (nome, existente["id"]))
    elif not eh_almoxarifado and existente:
        db.execute("DELETE FROM almoxarifados WHERE id = ?", (existente["id"],))


@bp.route("/unidades/<int:unidade_id>/setores/novo", methods=["GET", "POST"])
@login_required
def novo_setor(unidade_id):
    db = get_db()
    unidade = db.execute("SELECT * FROM unidades WHERE id = ?", (unidade_id,)).fetchone()
    if unidade is None:
        flash("Unidade não encontrada.", "erro")
        return redirect(url_for("cadastros.unidades"))

    if request.method == "POST":
        dados = _ler_formulario_setor(request)
        if not dados["nome"]:
            flash("Informe a descrição do setor.", "erro")
            return render_template("cadastros/form_setor.html", unidade=unidade, setor=None, **_dados_apoio_setor(db))
        try:
            cursor = db.execute(
                """INSERT INTO setores (unidade_id, nome, codigo, cor, responsavel_id, eh_almoxarifado,
                   codigo_integracao, localizacao, contato, telefone, ramal, pais, cep, logradouro, numero,
                   complemento, bairro, cidade, estado, observacao)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    unidade_id, dados["nome"], dados["codigo"], dados["cor"], dados["responsavel_id"],
                    dados["eh_almoxarifado"], dados["codigo_integracao"], dados["localizacao"], dados["contato"],
                    dados["telefone"], dados["ramal"], dados["pais"], dados["cep"], dados["logradouro"],
                    dados["numero"], dados["complemento"], dados["bairro"], dados["cidade"], dados["estado"],
                    dados["observacao"],
                ),
            )
            setor_id = cursor.lastrowid
            _sincronizar_almoxarifado(db, setor_id, unidade_id, dados["nome"], dados["eh_almoxarifado"])

            centro_custo_id = request.form.get("centro_custo_id")
            if centro_custo_id:
                db.execute(
                    "INSERT INTO setor_centro_custo (setor_id, centro_custo_id, percentual) VALUES (?,?,?)",
                    (setor_id, centro_custo_id, float(request.form.get("percentual", "100") or 100)),
                )
            for usuario_id in request.form.getlist("usuarios_liberados"):
                db.execute(
                    "INSERT INTO setor_usuarios_liberados (setor_id, usuario_id) VALUES (?,?)", (setor_id, usuario_id)
                )

            db.commit()
            flash("Setor cadastrado com sucesso.", "sucesso")
        except Exception:
            flash("Já existe um setor com este nome nesta unidade.", "erro")
            return render_template("cadastros/form_setor.html", unidade=unidade, setor=None, **_dados_apoio_setor(db))
        return redirect(url_for("cadastros.setores", unidade_id=unidade_id))

    return render_template("cadastros/form_setor.html", unidade=unidade, setor=None, **_dados_apoio_setor(db))


@bp.route("/setores/<int:setor_id>/editar", methods=["GET", "POST"])
@login_required
def editar_setor(setor_id):
    db = get_db()
    setor = db.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
    if setor is None:
        flash("Setor não encontrado.", "erro")
        return redirect(url_for("cadastros.unidades"))
    unidade = db.execute("SELECT * FROM unidades WHERE id = ?", (setor["unidade_id"],)).fetchone()

    if request.method == "POST":
        dados = _ler_formulario_setor(request)
        db.execute(
            """UPDATE setores SET nome=?, codigo=?, cor=?, responsavel_id=?, eh_almoxarifado=?,
               codigo_integracao=?, localizacao=?, contato=?, telefone=?, ramal=?, pais=?, cep=?, logradouro=?,
               numero=?, complemento=?, bairro=?, cidade=?, estado=?, observacao=? WHERE id=?""",
            (
                dados["nome"], dados["codigo"], dados["cor"], dados["responsavel_id"], dados["eh_almoxarifado"],
                dados["codigo_integracao"], dados["localizacao"], dados["contato"], dados["telefone"],
                dados["ramal"], dados["pais"], dados["cep"], dados["logradouro"], dados["numero"],
                dados["complemento"], dados["bairro"], dados["cidade"], dados["estado"], dados["observacao"],
                setor_id,
            ),
        )
        _sincronizar_almoxarifado(db, setor_id, setor["unidade_id"], dados["nome"], dados["eh_almoxarifado"])
        db.commit()
        flash("Setor atualizado.", "sucesso")
        return redirect(url_for("cadastros.setores", unidade_id=setor["unidade_id"]))

    apoio = _dados_apoio_setor(db)
    apoio["centros_custo_vinculados"] = db.execute(
        """SELECT scc.*, cc.nome AS centro_custo_nome FROM setor_centro_custo scc
           JOIN centros_custo cc ON cc.id = scc.centro_custo_id WHERE scc.setor_id = ?""",
        (setor_id,),
    ).fetchall()
    apoio["usuarios_liberados_ids"] = {
        row["usuario_id"] for row in db.execute("SELECT usuario_id FROM setor_usuarios_liberados WHERE setor_id = ?", (setor_id,))
    }
    return render_template("cadastros/form_setor.html", unidade=unidade, setor=setor, **apoio)


# ===================== USUÁRIOS =====================
@bp.route("/usuarios")
@login_required
@admin_required
def usuarios():
    db = get_db()
    lista = db.execute(
        """SELECT us.*, un.nome AS unidade_nome, g.nome AS grupo_nome FROM usuarios us
           LEFT JOIN unidades un ON un.id = us.unidade_id
           LEFT JOIN grupos_usuarios g ON g.id = us.grupo_id
           ORDER BY us.nome"""
    ).fetchall()
    return render_template("cadastros/usuarios.html", usuarios=lista, cargo_labels=CARGO_LABELS)


@bp.route("/usuarios/<int:usuario_id>/alternar-status", methods=["POST"])
@login_required
@admin_required
def alternar_status_usuario(usuario_id):
    db = get_db()
    if usuario_id == current_user.id:
        flash("Você não pode desativar seu próprio usuário.", "erro")
        return redirect(url_for("cadastros.usuarios"))
    usuario = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if usuario is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("cadastros.usuarios"))
    novo_status = 0 if usuario["ativo"] else 1
    db.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, usuario_id))
    from configuracao import _registrar_log

    _registrar_log(
        db, "usuario", "ativar" if novo_status else "desativar", f"{usuario['nome']} ({usuario['email']})"
    )
    db.commit()
    flash("Status do usuário atualizado.", "sucesso")
    return redirect(url_for("cadastros.usuarios"))


@bp.route("/usuarios/<int:usuario_id>/redefinir-senha", methods=["GET", "POST"])
@login_required
@admin_required
def redefinir_senha(usuario_id):
    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if usuario is None:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("cadastros.usuarios"))

    if request.method == "POST":
        from auth import validar_senha

        nova_senha = request.form.get("nova_senha", "")
        confirmar = request.form.get("confirmar_senha", "")
        erros = validar_senha(db, nova_senha)
        if nova_senha != confirmar:
            erros.append("As senhas não coincidem.")
        if erros:
            for erro in erros:
                flash(erro, "erro")
        else:
            db.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (generate_password_hash(nova_senha), usuario_id),
            )
            from configuracao import _registrar_log

            _registrar_log(db, "usuario", "redefinir_senha", f"{usuario['nome']} ({usuario['email']})")
            db.commit()
            flash(f"Senha de {usuario['nome']} redefinida com sucesso.", "sucesso")
            return redirect(url_for("cadastros.usuarios"))

    return render_template("cadastros/redefinir_senha.html", usuario=usuario)


# ===================== ESTOQUE DE PEÇAS =====================
@bp.route("/estoque")
@login_required
def estoque():
    db = get_db()
    termo = request.args.get("q", "").strip()
    sql = "SELECT * FROM pecas_estoque WHERE 1=1"
    params = []
    if termo:
        sql += " AND (nome LIKE ? OR codigo LIKE ?)"
        params += [f"%{termo}%", f"%{termo}%"]
    sql += " ORDER BY nome"
    lista = db.execute(sql, params).fetchall()
    return render_template("estoque/lista.html", pecas=lista, filtros={"q": termo})


@bp.route("/estoque/nova", methods=["GET", "POST"])
@login_required
def nova_peca():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        codigo = request.form.get("codigo", "").strip() or None
        unidade_medida = request.form.get("unidade_medida", "un").strip()
        quantidade = request.form.get("quantidade", "0") or 0
        quantidade_minima = request.form.get("quantidade_minima", "0") or 0
        custo_unitario = request.form.get("custo_unitario", "0") or 0
        fornecedor = request.form.get("fornecedor", "").strip()
        localizacao = request.form.get("localizacao", "").strip()

        if not nome:
            flash("Informe o nome da peça/insumo.", "erro")
            return render_template("estoque/form.html", peca=None)

        db = get_db()
        db.execute(
            """INSERT INTO pecas_estoque
               (codigo, nome, unidade_medida, quantidade, quantidade_minima, custo_unitario, fornecedor, localizacao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                codigo,
                nome,
                unidade_medida,
                float(quantidade),
                float(quantidade_minima),
                float(custo_unitario),
                fornecedor,
                localizacao,
            ),
        )
        db.commit()
        flash("Peça cadastrada no estoque.", "sucesso")
        return redirect(url_for("cadastros.estoque"))

    return render_template("estoque/form.html", peca=None)


@bp.route("/estoque/<int:peca_id>/editar", methods=["GET", "POST"])
@login_required
def editar_peca(peca_id):
    db = get_db()
    peca = db.execute("SELECT * FROM pecas_estoque WHERE id = ?", (peca_id,)).fetchone()
    if peca is None:
        flash("Peça não encontrada.", "erro")
        return redirect(url_for("cadastros.estoque"))

    if request.method == "POST":
        db.execute(
            """UPDATE pecas_estoque SET codigo = ?, nome = ?, unidade_medida = ?, quantidade = ?,
               quantidade_minima = ?, custo_unitario = ?, fornecedor = ?, localizacao = ?,
               atualizado_em = datetime('now','localtime') WHERE id = ?""",
            (
                request.form.get("codigo", "").strip() or None,
                request.form.get("nome", "").strip(),
                request.form.get("unidade_medida", "un").strip(),
                float(request.form.get("quantidade", "0") or 0),
                float(request.form.get("quantidade_minima", "0") or 0),
                float(request.form.get("custo_unitario", "0") or 0),
                request.form.get("fornecedor", "").strip(),
                request.form.get("localizacao", "").strip(),
                peca_id,
            ),
        )
        db.commit()
        flash("Peça atualizada.", "sucesso")
        return redirect(url_for("cadastros.estoque"))

    return render_template("estoque/form.html", peca=peca)

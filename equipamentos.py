from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db
from utils import dias_ate, salvar_arquivo, somar_meses

bp = Blueprint("equipamentos", __name__, url_prefix="/equipamentos")

CATEGORIAS_SUGERIDAS = [
    "Facoemulsificador",
    "Tonômetro",
    "Lâmpada de fenda",
    "OCT",
    "Topógrafo de córnea",
    "Retinógrafo",
    "Autorrefrator",
    "Microscópio cirúrgico",
    "Laser (YAG/SLT/Fotocoagulação)",
    "Biômetro",
    "Campímetro",
    "Outro",
]


@bp.route("/")
@login_required
def lista():
    db = get_db()
    termo = request.args.get("q", "").strip()
    unidade_id = request.args.get("unidade_id", "")
    status = request.args.get("status", "")
    criticidade = request.args.get("criticidade", "")
    tag = request.args.get("tag", "").strip()
    patrimonio = request.args.get("patrimonio", "").strip()
    numero_serie = request.args.get("numero_serie", "").strip()
    fabricante = request.args.get("fabricante", "").strip()
    setor_id = request.args.get("setor_id", "")
    situacao = request.args.get("situacao", "ativos")
    visualizar = request.args.get("visualizar", "100")

    sql = """SELECT e.*, u.nome AS unidade_nome, s.nome AS setor_nome, l.nome AS label_nome, l.cor AS label_cor
              FROM equipamentos e
              LEFT JOIN unidades u ON u.id = e.unidade_id
              LEFT JOIN setores s ON s.id = e.setor_id
              LEFT JOIN labels l ON l.id = e.label_id
              WHERE 1=1"""
    params = []

    if termo:
        sql += """ AND (e.nome LIKE ? OR e.patrimonio LIKE ? OR e.numero_serie LIKE ?
                    OR e.fabricante LIKE ? OR e.modelo LIKE ? OR e.tag LIKE ?)"""
        curinga = f"%{termo}%"
        params += [curinga, curinga, curinga, curinga, curinga, curinga]
    if unidade_id:
        sql += " AND e.unidade_id = ?"
        params.append(unidade_id)
    if setor_id:
        sql += " AND e.setor_id = ?"
        params.append(setor_id)
    if status:
        sql += " AND e.status = ?"
        params.append(status)
    if criticidade:
        sql += " AND e.criticidade = ?"
        params.append(criticidade)
    if tag:
        sql += " AND e.tag LIKE ?"
        params.append(f"%{tag}%")
    if patrimonio:
        sql += " AND e.patrimonio LIKE ?"
        params.append(f"%{patrimonio}%")
    if numero_serie:
        sql += " AND e.numero_serie LIKE ?"
        params.append(f"%{numero_serie}%")
    if fabricante:
        sql += " AND e.fabricante LIKE ?"
        params.append(f"%{fabricante}%")
    if situacao == "ativos":
        sql += " AND e.status != 'inativo'"
    elif situacao == "inativos":
        sql += " AND e.status = 'inativo'"

    total_registros = db.execute(f"SELECT COUNT(*) AS c FROM ({sql})", params).fetchone()["c"]
    sql += " ORDER BY e.nome"
    if visualizar != "todos":
        try:
            sql += f" LIMIT {int(visualizar)}"
        except ValueError:
            sql += " LIMIT 100"
    equipamentos = db.execute(sql, params).fetchall()
    unidades = db.execute("SELECT * FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    setores = db.execute("SELECT id, nome FROM setores ORDER BY nome").fetchall()

    return render_template(
        "equipamentos/lista.html",
        equipamentos=equipamentos,
        unidades=unidades,
        setores=setores,
        total_registros=total_registros,
        filtros={
            "q": termo, "unidade_id": unidade_id, "status": status, "criticidade": criticidade,
            "tag": tag, "patrimonio": patrimonio, "numero_serie": numero_serie, "fabricante": fabricante,
            "setor_id": setor_id, "situacao": situacao, "visualizar": visualizar,
        },
        dias_ate=dias_ate,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    db = get_db()
    unidades = db.execute("SELECT * FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    labels = db.execute("SELECT * FROM labels ORDER BY nome").fetchall()

    if request.method == "POST":
        dados = _ler_formulario(request)

        if not dados["nome"]:
            flash("Informe o nome/tipo do equipamento.", "erro")
            return render_template(
                "equipamentos/form.html",
                equipamento=None,
                unidades=unidades,
                labels=labels,
                setores=[],
                categorias=CATEGORIAS_SUGERIDAS,
            )

        cursor = db.execute(
            """INSERT INTO equipamentos
               (patrimonio, nome, categoria, fabricante, modelo, numero_serie, registro_anvisa,
                unidade_id, setor_id, localizacao, criticidade, status, data_aquisicao, valor_aquisicao,
                fornecedor, data_fim_garantia, necessita_calibracao, periodicidade_calibracao_meses,
                data_ultima_calibracao, data_proxima_calibracao, periodicidade_preventiva_meses,
                data_ultima_preventiva, data_proxima_preventiva, data_instalacao, valor_reposicao,
                de_terceiros, proprietario_terceiro, eh_padrao_calibracao, certificado_rastreabilidade,
                orgao_certificador, data_validade_rastreabilidade, observacoes, criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                dados["patrimonio"], dados["nome"], dados["categoria"], dados["fabricante"],
                dados["modelo"], dados["numero_serie"], dados["registro_anvisa"], dados["unidade_id"],
                dados["setor_id"], dados["localizacao"], dados["criticidade"], dados["status"],
                dados["data_aquisicao"], dados["valor_aquisicao"], dados["fornecedor"],
                dados["data_fim_garantia"], dados["necessita_calibracao"],
                dados["periodicidade_calibracao_meses"], dados["data_ultima_calibracao"],
                dados["data_proxima_calibracao"], dados["periodicidade_preventiva_meses"],
                dados["data_ultima_preventiva"], dados["data_proxima_preventiva"],
                dados["data_instalacao"], dados["valor_reposicao"], dados["de_terceiros"],
                dados["proprietario_terceiro"], dados["eh_padrao_calibracao"],
                dados["certificado_rastreabilidade"], dados["orgao_certificador"],
                dados["data_validade_rastreabilidade"], dados["observacoes"], current_user.id,
            ),
        )
        equipamento_id = cursor.lastrowid

        db.execute(
            "UPDATE equipamentos SET label_id = ? WHERE id = ?",
            (request.form.get("label_id") or None, equipamento_id),
        )

        arquivo = request.files.get("foto")
        if arquivo and arquivo.filename:
            try:
                _, caminho = salvar_arquivo(arquivo)
                db.execute(
                    "UPDATE equipamentos SET foto_path = ? WHERE id = ?", (caminho, equipamento_id)
                )
            except ValueError as e:
                flash(str(e), "aviso")

        db.commit()
        flash("Equipamento cadastrado com sucesso.", "sucesso")
        return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))

    return render_template(
        "equipamentos/form.html",
        equipamento=None,
        unidades=unidades,
        labels=labels,
        setores=[],
        categorias=CATEGORIAS_SUGERIDAS,
    )


@bp.route("/<int:equipamento_id>")
@login_required
def detalhe(equipamento_id):
    db = get_db()
    equipamento = db.execute(
        """SELECT e.*, u.nome AS unidade_nome, s.nome AS setor_nome, l.nome AS label_nome, l.cor AS label_cor
           FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           LEFT JOIN setores s ON s.id = e.setor_id
           LEFT JOIN labels l ON l.id = e.label_id
           WHERE e.id = ?""",
        (equipamento_id,),
    ).fetchone()
    if equipamento is None:
        flash("Equipamento não encontrado.", "erro")
        return redirect(url_for("equipamentos.lista"))

    ordens = db.execute(
        """SELECT os.*, us.nome AS tecnico_nome FROM ordens_servico os
           LEFT JOIN usuarios us ON us.id = os.tecnico_id
           WHERE os.equipamento_id = ? ORDER BY os.data_abertura DESC""",
        (equipamento_id,),
    ).fetchall()

    anexos = db.execute(
        "SELECT * FROM anexos WHERE equipamento_id = ? ORDER BY criado_em DESC", (equipamento_id,)
    ).fetchall()

    return render_template(
        "equipamentos/detalhe.html",
        equipamento=equipamento,
        ordens=ordens,
        anexos=anexos,
        dias_ate=dias_ate,
    )


@bp.route("/<int:equipamento_id>/editar", methods=["GET", "POST"])
@login_required
def editar(equipamento_id):
    db = get_db()
    equipamento = db.execute("SELECT * FROM equipamentos WHERE id = ?", (equipamento_id,)).fetchone()
    if equipamento is None:
        flash("Equipamento não encontrado.", "erro")
        return redirect(url_for("equipamentos.lista"))

    unidades = db.execute("SELECT * FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    labels = db.execute("SELECT * FROM labels ORDER BY nome").fetchall()
    setores = db.execute(
        "SELECT * FROM setores WHERE unidade_id = ? ORDER BY nome", (equipamento["unidade_id"],)
    ).fetchall() if equipamento["unidade_id"] else []

    if request.method == "POST":
        dados = _ler_formulario(request)
        db.execute(
            """UPDATE equipamentos SET
               patrimonio=?, nome=?, categoria=?, fabricante=?, modelo=?, numero_serie=?, registro_anvisa=?,
               unidade_id=?, setor_id=?, localizacao=?, criticidade=?, status=?, data_aquisicao=?,
               valor_aquisicao=?, fornecedor=?, data_fim_garantia=?, necessita_calibracao=?,
               periodicidade_calibracao_meses=?, data_ultima_calibracao=?, data_proxima_calibracao=?,
               periodicidade_preventiva_meses=?, data_ultima_preventiva=?, data_proxima_preventiva=?,
               data_instalacao=?, valor_reposicao=?, de_terceiros=?, proprietario_terceiro=?,
               eh_padrao_calibracao=?, certificado_rastreabilidade=?, orgao_certificador=?,
               data_validade_rastreabilidade=?, label_id=?, observacoes=?, atualizado_em=datetime('now','localtime')
               WHERE id=?""",
            (
                dados["patrimonio"], dados["nome"], dados["categoria"], dados["fabricante"],
                dados["modelo"], dados["numero_serie"], dados["registro_anvisa"], dados["unidade_id"],
                dados["setor_id"], dados["localizacao"], dados["criticidade"], dados["status"],
                dados["data_aquisicao"], dados["valor_aquisicao"], dados["fornecedor"],
                dados["data_fim_garantia"], dados["necessita_calibracao"],
                dados["periodicidade_calibracao_meses"], dados["data_ultima_calibracao"],
                dados["data_proxima_calibracao"], dados["periodicidade_preventiva_meses"],
                dados["data_ultima_preventiva"], dados["data_proxima_preventiva"],
                dados["data_instalacao"], dados["valor_reposicao"], dados["de_terceiros"],
                dados["proprietario_terceiro"], dados["eh_padrao_calibracao"],
                dados["certificado_rastreabilidade"], dados["orgao_certificador"],
                dados["data_validade_rastreabilidade"], request.form.get("label_id") or None,
                dados["observacoes"], equipamento_id,
            ),
        )

        arquivo = request.files.get("foto")
        if arquivo and arquivo.filename:
            try:
                _, caminho = salvar_arquivo(arquivo)
                db.execute(
                    "UPDATE equipamentos SET foto_path = ? WHERE id = ?", (caminho, equipamento_id)
                )
            except ValueError as e:
                flash(str(e), "aviso")

        db.commit()
        flash("Equipamento atualizado com sucesso.", "sucesso")
        return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))

    return render_template(
        "equipamentos/form.html",
        equipamento=equipamento,
        unidades=unidades,
        labels=labels,
        setores=setores,
        categorias=CATEGORIAS_SUGERIDAS,
    )


@bp.route("/<int:equipamento_id>/anexar", methods=["POST"])
@login_required
def anexar(equipamento_id):
    db = get_db()
    arquivo = request.files.get("arquivo")
    tipo = request.form.get("tipo", "outro")

    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo para enviar.", "erro")
        return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))

    try:
        nome_original, caminho = salvar_arquivo(arquivo)
    except ValueError as e:
        flash(str(e), "erro")
        return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))

    db.execute(
        """INSERT INTO anexos (equipamento_id, nome_arquivo, caminho, tipo, enviado_por)
           VALUES (?, ?, ?, ?, ?)""",
        (equipamento_id, nome_original, caminho, tipo, current_user.id),
    )
    db.commit()
    flash("Arquivo anexado com sucesso.", "sucesso")
    return redirect(url_for("equipamentos.detalhe", equipamento_id=equipamento_id))


@bp.route("/setores-por-unidade/<int:unidade_id>")
@login_required
def setores_por_unidade(unidade_id):
    """Endpoint simples usado pelo JS para popular o <select> de setores."""
    db = get_db()
    setores = db.execute(
        "SELECT id, nome FROM setores WHERE unidade_id = ? AND ativo = 1 ORDER BY nome", (unidade_id,)
    ).fetchall()
    return {"setores": [dict(s) for s in setores]}


def _ler_formulario(request):
    def vazio_para_none(valor):
        valor = (valor or "").strip()
        return valor if valor else None

    periodicidade_calibracao = vazio_para_none(request.form.get("periodicidade_calibracao_meses"))
    periodicidade_preventiva = vazio_para_none(request.form.get("periodicidade_preventiva_meses"))
    data_ultima_calibracao = vazio_para_none(request.form.get("data_ultima_calibracao"))
    data_ultima_preventiva = vazio_para_none(request.form.get("data_ultima_preventiva"))

    data_proxima_calibracao = vazio_para_none(request.form.get("data_proxima_calibracao"))
    if not data_proxima_calibracao and data_ultima_calibracao and periodicidade_calibracao:
        data_proxima_calibracao = somar_meses(data_ultima_calibracao, int(periodicidade_calibracao))

    data_proxima_preventiva = vazio_para_none(request.form.get("data_proxima_preventiva"))
    if not data_proxima_preventiva and data_ultima_preventiva and periodicidade_preventiva:
        data_proxima_preventiva = somar_meses(data_ultima_preventiva, int(periodicidade_preventiva))

    valor_aquisicao = vazio_para_none(request.form.get("valor_aquisicao"))
    valor_reposicao = vazio_para_none(request.form.get("valor_reposicao"))

    return {
        "patrimonio": vazio_para_none(request.form.get("patrimonio")),
        "nome": (request.form.get("nome") or "").strip(),
        "categoria": vazio_para_none(request.form.get("categoria")),
        "fabricante": vazio_para_none(request.form.get("fabricante")),
        "modelo": vazio_para_none(request.form.get("modelo")),
        "numero_serie": vazio_para_none(request.form.get("numero_serie")),
        "registro_anvisa": vazio_para_none(request.form.get("registro_anvisa")),
        "unidade_id": vazio_para_none(request.form.get("unidade_id")),
        "setor_id": vazio_para_none(request.form.get("setor_id")),
        "localizacao": vazio_para_none(request.form.get("localizacao")),
        "criticidade": request.form.get("criticidade", "media"),
        "status": request.form.get("status", "ativo"),
        "data_aquisicao": vazio_para_none(request.form.get("data_aquisicao")),
        "valor_aquisicao": float(valor_aquisicao) if valor_aquisicao else None,
        "fornecedor": vazio_para_none(request.form.get("fornecedor")),
        "data_fim_garantia": vazio_para_none(request.form.get("data_fim_garantia")),
        "necessita_calibracao": 1 if request.form.get("necessita_calibracao") else 0,
        "periodicidade_calibracao_meses": int(periodicidade_calibracao) if periodicidade_calibracao else None,
        "data_ultima_calibracao": data_ultima_calibracao,
        "data_proxima_calibracao": data_proxima_calibracao,
        "periodicidade_preventiva_meses": int(periodicidade_preventiva) if periodicidade_preventiva else None,
        "data_ultima_preventiva": data_ultima_preventiva,
        "data_proxima_preventiva": data_proxima_preventiva,
        "data_instalacao": vazio_para_none(request.form.get("data_instalacao")),
        "valor_reposicao": float(valor_reposicao) if valor_reposicao else None,
        "de_terceiros": 1 if request.form.get("de_terceiros") else 0,
        "proprietario_terceiro": vazio_para_none(request.form.get("proprietario_terceiro")),
        "eh_padrao_calibracao": 1 if request.form.get("eh_padrao_calibracao") else 0,
        "certificado_rastreabilidade": vazio_para_none(request.form.get("certificado_rastreabilidade")),
        "orgao_certificador": vazio_para_none(request.form.get("orgao_certificador")),
        "data_validade_rastreabilidade": vazio_para_none(request.form.get("data_validade_rastreabilidade")),
        "observacoes": vazio_para_none(request.form.get("observacoes")),
    }

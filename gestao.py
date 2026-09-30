import csv
import io
from datetime import date, timedelta

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import admin_required
from db import get_db
from utils import salvar_arquivo

bp = Blueprint("gestao", __name__, url_prefix="/gestao")

TIPO_MANUTENCAO_LABELS = {
    "preventiva": "Preventiva",
    "calibracao": "Calibração",
    "inspecao": "Inspeção",
    "inspecao_tecnica": "Inspeção Técnica",
    "inventario": "Inventário",
    "seguranca_eletrica": "Segurança Elétrica",
    "qualificacao": "Qualificação",
    "pesquisa_clinica": "Pesquisa Clínica",
    "reuniao_estrategica": "Reunião Estratégica",
    "ronda": "Ronda",
}


# ===================== SETORES (visão geral entre unidades) =====================
@bp.route("/setores")
@login_required
def setores():
    db = get_db()
    lista = db.execute(
        """SELECT s.*, u.nome AS unidade_nome,
                  (SELECT COUNT(*) FROM equipamentos e WHERE e.setor_id = s.id) AS total_equipamentos
           FROM setores s JOIN unidades u ON u.id = s.unidade_id
           ORDER BY u.nome, s.nome"""
    ).fetchall()
    return render_template("gestao/setores.html", setores=lista)


# ===================== PLANOS DE MANUTENÇÃO (preventiva/calibração) =====================
@bp.route("/planos-manutencao")
@login_required
def planos_manutencao():
    db = get_db()
    termo = request.args.get("q", "").strip()
    sql = """SELECT pl.*, p.nome AS procedimento_nome, u.nome AS responsavel_nome
              FROM planos_manutencao pl
              LEFT JOIN procedimentos_manutencao p ON p.id = pl.procedimento_id
              LEFT JOIN usuarios u ON u.id = pl.responsavel_id
              WHERE 1=1"""
    params = []
    if termo:
        sql += " AND pl.nome LIKE ?"
        params.append(f"%{termo}%")
    sql += " ORDER BY pl.oficina, pl.nome"
    lista = db.execute(sql, params).fetchall()

    agrupado = {}
    for plano in lista:
        agrupado.setdefault(plano["oficina"], []).append(plano)

    return render_template(
        "gestao/planos_manutencao.html", agrupado=agrupado, total=len(lista), termo=termo,
        tipo_labels=TIPO_MANUTENCAO_LABELS,
    )


@bp.route("/planos-manutencao/novo", methods=["GET", "POST"])
@login_required
def novo_plano_manutencao():
    db = get_db()
    if request.method == "POST":
        db.execute(
            """INSERT INTO planos_manutencao
               (nome, oficina, abrangencia, categoria_equipamento, pausado, ativo, tipo_manutencao, prioridade,
                responsavel_id, pendencia, ocorrencia, causa, procedimento_id, exigir_checklist, observacao,
                fornecedor_id, contrato_id, abrir_os_externa, periodicidade_meses, criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("oficina", "Engenharia Clínica").strip(),
                request.form.get("abrangencia", "equipamentos"),
                request.form.get("categoria_equipamento", "").strip() or None,
                1 if request.form.get("pausado") else 0,
                1 if request.form.get("ativo") else 0,
                request.form.get("tipo_manutencao", "preventiva"),
                request.form.get("prioridade", "media"),
                request.form.get("responsavel_id") or None,
                request.form.get("pendencia", "").strip() or None,
                request.form.get("ocorrencia", "").strip() or None,
                request.form.get("causa", "").strip() or None,
                request.form.get("procedimento_id") or None,
                1 if request.form.get("exigir_checklist") else 0,
                request.form.get("observacao", "").strip() or None,
                request.form.get("fornecedor_id") or None,
                request.form.get("contrato_id") or None,
                1 if request.form.get("abrir_os_externa") else 0,
                int(request.form.get("periodicidade_meses", "12") or 12),
                current_user.id,
            ),
        )
        db.commit()
        flash("Plano de manutenção cadastrado.", "sucesso")
        return redirect(url_for("gestao.planos_manutencao"))

    return render_template(
        "gestao/form_plano_manutencao.html",
        plano=None,
        usuarios=db.execute("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome").fetchall(),
        procedimentos=db.execute("SELECT id, nome FROM procedimentos_manutencao ORDER BY nome").fetchall(),
        fornecedores=db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall(),
        contratos=db.execute("SELECT id, descricao FROM contratos_manutencao WHERE status = 'ativo' ORDER BY descricao").fetchall(),
    )


@bp.route("/planos-manutencao/<int:plano_id>/editar", methods=["GET", "POST"])
@login_required
def editar_plano_manutencao(plano_id):
    db = get_db()
    plano = db.execute("SELECT * FROM planos_manutencao WHERE id = ?", (plano_id,)).fetchone()
    if plano is None:
        flash("Plano não encontrado.", "erro")
        return redirect(url_for("gestao.planos_manutencao"))

    if request.method == "POST":
        db.execute(
            """UPDATE planos_manutencao SET nome=?, oficina=?, abrangencia=?, categoria_equipamento=?, pausado=?,
               ativo=?, tipo_manutencao=?, prioridade=?, responsavel_id=?, pendencia=?, ocorrencia=?, causa=?,
               procedimento_id=?, exigir_checklist=?, observacao=?, fornecedor_id=?, contrato_id=?,
               abrir_os_externa=?, periodicidade_meses=? WHERE id=?""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("oficina", "Engenharia Clínica").strip(),
                request.form.get("abrangencia", "equipamentos"),
                request.form.get("categoria_equipamento", "").strip() or None,
                1 if request.form.get("pausado") else 0,
                1 if request.form.get("ativo") else 0,
                request.form.get("tipo_manutencao", "preventiva"),
                request.form.get("prioridade", "media"),
                request.form.get("responsavel_id") or None,
                request.form.get("pendencia", "").strip() or None,
                request.form.get("ocorrencia", "").strip() or None,
                request.form.get("causa", "").strip() or None,
                request.form.get("procedimento_id") or None,
                1 if request.form.get("exigir_checklist") else 0,
                request.form.get("observacao", "").strip() or None,
                request.form.get("fornecedor_id") or None,
                request.form.get("contrato_id") or None,
                1 if request.form.get("abrir_os_externa") else 0,
                int(request.form.get("periodicidade_meses", "12") or 12),
                plano_id,
            ),
        )
        db.commit()
        flash("Plano atualizado.", "sucesso")
        return redirect(url_for("gestao.planos_manutencao"))

    return render_template(
        "gestao/form_plano_manutencao.html",
        plano=plano,
        usuarios=db.execute("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome").fetchall(),
        procedimentos=db.execute("SELECT id, nome FROM procedimentos_manutencao ORDER BY nome").fetchall(),
        fornecedores=db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall(),
        contratos=db.execute("SELECT id, descricao FROM contratos_manutencao WHERE status = 'ativo' ORDER BY descricao").fetchall(),
    )


@bp.route("/planos-manutencao/<int:plano_id>/duplicar", methods=["POST"])
@login_required
def duplicar_plano_manutencao(plano_id):
    db = get_db()
    p = db.execute("SELECT * FROM planos_manutencao WHERE id = ?", (plano_id,)).fetchone()
    if p is None:
        flash("Plano não encontrado.", "erro")
        return redirect(url_for("gestao.planos_manutencao"))
    db.execute(
        """INSERT INTO planos_manutencao
           (nome, oficina, abrangencia, categoria_equipamento, pausado, ativo, tipo_manutencao, prioridade,
            responsavel_id, pendencia, ocorrencia, causa, procedimento_id, exigir_checklist, observacao,
            fornecedor_id, contrato_id, abrir_os_externa, periodicidade_meses, criado_por)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            p["nome"] + " (cópia)", p["oficina"], p["abrangencia"], p["categoria_equipamento"], p["pausado"],
            p["ativo"], p["tipo_manutencao"], p["prioridade"], p["responsavel_id"], p["pendencia"],
            p["ocorrencia"], p["causa"], p["procedimento_id"], p["exigir_checklist"], p["observacao"],
            p["fornecedor_id"], p["contrato_id"], p["abrir_os_externa"], p["periodicidade_meses"], current_user.id,
        ),
    )
    db.commit()
    flash("Plano duplicado.", "sucesso")
    return redirect(url_for("gestao.planos_manutencao"))


@bp.route("/planos-manutencao/<int:plano_id>/excluir", methods=["POST"])
@login_required
def excluir_plano_manutencao(plano_id):
    db = get_db()
    db.execute("DELETE FROM planos_manutencao WHERE id = ?", (plano_id,))
    db.commit()
    flash("Plano excluído.", "sucesso")
    return redirect(url_for("gestao.planos_manutencao"))


@bp.route("/planos-manutencao/exportar.csv")
@login_required
def exportar_planos_csv():
    db = get_db()
    linhas = db.execute(
        """SELECT pl.oficina, pl.nome, p.nome AS procedimento, pl.periodicidade_meses, pl.tipo_manutencao,
                  pl.prioridade, CASE WHEN pl.ativo = 1 THEN 'Ativo' ELSE 'Inativo' END AS status
           FROM planos_manutencao pl LEFT JOIN procedimentos_manutencao p ON p.id = pl.procedimento_id
           ORDER BY pl.oficina, pl.nome"""
    ).fetchall()
    return _csv_response(
        "planos_manutencao.csv",
        ["Oficina", "Nome", "Procedimento", "Periodicidade (meses)", "Tipo", "Prioridade", "Status"],
        linhas,
    )


@bp.route("/planos-manutencao/cronograma")
@login_required
def cronograma_planos():
    db = get_db()
    setor_id = request.args.get("setor_id", "")
    fornecedor_id = request.args.get("fornecedor_id", "")
    plano_id = request.args.get("plano_id", "")
    tipo = request.args.get("tipo", "")

    sql = """SELECT pl.*, p.nome AS procedimento_nome, u.nome AS responsavel_nome, f.nome AS fornecedor_nome
              FROM planos_manutencao pl
              LEFT JOIN procedimentos_manutencao p ON p.id = pl.procedimento_id
              LEFT JOIN usuarios u ON u.id = pl.responsavel_id
              LEFT JOIN fornecedores f ON f.id = pl.fornecedor_id
              WHERE pl.ativo = 1 AND pl.pausado = 0"""
    params = []
    if fornecedor_id:
        sql += " AND pl.fornecedor_id = ?"
        params.append(fornecedor_id)
    if plano_id:
        sql += " AND pl.id = ?"
        params.append(plano_id)
    if tipo:
        sql += " AND pl.tipo_manutencao = ?"
        params.append(tipo)
    sql += " ORDER BY pl.periodicidade_meses, pl.nome"

    planos = db.execute(sql, params).fetchall()
    setores = db.execute("SELECT id, nome FROM setores ORDER BY nome").fetchall()
    fornecedores = db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall()
    todos_planos = db.execute("SELECT id, nome FROM planos_manutencao ORDER BY nome").fetchall()

    return render_template(
        "gestao/cronograma_planos.html",
        planos=planos, setores=setores, fornecedores=fornecedores, todos_planos=todos_planos,
        filtros={"setor_id": setor_id, "fornecedor_id": fornecedor_id, "plano_id": plano_id, "tipo": tipo},
    )


# ===================== FORNECEDORES =====================
@bp.route("/fornecedores")
@login_required
def fornecedores():
    db = get_db()
    termo = request.args.get("q", "").strip()
    sql = "SELECT * FROM fornecedores WHERE 1=1"
    params = []
    if termo:
        sql += " AND (nome LIKE ? OR cnpj LIKE ? OR contato LIKE ?)"
        curinga = f"%{termo}%"
        params += [curinga, curinga, curinga]
    sql += " ORDER BY nome"
    lista = db.execute(sql, params).fetchall()
    return render_template("gestao/fornecedores.html", fornecedores=lista, filtros={"q": termo})


@bp.route("/fornecedores/novo", methods=["GET", "POST"])
@login_required
def novo_fornecedor():
    if request.method == "POST":
        db = get_db()
        db.execute(
            """INSERT INTO fornecedores (nome, cnpj, contato, telefone, email, servicos_prestados)
               VALUES (?,?,?,?,?,?)""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("cnpj", "").strip(),
                request.form.get("contato", "").strip(),
                request.form.get("telefone", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("servicos_prestados", "").strip(),
            ),
        )
        db.commit()
        flash("Fornecedor cadastrado com sucesso.", "sucesso")
        return redirect(url_for("gestao.fornecedores"))
    return render_template("gestao/form_fornecedor.html", fornecedor=None)


@bp.route("/fornecedores/<int:fornecedor_id>/editar", methods=["GET", "POST"])
@login_required
def editar_fornecedor(fornecedor_id):
    db = get_db()
    fornecedor = db.execute("SELECT * FROM fornecedores WHERE id = ?", (fornecedor_id,)).fetchone()
    if fornecedor is None:
        flash("Fornecedor não encontrado.", "erro")
        return redirect(url_for("gestao.fornecedores"))
    if request.method == "POST":
        db.execute(
            """UPDATE fornecedores SET nome=?, cnpj=?, contato=?, telefone=?, email=?, servicos_prestados=?
               WHERE id=?""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("cnpj", "").strip(),
                request.form.get("contato", "").strip(),
                request.form.get("telefone", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("servicos_prestados", "").strip(),
                fornecedor_id,
            ),
        )
        db.commit()
        flash("Fornecedor atualizado.", "sucesso")
        return redirect(url_for("gestao.fornecedores"))
    return render_template("gestao/form_fornecedor.html", fornecedor=fornecedor)


# ===================== CONTRATOS DE MANUTENÇÃO =====================
@bp.route("/contratos")
@login_required
def contratos():
    db = get_db()
    filtro = request.args.get("filtro", "")
    hoje = date.today().isoformat()
    em_30_dias = (date.today() + timedelta(days=30)).isoformat()

    sql = """SELECT c.*, f.nome AS fornecedor_nome, e.nome AS equipamento_nome, u.nome AS unidade_nome
              FROM contratos_manutencao c
              LEFT JOIN fornecedores f ON f.id = c.fornecedor_id
              LEFT JOIN equipamentos e ON e.id = c.equipamento_id
              LEFT JOIN unidades u ON u.id = c.unidade_id
              WHERE c.status = 'ativo'"""
    if filtro == "vencidos":
        sql += " AND c.data_fim IS NOT NULL AND c.data_fim < ?"
        params = [hoje]
    elif filtro == "a_vencer":
        sql += " AND c.data_fim BETWEEN ? AND ?"
        params = [hoje, em_30_dias]
    else:
        params = []
    sql += " ORDER BY c.data_fim"

    lista = db.execute(sql, params).fetchall()
    return render_template("gestao/contratos.html", contratos=lista, filtro=filtro, hoje=hoje)


@bp.route("/contratos/novo", methods=["GET", "POST"])
@login_required
def novo_contrato():
    db = get_db()
    fornecedores_lista = db.execute("SELECT id, nome FROM fornecedores WHERE ativo = 1 ORDER BY nome").fetchall()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    equipamentos = db.execute("SELECT id, nome FROM equipamentos WHERE status != 'baixado' ORDER BY nome").fetchall()

    if request.method == "POST":
        valor = request.form.get("valor", "").strip()
        db.execute(
            """INSERT INTO contratos_manutencao
               (fornecedor_id, unidade_id, equipamento_id, descricao, tipo_servico, data_inicio, data_fim, valor, observacoes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                request.form.get("fornecedor_id") or None,
                request.form.get("unidade_id") or None,
                request.form.get("equipamento_id") or None,
                request.form.get("descricao", "").strip(),
                request.form.get("tipo_servico", "").strip(),
                request.form.get("data_inicio") or None,
                request.form.get("data_fim") or None,
                float(valor) if valor else None,
                request.form.get("observacoes", "").strip(),
            ),
        )
        db.commit()
        flash("Contrato cadastrado com sucesso.", "sucesso")
        return redirect(url_for("gestao.contratos"))

    return render_template(
        "gestao/form_contrato.html", fornecedores=fornecedores_lista, unidades=unidades, equipamentos=equipamentos
    )


@bp.route("/contratos/<int:contrato_id>/encerrar", methods=["POST"])
@login_required
def encerrar_contrato(contrato_id):
    db = get_db()
    db.execute("UPDATE contratos_manutencao SET status = 'encerrado' WHERE id = ?", (contrato_id,))
    db.commit()
    flash("Contrato encerrado.", "sucesso")
    return redirect(url_for("gestao.contratos"))


# ===================== COLABORADORES =====================
@bp.route("/colaboradores")
@login_required
def colaboradores():
    db = get_db()
    lista = db.execute(
        """SELECT c.*, u.nome AS unidade_nome FROM colaboradores c
           LEFT JOIN unidades u ON u.id = c.unidade_id ORDER BY c.nome"""
    ).fetchall()
    return render_template("gestao/colaboradores.html", colaboradores=lista)


@bp.route("/colaboradores/novo", methods=["GET", "POST"])
@login_required
def novo_colaborador():
    db = get_db()
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        carga = request.form.get("carga_horaria_semanal", "").strip()
        db.execute(
            """INSERT INTO colaboradores (nome, funcao, unidade_id, telefone, email, carga_horaria_semanal)
               VALUES (?,?,?,?,?,?)""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("funcao", "").strip(),
                request.form.get("unidade_id") or None,
                request.form.get("telefone", "").strip(),
                request.form.get("email", "").strip(),
                float(carga) if carga else None,
            ),
        )
        db.commit()
        flash("Colaborador cadastrado com sucesso.", "sucesso")
        return redirect(url_for("gestao.colaboradores"))
    return render_template("gestao/form_colaborador.html", colaborador=None, unidades=unidades)


@bp.route("/colaboradores/<int:colaborador_id>/editar", methods=["GET", "POST"])
@login_required
def editar_colaborador(colaborador_id):
    db = get_db()
    colaborador = db.execute("SELECT * FROM colaboradores WHERE id = ?", (colaborador_id,)).fetchone()
    if colaborador is None:
        flash("Colaborador não encontrado.", "erro")
        return redirect(url_for("gestao.colaboradores"))
    unidades = db.execute("SELECT id, nome FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    if request.method == "POST":
        carga = request.form.get("carga_horaria_semanal", "").strip()
        db.execute(
            """UPDATE colaboradores SET nome=?, funcao=?, unidade_id=?, telefone=?, email=?, carga_horaria_semanal=?
               WHERE id=?""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("funcao", "").strip(),
                request.form.get("unidade_id") or None,
                request.form.get("telefone", "").strip(),
                request.form.get("email", "").strip(),
                float(carga) if carga else None,
                colaborador_id,
            ),
        )
        db.commit()
        flash("Colaborador atualizado.", "sucesso")
        return redirect(url_for("gestao.colaboradores"))
    return render_template("gestao/form_colaborador.html", colaborador=colaborador, unidades=unidades)


@bp.route("/colaboradores/horas", methods=["GET", "POST"])
@login_required
def horas_trabalhadas():
    db = get_db()
    colaboradores_lista = db.execute("SELECT id, nome FROM colaboradores WHERE ativo = 1 ORDER BY nome").fetchall()

    if request.method == "POST":
        numero_os = request.form.get("numero_os", "").strip()
        ordem_servico_id = None
        if numero_os:
            os_encontrada = db.execute(
                "SELECT id FROM ordens_servico WHERE numero = ?", (numero_os,)
            ).fetchone()
            if os_encontrada is None:
                flash(f"OS '{numero_os}' não encontrada — apontamento salvo sem vínculo com OS.", "aviso")
            else:
                ordem_servico_id = os_encontrada["id"]

        db.execute(
            """INSERT INTO apontamentos_horas (colaborador_id, ordem_servico_id, data, horas, observacao)
               VALUES (?,?,?,?,?)""",
            (
                request.form.get("colaborador_id"),
                ordem_servico_id,
                request.form.get("data"),
                float(request.form.get("horas", "0") or 0),
                request.form.get("observacao", "").strip(),
            ),
        )
        db.commit()
        flash("Horas registradas.", "sucesso")
        return redirect(url_for("gestao.horas_trabalhadas"))

    apontamentos = db.execute(
        """SELECT a.*, c.nome AS colaborador_nome, os.numero AS os_numero FROM apontamentos_horas a
           JOIN colaboradores c ON c.id = a.colaborador_id
           LEFT JOIN ordens_servico os ON os.id = a.ordem_servico_id
           ORDER BY a.data DESC LIMIT 50"""
    ).fetchall()
    resumo = db.execute(
        """SELECT c.nome, COALESCE(SUM(a.horas), 0) AS total_horas
           FROM colaboradores c LEFT JOIN apontamentos_horas a ON a.colaborador_id = c.id
           WHERE c.ativo = 1 GROUP BY c.id ORDER BY total_horas DESC"""
    ).fetchall()

    return render_template(
        "gestao/horas_trabalhadas.html", apontamentos=apontamentos, resumo=resumo, colaboradores=colaboradores_lista
    )


# ===================== MANUAIS (biblioteca técnica) =====================
@bp.route("/manuais", methods=["GET", "POST"])
@login_required
def manuais():
    db = get_db()

    if request.method == "POST":
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            flash("Selecione um arquivo para enviar.", "erro")
            return redirect(url_for("gestao.manuais"))
        try:
            _, caminho = salvar_arquivo(arquivo)
        except ValueError as e:
            flash(str(e), "erro")
            return redirect(url_for("gestao.manuais"))
        db.execute(
            """INSERT INTO manuais (titulo, categoria, equipamento_id, arquivo_path, criado_por)
               VALUES (?,?,?,?,?)""",
            (
                request.form.get("titulo", "").strip(),
                request.form.get("categoria", "").strip(),
                request.form.get("equipamento_id") or None,
                caminho,
                current_user.id,
            ),
        )
        db.commit()
        flash("Manual adicionado à biblioteca.", "sucesso")
        return redirect(url_for("gestao.manuais"))

    lista = db.execute(
        """SELECT m.*, e.nome AS equipamento_nome FROM manuais m
           LEFT JOIN equipamentos e ON e.id = m.equipamento_id ORDER BY m.criado_em DESC"""
    ).fetchall()
    equipamentos = db.execute("SELECT id, nome FROM equipamentos ORDER BY nome").fetchall()
    return render_template("gestao/manuais.html", manuais=lista, equipamentos=equipamentos)


# ===================== DADOS CONSOLIDADOS =====================
@bp.route("/dados-consolidados")
@login_required
def dados_consolidados():
    db = get_db()
    por_unidade = db.execute(
        """SELECT u.nome, COUNT(e.id) AS total, COALESCE(SUM(e.valor_aquisicao), 0) AS valor_total
           FROM unidades u LEFT JOIN equipamentos e ON e.unidade_id = u.id AND e.status != 'baixado'
           GROUP BY u.id ORDER BY total DESC"""
    ).fetchall()
    por_criticidade = db.execute(
        "SELECT criticidade, COUNT(*) AS total FROM equipamentos WHERE status != 'baixado' GROUP BY criticidade"
    ).fetchall()
    por_status = db.execute(
        "SELECT status, COUNT(*) AS total FROM equipamentos GROUP BY status"
    ).fetchall()
    valor_total_parque = db.execute(
        "SELECT COALESCE(SUM(valor_aquisicao), 0) AS total FROM equipamentos WHERE status != 'baixado'"
    ).fetchone()["total"]
    contratos_ativos = db.execute("SELECT COUNT(*) AS c FROM contratos_manutencao WHERE status = 'ativo'").fetchone()["c"]

    return render_template(
        "gestao/dados_consolidados.html",
        por_unidade=por_unidade,
        por_criticidade=por_criticidade,
        por_status=por_status,
        valor_total_parque=valor_total_parque,
        contratos_ativos=contratos_ativos,
    )


# ===================== RELATÓRIOS GERENCIAIS (exportação CSV) =====================
@bp.route("/relatorios-gerenciais")
@login_required
def relatorios_gerenciais():
    return render_template("gestao/relatorios_gerenciais.html")


@bp.route("/relatorios-gerenciais/equipamentos.csv")
@login_required
def exportar_equipamentos_csv():
    db = get_db()
    linhas = db.execute(
        """SELECT e.patrimonio, e.nome, e.categoria, e.fabricante, e.modelo, e.numero_serie,
                  u.nome AS unidade, s.nome AS setor, e.criticidade, e.status,
                  e.data_proxima_calibracao, e.data_proxima_preventiva
           FROM equipamentos e
           LEFT JOIN unidades u ON u.id = e.unidade_id
           LEFT JOIN setores s ON s.id = e.setor_id
           ORDER BY e.nome"""
    ).fetchall()
    return _csv_response(
        "equipamentos.csv",
        ["Patrimônio", "Nome", "Categoria", "Fabricante", "Modelo", "Nº Série", "Unidade", "Setor",
         "Criticidade", "Status", "Próx. Calibração", "Próx. Preventiva"],
        linhas,
    )


@bp.route("/relatorios-gerenciais/ordens-servico.csv")
@login_required
def exportar_os_csv():
    db = get_db()
    linhas = db.execute(
        """SELECT os.numero, e.nome AS equipamento, os.tipo, os.prioridade, os.status,
                  os.data_abertura, os.data_conclusao, os.tempo_parado_horas,
                  os.custo_pecas, os.custo_mao_obra
           FROM ordens_servico os LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           ORDER BY os.data_abertura DESC"""
    ).fetchall()
    return _csv_response(
        "ordens_servico.csv",
        ["Número", "Equipamento", "Tipo", "Prioridade", "Status", "Abertura", "Conclusão",
         "Tempo parado (h)", "Custo peças", "Custo mão de obra"],
        linhas,
    )


def _csv_response(nome_arquivo, cabecalho, linhas):
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(cabecalho)
    for linha in linhas:
        escritor.writerow([v if v is not None else "" for v in tuple(linha)])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )


# ===================== CADASTROS BÁSICOS (hub) =====================
@bp.route("/cadastros-basicos")
@login_required
def cadastros_basicos():
    return render_template("gestao/cadastros_basicos.html")


# ===================== PROCEDIMENTOS DE MANUTENÇÃO =====================
@bp.route("/procedimentos")
@login_required
def procedimentos():
    db = get_db()
    apenas_nao_publicados = request.args.get("nao_publicados") == "1"
    situacao = request.args.get("situacao", "ativo")
    sql = """SELECT p.*, (SELECT COUNT(*) FROM procedimento_itens i WHERE i.procedimento_id = p.id) AS total_itens
             FROM procedimentos_manutencao p WHERE 1=1"""
    params = []
    if apenas_nao_publicados:
        sql += " AND p.publicado = 0"
    if situacao == "ativo":
        sql += " AND p.ativo = 1"
    elif situacao == "inativo":
        sql += " AND p.ativo = 0"
    sql += " ORDER BY p.nome"
    lista = db.execute(sql, params).fetchall()
    return render_template(
        "gestao/procedimentos.html", procedimentos=lista, apenas_nao_publicados=apenas_nao_publicados, situacao=situacao
    )


@bp.route("/procedimentos/novo", methods=["GET", "POST"])
@login_required
def novo_procedimento():
    from utils import gerar_codigo_procedimento

    db = get_db()
    if request.method == "POST":
        tipo = request.form.get("tipo", "preventiva")
        codigo = gerar_codigo_procedimento(db, tipo)
        cursor = db.execute(
            """INSERT INTO procedimentos_manutencao
               (codigo, nome, tipo, categoria, titulo_relatorio, procedimento_generico, ativo)
               VALUES (?,?,?,?,?,?,?)""",
            (
                codigo,
                request.form.get("nome", "").strip(),
                tipo,
                request.form.get("categoria", "").strip(),
                request.form.get("titulo_relatorio", "").strip(),
                1 if request.form.get("procedimento_generico") else 0,
                1 if request.form.get("ativo") else 0,
            ),
        )
        db.commit()
        flash(f"Procedimento {codigo} cadastrado. Adicione os blocos de verificação e os itens do checklist.", "sucesso")
        return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=cursor.lastrowid))
    return render_template("gestao/form_procedimento.html", procedimento=None)


@bp.route("/procedimentos/<int:procedimento_id>/editar", methods=["GET", "POST"])
@login_required
def editar_procedimento(procedimento_id):
    db = get_db()
    procedimento = db.execute("SELECT * FROM procedimentos_manutencao WHERE id = ?", (procedimento_id,)).fetchone()
    if procedimento is None:
        flash("Procedimento não encontrado.", "erro")
        return redirect(url_for("gestao.procedimentos"))
    if request.method == "POST":
        db.execute(
            """UPDATE procedimentos_manutencao SET nome=?, tipo=?, categoria=?, titulo_relatorio=?,
               procedimento_generico=?, ativo=? WHERE id=?""",
            (
                request.form.get("nome", "").strip(),
                request.form.get("tipo", "preventiva"),
                request.form.get("categoria", "").strip(),
                request.form.get("titulo_relatorio", "").strip(),
                1 if request.form.get("procedimento_generico") else 0,
                1 if request.form.get("ativo") else 0,
                procedimento_id,
            ),
        )
        db.commit()
        flash("Procedimento atualizado.", "sucesso")
        return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=procedimento_id))
    return render_template("gestao/form_procedimento.html", procedimento=procedimento)


@bp.route("/procedimentos/<int:procedimento_id>/publicar", methods=["POST"])
@login_required
def publicar_procedimento(procedimento_id):
    db = get_db()
    db.execute(
        "UPDATE procedimentos_manutencao SET publicado = 1, data_publicacao = datetime('now', 'localtime') WHERE id = ?",
        (procedimento_id,),
    )
    db.commit()
    flash("Procedimento publicado.", "sucesso")
    return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=procedimento_id))


@bp.route("/procedimentos/<int:procedimento_id>/duplicar", methods=["POST"])
@login_required
def duplicar_procedimento(procedimento_id):
    from utils import gerar_codigo_procedimento

    db = get_db()
    original = db.execute("SELECT * FROM procedimentos_manutencao WHERE id = ?", (procedimento_id,)).fetchone()
    if original is None:
        flash("Procedimento não encontrado.", "erro")
        return redirect(url_for("gestao.procedimentos"))
    codigo = gerar_codigo_procedimento(db, original["tipo"])
    cursor = db.execute(
        """INSERT INTO procedimentos_manutencao
           (codigo, nome, tipo, categoria, titulo_relatorio, procedimento_generico, ativo)
           VALUES (?,?,?,?,?,?,0)""",
        (
            codigo,
            f"{original['nome']} (cópia)",
            original["tipo"],
            original["categoria"],
            original["titulo_relatorio"],
            original["procedimento_generico"],
        ),
    )
    novo_id = cursor.lastrowid
    blocos = db.execute("SELECT * FROM procedimento_blocos WHERE procedimento_id = ? ORDER BY ordem, id", (procedimento_id,)).fetchall()
    for bloco in blocos:
        novo_bloco = db.execute(
            "INSERT INTO procedimento_blocos (procedimento_id, ordem, descricao, calibra_componente, instrucoes_gerais) VALUES (?,?,?,?,?)",
            (novo_id, bloco["ordem"], bloco["descricao"], bloco["calibra_componente"], bloco["instrucoes_gerais"]),
        )
        itens = db.execute("SELECT * FROM procedimento_itens WHERE bloco_id = ? ORDER BY ordem, id", (bloco["id"],)).fetchall()
        for item in itens:
            db.execute(
                "INSERT INTO procedimento_itens (procedimento_id, bloco_id, ordem, descricao, ativo) VALUES (?,?,?,?,?)",
                (novo_id, novo_bloco.lastrowid, item["ordem"], item["descricao"], item["ativo"]),
            )
    db.commit()
    flash(f"Procedimento duplicado como {codigo}.", "sucesso")
    return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=novo_id))


@bp.route("/procedimentos/<int:procedimento_id>")
@login_required
def detalhe_procedimento(procedimento_id):
    db = get_db()
    procedimento = db.execute("SELECT * FROM procedimentos_manutencao WHERE id = ?", (procedimento_id,)).fetchone()
    if procedimento is None:
        flash("Procedimento não encontrado.", "erro")
        return redirect(url_for("gestao.procedimentos"))
    blocos = db.execute(
        "SELECT * FROM procedimento_blocos WHERE procedimento_id = ? ORDER BY ordem, id", (procedimento_id,)
    ).fetchall()
    itens_por_bloco = {}
    for bloco in blocos:
        itens_por_bloco[bloco["id"]] = db.execute(
            "SELECT * FROM procedimento_itens WHERE bloco_id = ? ORDER BY ordem, id", (bloco["id"],)
        ).fetchall()
    itens_sem_bloco = db.execute(
        "SELECT * FROM procedimento_itens WHERE procedimento_id = ? AND bloco_id IS NULL ORDER BY ordem, id", (procedimento_id,)
    ).fetchall()
    return render_template(
        "gestao/detalhe_procedimento.html",
        procedimento=procedimento,
        blocos=blocos,
        itens_por_bloco=itens_por_bloco,
        itens_sem_bloco=itens_sem_bloco,
    )


@bp.route("/procedimentos/<int:procedimento_id>/bloco", methods=["POST"])
@login_required
def adicionar_bloco_procedimento(procedimento_id):
    db = get_db()
    descricao = request.form.get("descricao", "").strip()
    if descricao:
        proxima_ordem = db.execute(
            "SELECT COALESCE(MAX(ordem), 0) + 1 AS o FROM procedimento_blocos WHERE procedimento_id = ?", (procedimento_id,)
        ).fetchone()["o"]
        db.execute(
            "INSERT INTO procedimento_blocos (procedimento_id, ordem, descricao, calibra_componente, instrucoes_gerais) VALUES (?,?,?,?,?)",
            (
                procedimento_id,
                proxima_ordem,
                descricao,
                1 if request.form.get("calibra_componente") else 0,
                request.form.get("instrucoes_gerais", "").strip() or None,
            ),
        )
        db.commit()
        flash("Bloco de verificação adicionado.", "sucesso")
    return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=procedimento_id))


@bp.route("/procedimentos/<int:procedimento_id>/blocos/<int:bloco_id>/item", methods=["POST"])
@login_required
def adicionar_item_procedimento(procedimento_id, bloco_id):
    db = get_db()
    descricao = request.form.get("descricao", "").strip()
    if descricao:
        proxima_ordem = db.execute(
            "SELECT COALESCE(MAX(ordem), 0) + 1 AS o FROM procedimento_itens WHERE bloco_id = ?", (bloco_id,)
        ).fetchone()["o"]
        db.execute(
            "INSERT INTO procedimento_itens (procedimento_id, bloco_id, ordem, descricao) VALUES (?,?,?,?)",
            (procedimento_id, bloco_id, proxima_ordem, descricao),
        )
        db.commit()
        flash("Item adicionado ao checklist.", "sucesso")
    return redirect(url_for("gestao.detalhe_procedimento", procedimento_id=procedimento_id))


# ===================== VINCULAR PROCEDIMENTOS A MODELOS =====================
@bp.route("/vincular-procedimentos", methods=["GET", "POST"])
@login_required
def vincular_procedimentos():
    db = get_db()
    if request.method == "POST":
        modelo_id = request.form.get("modelo_id")
        procedimento_id = request.form.get("procedimento_id")
        try:
            db.execute(
                "INSERT INTO modelo_procedimentos (modelo_id, procedimento_id) VALUES (?,?)",
                (modelo_id, procedimento_id),
            )
            db.commit()
            flash("Procedimento vinculado ao modelo.", "sucesso")
        except Exception:
            flash("Esse procedimento já está vinculado a esse modelo.", "erro")
        return redirect(url_for("gestao.vincular_procedimentos"))

    modelos = db.execute("SELECT id, nome FROM modelos WHERE ativo = 1 ORDER BY nome").fetchall()
    procedimentos_lista = db.execute("SELECT id, nome FROM procedimentos_manutencao ORDER BY nome").fetchall()
    vinculos = db.execute(
        """SELECT mp.*, mo.nome AS modelo_nome, p.nome AS procedimento_nome FROM modelo_procedimentos mp
           JOIN modelos mo ON mo.id = mp.modelo_id
           JOIN procedimentos_manutencao p ON p.id = mp.procedimento_id
           ORDER BY mo.nome, p.nome"""
    ).fetchall()
    return render_template(
        "gestao/vincular_procedimentos.html", modelos=modelos, procedimentos=procedimentos_lista, vinculos=vinculos
    )


@bp.route("/vincular-procedimentos/<int:vinculo_id>/remover", methods=["POST"])
@login_required
def remover_vinculo_procedimento(vinculo_id):
    db = get_db()
    db.execute("DELETE FROM modelo_procedimentos WHERE id = ?", (vinculo_id,))
    db.commit()
    flash("Vínculo removido.", "sucesso")
    return redirect(url_for("gestao.vincular_procedimentos"))


# ===================== AGENDADOR DE RELATÓRIOS (configuração) =====================
@bp.route("/agendador-relatorios", methods=["GET", "POST"])
@login_required
@admin_required
def agendador_relatorios():
    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO agendamentos_relatorio (relatorio, frequencia, destinatarios, criado_por) VALUES (?,?,?,?)",
            (
                request.form.get("relatorio", "").strip(),
                request.form.get("frequencia", "semanal"),
                request.form.get("destinatarios", "").strip(),
                current_user.id,
            ),
        )
        db.commit()
        flash("Agendamento salvo. O envio automático só dispara se houver um servidor de e-mail (SMTP) configurado e o app rodando continuamente — nenhum dos dois existe nesta instalação local ainda.", "aviso")
        return redirect(url_for("gestao.agendador_relatorios"))

    lista = db.execute("SELECT * FROM agendamentos_relatorio ORDER BY criado_em DESC").fetchall()
    return render_template("gestao/agendador_relatorios.html", agendamentos=lista)


@bp.route("/agendador-relatorios/<int:agendamento_id>/alternar", methods=["POST"])
@login_required
@admin_required
def alternar_agendamento(agendamento_id):
    db = get_db()
    agendamento = db.execute("SELECT * FROM agendamentos_relatorio WHERE id = ?", (agendamento_id,)).fetchone()
    if agendamento:
        db.execute("UPDATE agendamentos_relatorio SET ativo = ? WHERE id = ?", (0 if agendamento["ativo"] else 1, agendamento_id))
        db.commit()
    return redirect(url_for("gestao.agendador_relatorios"))


# ===================== SENSORES (leitura manual) =====================
@bp.route("/sensores", methods=["GET", "POST"])
@login_required
def sensores():
    db = get_db()
    equipamentos = db.execute("SELECT id, nome FROM equipamentos WHERE status != 'baixado' ORDER BY nome").fetchall()

    if request.method == "POST":
        db.execute(
            "INSERT INTO sensores (nome, equipamento_id, tipo_medida, unidade_medida, valor_minimo, valor_maximo) VALUES (?,?,?,?,?,?)",
            (
                request.form.get("nome", "").strip(),
                request.form.get("equipamento_id") or None,
                request.form.get("tipo_medida", "").strip(),
                request.form.get("unidade_medida", "un").strip(),
                request.form.get("valor_minimo") or None,
                request.form.get("valor_maximo") or None,
            ),
        )
        db.commit()
        flash("Sensor cadastrado para leitura manual.", "sucesso")
        return redirect(url_for("gestao.sensores"))

    lista = db.execute(
        """SELECT s.*, e.nome AS equipamento_nome,
                  (SELECT valor FROM leituras_sensor l WHERE l.sensor_id = s.id ORDER BY l.criado_em DESC LIMIT 1) AS ultima_leitura
           FROM sensores s LEFT JOIN equipamentos e ON e.id = s.equipamento_id
           WHERE s.ativo = 1 ORDER BY s.nome"""
    ).fetchall()
    return render_template("gestao/sensores.html", sensores=lista, equipamentos=equipamentos)


@bp.route("/sensores/<int:sensor_id>/leitura", methods=["POST"])
@login_required
def registrar_leitura_sensor(sensor_id):
    db = get_db()
    valor = request.form.get("valor")
    if valor:
        db.execute(
            "INSERT INTO leituras_sensor (sensor_id, valor, registrado_por) VALUES (?,?,?)",
            (sensor_id, float(valor), current_user.id),
        )
        db.commit()
        flash("Leitura registrada.", "sucesso")
    return redirect(url_for("gestao.sensores"))


# ===================== GERAR OS A PARTIR DE UM PLANO =====================
@bp.route("/planos-manutencao/<int:plano_id>/gerar-os", methods=["GET", "POST"])
@login_required
def gerar_os_de_plano(plano_id):
    from utils import gerar_numero_os

    db = get_db()
    plano = db.execute("SELECT * FROM planos_manutencao WHERE id = ?", (plano_id,)).fetchone()
    if plano is None:
        flash("Plano não encontrado.", "erro")
        return redirect(url_for("gestao.planos_manutencao"))

    if request.method == "POST":
        equipamento_id = request.form.get("equipamento_id") or None
        numero = gerar_numero_os(db)
        cursor = db.execute(
            """INSERT INTO ordens_servico
               (numero, equipamento_id, tipo, prioridade, descricao_problema, tecnico_id,
                empresa_terceirizada, centro_custo_id, plano_manutencao_id, criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                numero, equipamento_id, plano["tipo_manutencao"], plano["prioridade"],
                f"Gerada pelo plano: {plano['nome']}", plano["responsavel_id"],
                None, None, plano_id, current_user.id,
            ),
        )
        ordem_id = cursor.lastrowid
        db.execute(
            """INSERT INTO ordem_servico_historico (ordem_servico_id, status_anterior, status_novo, usuario_id, observacao)
               VALUES (?, NULL, 'aberta', ?, ?)""",
            (ordem_id, current_user.id, f"Gerada a partir do plano '{plano['nome']}'"),
        )

        if plano["exigir_checklist"] and plano["procedimento_id"]:
            itens = db.execute(
                "SELECT id FROM procedimento_itens WHERE procedimento_id = ?", (plano["procedimento_id"],)
            ).fetchall()
            for item in itens:
                db.execute(
                    "INSERT INTO plano_manutencao_checklist (ordem_servico_id, procedimento_item_id) VALUES (?,?)",
                    (ordem_id, item["id"]),
                )

        db.commit()
        flash(f"Ordem de serviço {numero} gerada a partir do plano.", "sucesso")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    equipamentos = db.execute(
        "SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome"
    ).fetchall()
    return render_template("gestao/gerar_os_plano.html", plano=plano, equipamentos=equipamentos)


@bp.route("/gec-maps")
@login_required
def gec_maps():
    return render_template(
        "gestao/em_construcao.html",
        titulo="GEC Maps",
        descricao="Localização geográfica/planta baixa dos equipamentos. Precisamos definir a fonte do mapa (planta do prédio, coordenadas, etc.).",
    )

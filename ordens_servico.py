from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db
from utils import gerar_numero_os, salvar_arquivo

bp = Blueprint("ordens_servico", __name__, url_prefix="/ordens-servico")

STATUS_LABELS = {
    "aberta": "Aberta",
    "em_andamento": "Em andamento",
    "aguardando_peca": "Aguardando peça",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
TIPO_LABELS = {
    "corretiva": "Corretiva",
    "preventiva": "Preventiva",
    "calibracao": "Calibração",
    "instalacao": "Instalação",
    "inspecao": "Inspeção",
    "administrativo": "Administrativo",
    "gerencial": "Gerencial",
    "inventario": "Inventário",
    "qualificacao": "Qualificação",
    "recebimento": "Recebimento",
    "ronda": "Ronda",
    "seguranca_eletrica": "Segurança Elétrica",
    "transporte": "Transporte",
    "treinamento": "Treinamento",
    "inspecao_tecnica": "Inspeção Técnica",
    "pesquisa_clinica": "Pesquisa Clínica",
    "reuniao_estrategica": "Reunião Estratégica",
}
PRIORIDADE_LABELS = {"baixa": "Baixa", "media": "Média", "alta": "Alta", "critica": "Crítica"}


def _buscar_ordens(status="", tipo="", prioridade="", termo="", atrasada=False, minhas=False,
                    solicitante=None, sem_tecnico=False, aguardando_orcamento=False,
                    apenas_abertas=False, ordenar="padrao"):
    db = get_db()
    sql = """SELECT os.*, e.nome AS equipamento_nome, e.patrimonio, e.tag, s.nome AS setor_nome,
                     u.nome AS unidade_nome, us.nome AS tecnico_nome
              FROM ordens_servico os
              LEFT JOIN equipamentos e ON e.id = os.equipamento_id
              LEFT JOIN setores s ON s.id = e.setor_id
              LEFT JOIN unidades u ON u.id = e.unidade_id
              LEFT JOIN usuarios us ON us.id = os.tecnico_id
              WHERE 1=1"""
    params = []
    if status:
        sql += " AND os.status = ?"
        params.append(status)
    if tipo:
        sql += " AND os.tipo = ?"
        params.append(tipo)
    if prioridade:
        sql += " AND os.prioridade = ?"
        params.append(prioridade)
    if termo:
        sql += " AND (os.numero LIKE ? OR e.nome LIKE ? OR os.descricao_problema LIKE ? OR e.tag LIKE ?)"
        curinga = f"%{termo}%"
        params += [curinga, curinga, curinga, curinga]
    if atrasada:
        sql += """ AND os.status IN ('aberta','em_andamento','aguardando_peca')
                   AND os.data_agendada IS NOT NULL AND os.data_agendada < date('now','localtime')"""
    if minhas:
        sql += " AND os.tecnico_id = ?"
        params.append(current_user.id)
    if solicitante:
        sql += " AND os.solicitante = ?"
        params.append(solicitante)
    if sem_tecnico:
        sql += " AND os.tecnico_id IS NULL"
    if aguardando_orcamento:
        sql += " AND os.aguardando_aprovacao_orcamento = 1"
    if apenas_abertas:
        sql += " AND os.status IN ('aberta','em_andamento','aguardando_peca')"

    if ordenar == "abertura_asc":
        sql += " ORDER BY os.data_abertura ASC"
    elif ordenar == "unidade":
        sql += " ORDER BY u.nome, os.data_abertura DESC"
    else:
        sql += """ ORDER BY CASE os.status WHEN 'aberta' THEN 0 WHEN 'em_andamento' THEN 1
                   WHEN 'aguardando_peca' THEN 2 WHEN 'concluida' THEN 3 ELSE 4 END, os.data_abertura DESC"""

    return db.execute(sql, params).fetchall()


def _renderizar_lista(ordens, titulo=None, subtitulo=None, filtros=None, mostrar_filtros=True):
    return render_template(
        "ordens_servico/lista.html",
        ordens=ordens,
        titulo=titulo,
        subtitulo=subtitulo,
        filtros=filtros or {"status": "", "tipo": "", "prioridade": "", "q": ""},
        mostrar_filtros=mostrar_filtros,
        status_labels=STATUS_LABELS,
        tipo_labels=TIPO_LABELS,
        prioridade_labels=PRIORIDADE_LABELS,
    )


@bp.route("/")
@login_required
def lista():
    status = request.args.get("status", "")
    tipo = request.args.get("tipo", "")
    prioridade = request.args.get("prioridade", "")
    termo = request.args.get("q", "").strip()
    atrasada = request.args.get("atrasada", "")
    minhas = request.args.get("minhas", "")

    ordens = _buscar_ordens(status=status, tipo=tipo, prioridade=prioridade, termo=termo,
                             atrasada=atrasada, minhas=minhas)
    return _renderizar_lista(ordens, filtros={"status": status, "tipo": tipo, "prioridade": prioridade, "q": termo})


@bp.route("/gec")
@login_required
def lista_gec():
    ordens = _buscar_ordens(apenas_abertas=True, ordenar="abertura_asc")
    return _renderizar_lista(
        ordens,
        titulo="Ordens de Serviço GEC",
        subtitulo="Lista simplificada das OS em aberto, para uso rápido em campo",
        mostrar_filtros=False,
    )


@bp.route("/minhas-requisicoes")
@login_required
def minhas_requisicoes():
    ordens = _buscar_ordens(solicitante=current_user.nome)
    return _renderizar_lista(
        ordens,
        titulo="Minhas Requisições de Serviço",
        subtitulo="Ordens de serviço solicitadas por você",
        mostrar_filtros=False,
    )


@bp.route("/administrar-requisicoes")
@login_required
def administrar_requisicoes():
    db = get_db()
    requisicoes = db.execute(
        """SELECT r.*, e.nome AS equipamento_nome
           FROM requisicoes_servico r
           LEFT JOIN equipamentos e ON e.id = r.equipamento_id
           WHERE r.status = 'pendente'
           ORDER BY r.data_abertura"""
    ).fetchall()
    return render_template("ordens_servico/requisicoes.html", requisicoes=requisicoes)


@bp.route("/requisicoes/<int:requisicao_id>/abrir-os", methods=["GET", "POST"])
@login_required
def abrir_os_requisicao(requisicao_id):
    from utils import gerar_numero_os

    db = get_db()
    requisicao = db.execute("SELECT * FROM requisicoes_servico WHERE id = ?", (requisicao_id,)).fetchone()
    if requisicao is None or requisicao["status"] != "pendente":
        flash("Requisição não encontrada ou já processada.", "erro")
        return redirect(url_for("ordens_servico.administrar_requisicoes"))

    if request.method == "POST":
        numero = gerar_numero_os(db)
        cursor = db.execute(
            """INSERT INTO ordens_servico
               (numero, equipamento_id, tipo, prioridade, descricao_problema, solicitante, criado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (
                numero,
                request.form.get("equipamento_id") or requisicao["equipamento_id"],
                request.form.get("tipo", "corretiva"),
                requisicao["prioridade"],
                requisicao["ocorrencia"] or requisicao["descricao_equipamento_setor"] or "Requisição de serviço",
                requisicao["solicitante_nome"],
                current_user.id,
            ),
        )
        ordem_id = cursor.lastrowid
        db.execute(
            "UPDATE requisicoes_servico SET status = 'convertida', ordem_servico_id = ? WHERE id = ?",
            (ordem_id, requisicao_id),
        )
        db.commit()
        flash(f"OS {numero} aberta a partir da requisição.", "sucesso")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    equipamentos = db.execute("SELECT id, nome, patrimonio FROM equipamentos ORDER BY nome").fetchall()
    return render_template("ordens_servico/abrir_os_requisicao.html", requisicao=requisicao, equipamentos=equipamentos, tipo_labels=TIPO_LABELS)


@bp.route("/requisicoes/<int:requisicao_id>/negar", methods=["POST"])
@login_required
def negar_requisicao(requisicao_id):
    db = get_db()
    motivo = request.form.get("motivo", "").strip()
    db.execute(
        "UPDATE requisicoes_servico SET status = 'negada', motivo_negativa = ? WHERE id = ?",
        (motivo, requisicao_id),
    )
    db.commit()
    flash("Requisição negada.", "sucesso")
    return redirect(url_for("ordens_servico.administrar_requisicoes"))


@bp.route("/monitor")
@login_required
def monitor():
    ordens = _buscar_ordens(apenas_abertas=True, ordenar="abertura_asc")
    return _renderizar_lista(
        ordens,
        titulo="Monitor de Atendimento",
        subtitulo="Todas as OS em aberto, da mais antiga para a mais recente",
        mostrar_filtros=False,
    )


@bp.route("/monitor-gec")
@login_required
def monitor_gec():
    ordens = _buscar_ordens(apenas_abertas=True, ordenar="unidade")
    return _renderizar_lista(
        ordens,
        titulo="Monitor de Atendimento GEC",
        subtitulo="OS em aberto agrupadas por unidade",
        mostrar_filtros=False,
    )


@bp.route("/pendencias")
@login_required
def pendencias():
    db = get_db()
    ordens = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome, e.patrimonio, us.nome AS tecnico_nome
           FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           LEFT JOIN usuarios us ON us.id = os.tecnico_id
           WHERE os.status = 'aguardando_peca'
              OR (os.status IN ('aberta','em_andamento') AND os.data_agendada IS NOT NULL
                  AND os.data_agendada < date('now','localtime'))
           ORDER BY os.data_agendada"""
    ).fetchall()
    return _renderizar_lista(
        ordens,
        titulo="Pendência das Ordens de Serviço",
        subtitulo="OS aguardando peça ou com prazo vencido",
        mostrar_filtros=False,
    )


@bp.route("/rapida", methods=["GET", "POST"])
@login_required
def rapida():
    db = get_db()
    equipamentos = db.execute(
        "SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome"
    ).fetchall()

    if request.method == "POST":
        equipamento_id = request.form.get("equipamento_id") or None
        descricao_problema = request.form.get("descricao_problema", "").strip()
        if not descricao_problema:
            flash("Descreva rapidamente o problema.", "erro")
            return render_template("ordens_servico/rapida.html", equipamentos=equipamentos)

        numero = gerar_numero_os(db)
        cursor = db.execute(
            """INSERT INTO ordens_servico (numero, equipamento_id, tipo, prioridade, descricao_problema, criado_por)
               VALUES (?, ?, 'corretiva', 'media', ?, ?)""",
            (numero, equipamento_id, descricao_problema, current_user.id),
        )
        ordem_id = cursor.lastrowid
        db.execute(
            """INSERT INTO ordem_servico_historico (ordem_servico_id, status_anterior, status_novo, usuario_id, observacao)
               VALUES (?, NULL, 'aberta', ?, 'Ordem de serviço rápida criada')""",
            (ordem_id, current_user.id),
        )
        db.commit()
        flash(f"Ordem de serviço {numero} criada.", "sucesso")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    return render_template("ordens_servico/rapida.html", equipamentos=equipamentos)


@bp.route("/manutencoes-previstas")
@login_required
def manutencoes_previstas():
    from datetime import date, timedelta

    db = get_db()
    em_30_dias = (date.today() + timedelta(days=30)).isoformat()

    preventivas = db.execute(
        """SELECT e.id, e.nome, e.patrimonio, u.nome AS unidade_nome, e.data_proxima_preventiva AS data
           FROM equipamentos e LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.periodicidade_preventiva_meses IS NOT NULL AND e.data_proxima_preventiva <= ?
           AND e.status != 'baixado' ORDER BY e.data_proxima_preventiva""",
        (em_30_dias,),
    ).fetchall()
    calibracoes = db.execute(
        """SELECT e.id, e.nome, e.patrimonio, u.nome AS unidade_nome, e.data_proxima_calibracao AS data
           FROM equipamentos e LEFT JOIN unidades u ON u.id = e.unidade_id
           WHERE e.necessita_calibracao = 1 AND e.data_proxima_calibracao <= ?
           AND e.status != 'baixado' ORDER BY e.data_proxima_calibracao""",
        (em_30_dias,),
    ).fetchall()

    return render_template(
        "ordens_servico/manutencoes_previstas.html", preventivas=preventivas, calibracoes=calibracoes
    )


@bp.route("/manutencoes-previstas/gerar/<int:equipamento_id>/<tipo>", methods=["POST"])
@login_required
def gerar_manutencao(equipamento_id, tipo):
    if tipo not in ("preventiva", "calibracao"):
        flash("Tipo de manutenção inválido.", "erro")
        return redirect(url_for("ordens_servico.manutencoes_previstas"))

    db = get_db()
    equipamento = db.execute("SELECT * FROM equipamentos WHERE id = ?", (equipamento_id,)).fetchone()
    if equipamento is None:
        flash("Equipamento não encontrado.", "erro")
        return redirect(url_for("ordens_servico.manutencoes_previstas"))

    descricao = "Preventiva programada" if tipo == "preventiva" else "Calibração programada"
    numero = gerar_numero_os(db)
    cursor = db.execute(
        """INSERT INTO ordens_servico (numero, equipamento_id, tipo, prioridade, descricao_problema, criado_por)
           VALUES (?, ?, ?, 'media', ?, ?)""",
        (numero, equipamento_id, tipo, f"{descricao} — {equipamento['nome']}", current_user.id),
    )
    ordem_id = cursor.lastrowid
    db.execute(
        """INSERT INTO ordem_servico_historico (ordem_servico_id, status_anterior, status_novo, usuario_id, observacao)
           VALUES (?, NULL, 'aberta', ?, 'Gerada a partir dos planos de manutenção previstos')""",
        (ordem_id, current_user.id),
    )
    db.commit()
    flash(f"Ordem de serviço {numero} gerada para {equipamento['nome']}.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/agenda-equipe")
@login_required
def agenda_equipe():
    db = get_db()
    ordens = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome, us.nome AS tecnico_nome
           FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           LEFT JOIN usuarios us ON us.id = os.tecnico_id
           WHERE os.data_agendada IS NOT NULL AND os.status IN ('aberta','em_andamento','aguardando_peca')
           ORDER BY os.data_agendada, us.nome"""
    ).fetchall()
    return render_template("ordens_servico/agenda_equipe.html", ordens=ordens, status_labels=STATUS_LABELS)


@bp.route("/kanban")
@login_required
def kanban():
    db = get_db()
    ordens = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           WHERE os.status != 'cancelada'
           ORDER BY os.prioridade DESC, os.data_abertura"""
    ).fetchall()
    colunas = {"aberta": [], "em_andamento": [], "aguardando_peca": [], "concluida": []}
    for os_item in ordens:
        colunas.setdefault(os_item["status"], []).append(os_item)
    return render_template("ordens_servico/kanban.html", colunas=colunas, status_labels=STATUS_LABELS)


@bp.route("/auditoria")
@login_required
def auditoria():
    db = get_db()
    eventos = db.execute(
        """SELECT h.*, os.numero AS os_numero, u.nome AS usuario_nome
           FROM ordem_servico_historico h
           JOIN ordens_servico os ON os.id = h.ordem_servico_id
           LEFT JOIN usuarios u ON u.id = h.usuario_id
           ORDER BY h.criado_em DESC LIMIT 200"""
    ).fetchall()
    return render_template("ordens_servico/auditoria.html", eventos=eventos, status_labels=STATUS_LABELS)


@bp.route("/certificados")
@login_required
def certificados():
    db = get_db()
    termo = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")

    lista_certificados = db.execute(
        """SELECT a.*, e.nome AS equipamento_nome, os.numero AS os_numero
           FROM anexos a
           LEFT JOIN equipamentos e ON e.id = a.equipamento_id
           LEFT JOIN ordens_servico os ON os.id = a.ordem_servico_id
           WHERE a.tipo = 'certificado'
           ORDER BY a.criado_em DESC"""
    ).fetchall()

    sql_oficiais = """SELECT os.id AS ordem_id, os.numero, os.tipo, os.data_conclusao,
                              os.certificado_numero, os.certificado_situacao, os.certificado_validade,
                              e.nome AS equipamento_nome
                       FROM ordens_servico os
                       LEFT JOIN equipamentos e ON e.id = os.equipamento_id
                       WHERE os.certificado_numero IS NOT NULL"""
    params_oficiais = []
    if termo:
        sql_oficiais += " AND (os.numero LIKE ? OR e.nome LIKE ? OR os.certificado_numero LIKE ?)"
        curinga = f"%{termo}%"
        params_oficiais += [curinga, curinga, curinga]
    if tipo:
        sql_oficiais += " AND os.tipo = ?"
        params_oficiais.append(tipo)
    sql_oficiais += " ORDER BY os.data_conclusao DESC LIMIT 500"
    certificados_oficiais = db.execute(sql_oficiais, params_oficiais).fetchall()

    sql = """SELECT os.id AS ordem_id, os.numero, os.tipo, os.data_conclusao, os.data_abertura,
                     e.nome AS equipamento_nome
              FROM ordens_servico os
              LEFT JOIN equipamentos e ON e.id = os.equipamento_id
              WHERE os.tipo IN ('preventiva', 'calibracao') AND os.status = 'concluida'
                AND os.certificado_numero IS NULL
                AND NOT EXISTS (SELECT 1 FROM anexos a WHERE a.ordem_servico_id = os.id AND a.tipo = 'certificado')"""
    params = []
    if termo:
        sql += " AND (os.numero LIKE ? OR e.nome LIKE ?)"
        curinga = f"%{termo}%"
        params += [curinga, curinga]
    if tipo:
        sql += " AND os.tipo = ?"
        params.append(tipo)
    sql += " ORDER BY os.data_conclusao DESC LIMIT 500"
    certificados_gerados = db.execute(sql, params).fetchall()

    return render_template(
        "ordens_servico/certificados.html",
        certificados=lista_certificados,
        certificados_oficiais=certificados_oficiais,
        certificados_gerados=certificados_gerados,
        apenas_pendentes=False,
        filtros={"q": termo, "tipo": tipo},
        tipo_labels=TIPO_LABELS,
    )


@bp.route("/<int:ordem_id>/certificado")
@login_required
def certificado(ordem_id):
    db = get_db()
    ordem = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome, e.fabricante, e.modelo, e.numero_serie, e.tag,
                  e.patrimonio, u.nome AS unidade_nome, s.nome AS setor_nome, t.nome AS tecnico_nome
           FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           LEFT JOIN unidades u ON u.id = e.unidade_id
           LEFT JOIN setores s ON s.id = e.setor_id
           LEFT JOIN usuarios t ON t.id = os.tecnico_id
           WHERE os.id = ?""",
        (ordem_id,),
    ).fetchone()
    if ordem is None:
        flash("Ordem de serviço não encontrada.", "erro")
        return redirect(url_for("ordens_servico.certificados"))
    if ordem["tipo"] not in ("preventiva", "calibracao"):
        flash("Certificado disponível apenas para OS de preventiva ou calibração.", "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    checklist = db.execute(
        """SELECT pi.descricao, c.concluido
           FROM plano_manutencao_checklist c
           JOIN procedimento_itens pi ON pi.id = c.procedimento_item_id
           WHERE c.ordem_servico_id = ?
           ORDER BY pi.ordem, pi.id""",
        (ordem_id,),
    ).fetchall()

    titulo = "Certificado de Calibração" if ordem["tipo"] == "calibracao" else "Certificado de Manutenção Preventiva"
    if ordem["plano_manutencao_id"]:
        procedimento = db.execute(
            """SELECT p.titulo_relatorio FROM planos_manutencao pl
               JOIN procedimentos_manutencao p ON p.id = pl.procedimento_id
               WHERE pl.id = ?""",
            (ordem["plano_manutencao_id"],),
        ).fetchone()
        if procedimento and procedimento["titulo_relatorio"]:
            titulo = procedimento["titulo_relatorio"]

    return render_template(
        "ordens_servico/certificado.html",
        ordem=ordem,
        checklist=checklist,
        titulo=titulo,
        tipo_labels=TIPO_LABELS,
        nome_organizacao="Fundação Altino Ventura",
    )


@bp.route("/certificados/aguardando-analise")
@login_required
def certificados_aguardando_analise():
    db = get_db()
    lista_certificados = db.execute(
        """SELECT a.*, e.nome AS equipamento_nome, os.numero AS os_numero
           FROM anexos a
           LEFT JOIN equipamentos e ON e.id = a.equipamento_id
           LEFT JOIN ordens_servico os ON os.id = a.ordem_servico_id
           WHERE a.tipo = 'certificado' AND a.revisado = 0
           ORDER BY a.criado_em DESC"""
    ).fetchall()
    return render_template("ordens_servico/certificados.html", certificados=lista_certificados, apenas_pendentes=True)


@bp.route("/certificados/<int:anexo_id>/revisar", methods=["POST"])
@login_required
def revisar_certificado(anexo_id):
    db = get_db()
    db.execute("UPDATE anexos SET revisado = 1 WHERE id = ?", (anexo_id,))
    db.commit()
    flash("Certificado marcado como analisado.", "sucesso")
    return redirect(request.referrer or url_for("ordens_servico.certificados"))


@bp.route("/cadastros-basicos")
@login_required
def cadastros_basicos():
    return render_template("ordens_servico/cadastros_basicos.html")


@bp.route("/servicos-externos-orcamento")
@login_required
def servicos_externos_orcamento():
    ordens = _buscar_ordens(aguardando_orcamento=True)
    return _renderizar_lista(
        ordens,
        titulo="Serviços Externos Aguardando Aprovação do Orçamento",
        subtitulo="Ordens de serviço com empresa terceirizada aguardando aprovação de valor",
        mostrar_filtros=False,
    )


@bp.route("/<int:ordem_id>/aprovar-orcamento", methods=["POST"])
@login_required
def aprovar_orcamento(ordem_id):
    db = get_db()
    db.execute(
        "UPDATE ordens_servico SET aguardando_aprovacao_orcamento = 0 WHERE id = ?", (ordem_id,)
    )
    db.commit()
    flash("Orçamento aprovado.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/<int:ordem_id>/checklist/<int:item_id>/alternar", methods=["POST"])
@login_required
def alternar_checklist(ordem_id, item_id):
    db = get_db()
    item = db.execute(
        "SELECT * FROM plano_manutencao_checklist WHERE ordem_servico_id = ? AND procedimento_item_id = ?",
        (ordem_id, item_id),
    ).fetchone()
    if item:
        db.execute(
            "UPDATE plano_manutencao_checklist SET concluido = ? WHERE id = ?",
            (0 if item["concluido"] else 1, item["id"]),
        )
        db.commit()
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/<int:ordem_id>/assinar", methods=["POST"])
@login_required
def assinar(ordem_id):
    db = get_db()
    nome_declarado = request.form.get("nome_declarado", "").strip()
    if not nome_declarado:
        flash("Digite seu nome completo para confirmar a assinatura.", "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    db.execute(
        "INSERT INTO assinaturas (ordem_servico_id, usuario_id, nome_declarado, ip) VALUES (?,?,?,?)",
        (ordem_id, current_user.id, nome_declarado, request.remote_addr),
    )
    db.commit()
    flash("Assinatura eletrônica registrada nesta ordem de serviço.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    db = get_db()
    equipamento_id_preselecionado = request.args.get("equipamento_id", "")
    equipamentos = db.execute(
        "SELECT id, nome, patrimonio FROM equipamentos WHERE status != 'baixado' ORDER BY nome"
    ).fetchall()
    tecnicos = db.execute(
        "SELECT id, nome FROM usuarios WHERE cargo IN ('tecnico', 'admin', 'gestor') AND ativo = 1 ORDER BY nome"
    ).fetchall()
    centros_custo = db.execute("SELECT id, nome FROM centros_custo WHERE ativo = 1 ORDER BY nome").fetchall()
    labels = db.execute("SELECT * FROM labels ORDER BY nome").fetchall()

    if request.method == "POST":
        equipamento_id = request.form.get("equipamento_id") or None
        tipo = request.form.get("tipo", "corretiva")
        prioridade = request.form.get("prioridade", "media")
        descricao_problema = request.form.get("descricao_problema", "").strip()
        solicitante = request.form.get("solicitante", "").strip()
        tecnico_id = request.form.get("tecnico_id") or None
        data_agendada = request.form.get("data_agendada") or None
        empresa_terceirizada = request.form.get("empresa_terceirizada", "").strip()
        aguardando_orcamento = 1 if request.form.get("aguardando_aprovacao_orcamento") else 0
        valor_orcamento = request.form.get("valor_orcamento", "").strip()
        centro_custo_id = request.form.get("centro_custo_id") or None
        label_id = request.form.get("label_id") or None

        if not descricao_problema:
            flash("Descreva o problema ou o serviço a ser executado.", "erro")
            return render_template(
                "ordens_servico/form.html",
                ordem=None,
                equipamentos=equipamentos,
                tecnicos=tecnicos,
                centros_custo=centros_custo,
                labels=labels,
                equipamento_id_preselecionado=equipamento_id_preselecionado,
                tipo_labels=TIPO_LABELS,
                prioridade_labels=PRIORIDADE_LABELS,
            )

        numero = gerar_numero_os(db)
        cursor = db.execute(
            """INSERT INTO ordens_servico
               (numero, equipamento_id, tipo, prioridade, descricao_problema, solicitante,
                tecnico_id, data_agendada, empresa_terceirizada, aguardando_aprovacao_orcamento,
                valor_orcamento, centro_custo_id, label_id, criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (numero, equipamento_id, tipo, prioridade, descricao_problema, solicitante,
             tecnico_id, data_agendada, empresa_terceirizada or None, aguardando_orcamento,
             float(valor_orcamento) if valor_orcamento else None, centro_custo_id, label_id, current_user.id),
        )
        ordem_id = cursor.lastrowid
        db.execute(
            """INSERT INTO ordem_servico_historico (ordem_servico_id, status_anterior, status_novo, usuario_id, observacao)
               VALUES (?, NULL, 'aberta', ?, 'Ordem de serviço criada')""",
            (ordem_id, current_user.id),
        )
        db.commit()
        flash(f"Ordem de serviço {numero} criada com sucesso.", "sucesso")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    return render_template(
        "ordens_servico/form.html",
        ordem=None,
        equipamentos=equipamentos,
        tecnicos=tecnicos,
        centros_custo=centros_custo,
        labels=labels,
        equipamento_id_preselecionado=equipamento_id_preselecionado,
        tipo_labels=TIPO_LABELS,
        prioridade_labels=PRIORIDADE_LABELS,
    )


@bp.route("/<int:ordem_id>")
@login_required
def detalhe(ordem_id):
    db = get_db()
    ordem = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome, e.patrimonio, e.id AS eq_id,
                  us.nome AS tecnico_nome, l.nome AS label_nome, l.cor AS label_cor, pl.nome AS plano_nome
           FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           LEFT JOIN usuarios us ON us.id = os.tecnico_id
           LEFT JOIN labels l ON l.id = os.label_id
           LEFT JOIN planos_manutencao pl ON pl.id = os.plano_manutencao_id
           WHERE os.id = ?""",
        (ordem_id,),
    ).fetchone()
    if ordem is None:
        flash("Ordem de serviço não encontrada.", "erro")
        return redirect(url_for("ordens_servico.lista"))

    checklist = db.execute(
        """SELECT c.*, i.descricao FROM plano_manutencao_checklist c
           JOIN procedimento_itens i ON i.id = c.procedimento_item_id
           WHERE c.ordem_servico_id = ? ORDER BY i.ordem, i.id""",
        (ordem_id,),
    ).fetchall()

    historico = db.execute(
        """SELECT h.*, u.nome AS usuario_nome FROM ordem_servico_historico h
           LEFT JOIN usuarios u ON u.id = h.usuario_id
           WHERE h.ordem_servico_id = ? ORDER BY h.criado_em DESC""",
        (ordem_id,),
    ).fetchall()

    pecas_usadas = db.execute(
        """SELECT osp.*, p.nome AS peca_nome, p.unidade_medida FROM ordem_servico_pecas osp
           JOIN pecas_estoque p ON p.id = osp.peca_id WHERE osp.ordem_servico_id = ?""",
        (ordem_id,),
    ).fetchall()

    pecas_disponiveis = db.execute("SELECT id, nome, quantidade, custo_unitario FROM pecas_estoque ORDER BY nome").fetchall()
    tecnicos = db.execute(
        "SELECT id, nome FROM usuarios WHERE cargo IN ('tecnico', 'admin', 'gestor') AND ativo = 1 ORDER BY nome"
    ).fetchall()
    anexos = db.execute(
        "SELECT * FROM anexos WHERE ordem_servico_id = ? ORDER BY criado_em DESC", (ordem_id,)
    ).fetchall()
    assinaturas = db.execute(
        """SELECT a.*, u.nome AS usuario_nome FROM assinaturas a
           LEFT JOIN usuarios u ON u.id = a.usuario_id
           WHERE a.ordem_servico_id = ? ORDER BY a.criado_em DESC""",
        (ordem_id,),
    ).fetchall()

    return render_template(
        "ordens_servico/detalhe.html",
        ordem=ordem,
        historico=historico,
        pecas_usadas=pecas_usadas,
        pecas_disponiveis=pecas_disponiveis,
        tecnicos=tecnicos,
        anexos=anexos,
        assinaturas=assinaturas,
        checklist=checklist,
        status_labels=STATUS_LABELS,
        tipo_labels=TIPO_LABELS,
        prioridade_labels=PRIORIDADE_LABELS,
    )


@bp.route("/<int:ordem_id>/atualizar-status", methods=["POST"])
@login_required
def atualizar_status(ordem_id):
    db = get_db()
    ordem = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (ordem_id,)).fetchone()
    if ordem is None:
        flash("Ordem de serviço não encontrada.", "erro")
        return redirect(url_for("ordens_servico.lista"))

    novo_status = request.form.get("status")
    observacao = request.form.get("observacao", "").strip()
    tecnico_id = request.form.get("tecnico_id") or ordem["tecnico_id"]

    if novo_status == "concluida" and ordem["plano_manutencao_id"]:
        plano = db.execute(
            "SELECT exigir_checklist FROM planos_manutencao WHERE id = ?", (ordem["plano_manutencao_id"],)
        ).fetchone()
        if plano and plano["exigir_checklist"]:
            pendentes = db.execute(
                "SELECT COUNT(*) AS c FROM plano_manutencao_checklist WHERE ordem_servico_id = ? AND concluido = 0",
                (ordem_id,),
            ).fetchone()["c"]
            if pendentes:
                flash(f"Este plano exige o checklist preenchido — faltam {pendentes} item(ns) a marcar.", "erro")
                return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    campos_extra = ""
    valores_extra = []

    if novo_status == "em_andamento" and not ordem["data_inicio"]:
        campos_extra += ", data_inicio = datetime('now','localtime')"
    if novo_status == "concluida":
        campos_extra += ", data_conclusao = datetime('now','localtime')"
        solucao = request.form.get("solucao", "").strip()
        if solucao:
            campos_extra += ", solucao = ?"
            valores_extra.append(solucao)
        tempo_parado = request.form.get("tempo_parado_horas")
        if tempo_parado:
            campos_extra += ", tempo_parado_horas = ?"
            valores_extra.append(float(tempo_parado))
        custo_mao_obra = request.form.get("custo_mao_obra")
        if custo_mao_obra:
            campos_extra += ", custo_mao_obra = ?"
            valores_extra.append(float(custo_mao_obra))

    sql = f"UPDATE ordens_servico SET status = ?, tecnico_id = ?, atualizado_em = datetime('now','localtime') {campos_extra} WHERE id = ?"
    db.execute(sql, [novo_status, tecnico_id] + valores_extra + [ordem_id])

    db.execute(
        """INSERT INTO ordem_servico_historico (ordem_servico_id, status_anterior, status_novo, usuario_id, observacao)
           VALUES (?, ?, ?, ?, ?)""",
        (ordem_id, ordem["status"], novo_status, current_user.id, observacao or None),
    )

    # Se for uma OS de preventiva/calibração concluída, atualiza as datas do equipamento.
    if novo_status == "concluida" and ordem["equipamento_id"]:
        from utils import somar_meses

        equipamento = db.execute(
            "SELECT * FROM equipamentos WHERE id = ?", (ordem["equipamento_id"],)
        ).fetchone()
        if ordem["tipo"] == "preventiva" and equipamento["periodicidade_preventiva_meses"]:
            hoje = request.form.get("data_execucao") or __import__("datetime").date.today().isoformat()
            proxima = somar_meses(hoje, equipamento["periodicidade_preventiva_meses"])
            db.execute(
                "UPDATE equipamentos SET data_ultima_preventiva = ?, data_proxima_preventiva = ? WHERE id = ?",
                (hoje, proxima, equipamento["id"]),
            )
        if ordem["tipo"] == "calibracao" and equipamento["periodicidade_calibracao_meses"]:
            hoje = request.form.get("data_execucao") or __import__("datetime").date.today().isoformat()
            proxima = somar_meses(hoje, equipamento["periodicidade_calibracao_meses"])
            db.execute(
                "UPDATE equipamentos SET data_ultima_calibracao = ?, data_proxima_calibracao = ? WHERE id = ?",
                (hoje, proxima, equipamento["id"]),
            )

    db.commit()
    flash("Status da ordem de serviço atualizado.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/<int:ordem_id>/adicionar-peca", methods=["POST"])
@login_required
def adicionar_peca(ordem_id):
    db = get_db()
    peca_id = request.form.get("peca_id")
    quantidade = float(request.form.get("quantidade", "1") or 1)

    peca = db.execute("SELECT * FROM pecas_estoque WHERE id = ?", (peca_id,)).fetchone()
    if peca is None:
        flash("Peça não encontrada.", "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    if peca["quantidade"] < quantidade:
        flash(f"Estoque insuficiente de {peca['nome']} (disponível: {peca['quantidade']}).", "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    db.execute(
        "INSERT INTO ordem_servico_pecas (ordem_servico_id, peca_id, quantidade, custo_unitario) VALUES (?,?,?,?)",
        (ordem_id, peca_id, quantidade, peca["custo_unitario"]),
    )
    db.execute("UPDATE pecas_estoque SET quantidade = quantidade - ? WHERE id = ?", (quantidade, peca_id))

    custo_total_pecas = db.execute(
        "SELECT COALESCE(SUM(quantidade * custo_unitario), 0) AS total FROM ordem_servico_pecas WHERE ordem_servico_id = ?",
        (ordem_id,),
    ).fetchone()["total"]
    db.execute("UPDATE ordens_servico SET custo_pecas = ? WHERE id = ?", (custo_total_pecas, ordem_id))

    db.commit()
    flash(f"{peca['nome']} adicionada à ordem de serviço.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))


@bp.route("/<int:ordem_id>/anexar", methods=["POST"])
@login_required
def anexar(ordem_id):
    db = get_db()
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo para enviar.", "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    try:
        nome_original, caminho = salvar_arquivo(arquivo)
    except ValueError as e:
        flash(str(e), "erro")
        return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

    db.execute(
        "INSERT INTO anexos (ordem_servico_id, nome_arquivo, caminho, tipo, enviado_por) VALUES (?,?,?,?,?)",
        (ordem_id, nome_original, caminho, "laudo", current_user.id),
    )
    db.commit()
    flash("Arquivo anexado com sucesso.", "sucesso")
    return redirect(url_for("ordens_servico.detalhe", ordem_id=ordem_id))

import hashlib
import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint("perfil", __name__, url_prefix="/perfil")


# ===================== MEU PERFIL =====================
@bp.route("/", methods=["GET", "POST"])
@login_required
def meu_perfil():
    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios WHERE id = ?", (current_user.id,)).fetchone()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        if not nome:
            flash("O nome não pode ficar em branco.", "erro")
        else:
            db.execute("UPDATE usuarios SET nome = ?, telefone = ? WHERE id = ?", (nome, telefone, current_user.id))
            db.commit()
            flash("Perfil atualizado.", "sucesso")
        return redirect(url_for("perfil.meu_perfil"))

    return render_template("perfil/meu_perfil.html", usuario=usuario)


@bp.route("/senha", methods=["POST"])
@login_required
def trocar_senha():
    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios WHERE id = ?", (current_user.id,)).fetchone()

    senha_atual = request.form.get("senha_atual", "")
    nova_senha = request.form.get("nova_senha", "")
    confirmar = request.form.get("confirmar_senha", "")

    from auth import validar_senha

    erros = validar_senha(db, nova_senha)
    if nova_senha != confirmar:
        erros.append("As senhas não coincidem.")

    if not check_password_hash(usuario["senha_hash"], senha_atual):
        flash("Senha atual incorreta.", "erro")
    elif erros:
        for erro in erros:
            flash(erro, "erro")
    else:
        db.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova_senha), current_user.id))
        db.commit()
        flash("Senha alterada com sucesso.", "sucesso")

    return redirect(url_for("perfil.meu_perfil"))


# ===================== MINHA AGENDA =====================
@bp.route("/agenda")
@login_required
def minha_agenda():
    db = get_db()
    ordens = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           WHERE os.tecnico_id = ? AND os.data_agendada IS NOT NULL
           AND os.status IN ('aberta','em_andamento','aguardando_peca')
           ORDER BY os.data_agendada""",
        (current_user.id,),
    ).fetchall()
    return render_template("perfil/minha_agenda.html", ordens=ordens)


# ===================== MINHAS TAREFAS =====================
@bp.route("/tarefas")
@login_required
def minhas_tarefas():
    db = get_db()
    ordens = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           WHERE os.tecnico_id = ? AND os.status IN ('aberta','em_andamento','aguardando_peca')
           ORDER BY CASE os.prioridade WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, os.data_abertura""",
        (current_user.id,),
    ).fetchall()
    return render_template("perfil/minhas_tarefas.html", ordens=ordens)


# ===================== AGENDA TELEFÔNICA =====================
@bp.route("/agenda-telefonica")
@login_required
def agenda_telefonica():
    db = get_db()
    usuarios = db.execute(
        """SELECT nome, telefone, email, cargo, 'Usuário do sistema' AS origem FROM usuarios
           WHERE ativo = 1 ORDER BY nome"""
    ).fetchall()
    colaboradores = db.execute(
        """SELECT nome, telefone, email, funcao AS cargo, 'Colaborador' AS origem FROM colaboradores
           WHERE ativo = 1 ORDER BY nome"""
    ).fetchall()
    contatos = sorted(list(usuarios) + list(colaboradores), key=lambda c: c["nome"])
    return render_template("perfil/agenda_telefonica.html", contatos=contatos)


# ===================== TOKENS DE ACESSO PESSOAL =====================
@bp.route("/tokens", methods=["GET", "POST"])
@login_required
def tokens():
    db = get_db()
    novo_token_gerado = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Dê um nome ao token para identificá-lo depois.", "erro")
        else:
            token_bruto = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token_bruto.encode()).hexdigest()
            db.execute(
                "INSERT INTO tokens_acesso (usuario_id, nome, token_hash, token_prefixo) VALUES (?,?,?,?)",
                (current_user.id, nome, token_hash, token_bruto[:8]),
            )
            db.commit()
            novo_token_gerado = token_bruto
            flash("Token gerado. Copie agora — ele não será mostrado novamente.", "sucesso")

    lista = db.execute(
        "SELECT * FROM tokens_acesso WHERE usuario_id = ? ORDER BY criado_em DESC", (current_user.id,)
    ).fetchall()
    return render_template("perfil/tokens.html", tokens=lista, novo_token_gerado=novo_token_gerado)


@bp.route("/tokens/<int:token_id>/revogar", methods=["POST"])
@login_required
def revogar_token(token_id):
    db = get_db()
    db.execute(
        "UPDATE tokens_acesso SET revogado = 1 WHERE id = ? AND usuario_id = ?", (token_id, current_user.id)
    )
    db.commit()
    flash("Token revogado.", "sucesso")
    return redirect(url_for("perfil.tokens"))


# ===================== EM CONSTRUÇÃO =====================
@bp.route("/trocar-empresa")
@login_required
def trocar_empresa():
    return render_template(
        "perfil/em_construcao.html",
        titulo="Trocar de Empresa",
        descricao="O GEC hoje atende uma única organização por instalação. Suporte a múltiplas empresas/contextos no mesmo login ainda não foi implementado.",
    )


@bp.route("/notificacoes", methods=["GET", "POST"])
@login_required
def notificacoes():
    db = get_db()
    prefs = db.execute("SELECT * FROM preferencias_notificacao WHERE usuario_id = ?", (current_user.id,)).fetchone()

    if request.method == "POST":
        dados = (
            1 if request.form.get("email_os_atribuida") else 0,
            1 if request.form.get("email_calibracao_vencendo") else 0,
            1 if request.form.get("email_alerta_geral") else 0,
        )
        if prefs:
            db.execute(
                "UPDATE preferencias_notificacao SET email_os_atribuida=?, email_calibracao_vencendo=?, email_alerta_geral=? WHERE usuario_id=?",
                dados + (current_user.id,),
            )
        else:
            db.execute(
                "INSERT INTO preferencias_notificacao (usuario_id, email_os_atribuida, email_calibracao_vencendo, email_alerta_geral) VALUES (?,?,?,?)",
                (current_user.id,) + dados,
            )
        db.commit()
        flash("Preferências salvas. Elas só terão efeito prático quando um servidor de e-mail (SMTP) for configurado — hoje o sistema não envia e-mails.", "aviso")
        return redirect(url_for("perfil.notificacoes"))

    return render_template("perfil/notificacoes.html", prefs=prefs)


@bp.route("/gec-sign")
@login_required
def gec_sign():
    db = get_db()
    assinaturas = db.execute(
        """SELECT a.*, os.numero AS os_numero FROM assinaturas a
           JOIN ordens_servico os ON os.id = a.ordem_servico_id
           WHERE a.usuario_id = ? ORDER BY a.criado_em DESC""",
        (current_user.id,),
    ).fetchall()
    return render_template("perfil/gec_sign.html", assinaturas=assinaturas)


@bp.route("/cursos")
@login_required
def cursos():
    return render_template(
        "perfil/em_construcao.html",
        titulo="Meus Cursos",
        descricao="Módulo de treinamentos/EAD da equipe técnica. Ainda não construído — me diga se você quer isso e como deveria funcionar.",
    )


# ===================== CHAT INTERNO =====================
@bp.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    db = get_db()
    if request.method == "POST":
        mensagem = request.form.get("mensagem", "").strip()
        if mensagem:
            db.execute("INSERT INTO mensagens_chat (usuario_id, mensagem) VALUES (?, ?)", (current_user.id, mensagem))
            db.commit()
        return redirect(url_for("perfil.chat"))

    mensagens = db.execute(
        """SELECT m.*, u.nome AS usuario_nome FROM mensagens_chat m
           LEFT JOIN usuarios u ON u.id = m.usuario_id
           ORDER BY m.criado_em DESC LIMIT 100"""
    ).fetchall()
    return render_template("perfil/chat.html", mensagens=mensagens)

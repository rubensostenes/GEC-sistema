"""Versão Firestore do módulo de cadastros — começando por Unidades
(módulo 2 da ordem descrita em MIGRACAO_FIRESTORE.md).

Reaproveita os MESMOS templates do app atual (cadastros/unidades.html,
cadastros/form_unidade.html) — Jinja aceita `obj.campo` tanto em objetos
quanto em dicts, então os documentos do Firestore (convertidos pra dict)
funcionam sem alterar nenhum template.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from auth import admin_required
from firestore_app.db_firestore import get_db

bp = Blueprint("cadastros", __name__, url_prefix="/cadastros")


def _unidade_para_dict(doc):
    dados = doc.to_dict()
    dados["id"] = doc.id
    return dados


# ===================== UNIDADES =====================
@bp.route("/unidades")
@login_required
def unidades():
    db = get_db()
    docs = db.collection("unidades").order_by("nome").stream()

    lista = []
    for doc in docs:
        unidade = _unidade_para_dict(doc)
        # Sem JOIN no Firestore: uma contagem agregada por unidade
        # (barato — Firestore tem count() nativo, não baixa os documentos).
        contagem = (
            db.collection("equipamentos")
            .where("unidade_id", "==", doc.id)
            .count()
            .get()
        )
        unidade["total_equipamentos"] = contagem[0][0].value
        lista.append(unidade)

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
        existe = db.collection("unidades").where("nome", "==", nome).limit(1).get()
        if existe:
            flash("Já existe uma unidade com este nome.", "erro")
            return render_template("cadastros/form_unidade.html", unidade=None)

        db.collection("unidades").add({"nome": nome, "endereco": endereco, "ativo": True})
        flash("Unidade cadastrada com sucesso.", "sucesso")
        return redirect(url_for("cadastros.unidades"))

    return render_template("cadastros/form_unidade.html", unidade=None)

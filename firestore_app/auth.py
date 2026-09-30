"""Versão Firestore do login (módulo 1 de MIGRACAO_FIRESTORE.md).

Mesma lógica do auth.py atual (Flask-Login + hash de senha, sem Firebase
Auth) — só troca onde os dados de usuário são lidos/gravados.
"""
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from firestore_app.db_firestore import get_db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para continuar."
login_manager.login_message_category = "aviso"

bp = Blueprint("auth", __name__, url_prefix="/auth")

CARGOS_VALIDOS = ["admin", "gestor", "tecnico", "solicitante"]
CARGO_LABELS = {
    "admin": "Administrador",
    "gestor": "Gestor",
    "tecnico": "Técnico",
    "solicitante": "Solicitante",
}


class User(UserMixin):
    def __init__(self, doc_id, dados):
        self.id = doc_id
        self.nome = dados["nome"]
        self.email = dados["email"]
        self.cargo = dados["cargo"]
        self.unidade_id = dados.get("unidade_id")
        self.ativo = dados.get("ativo", True)

    @property
    def is_admin(self):
        return self.cargo == "admin"

    @property
    def is_gestor(self):
        return self.cargo in ("admin", "gestor")

    def cargo_label(self):
        return CARGO_LABELS.get(self.cargo, self.cargo)

    @property
    def iniciais(self):
        partes = self.nome.split()
        letras = (partes[0][0] if partes else "?") + (partes[-1][0] if len(partes) > 1 else "")
        return letras.upper()


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    doc = db.collection("usuarios").document(user_id).get()
    if not doc.exists or not doc.to_dict().get("ativo", True):
        return None
    return User(doc.id, doc.to_dict())


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Apenas administradores podem acessar esta página.", "erro")
            return redirect(url_for("dashboard.index"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        db = get_db()
        resultados = db.collection("usuarios").where("email", "==", email).limit(1).get()
        doc = resultados[0] if resultados else None
        dados = doc.to_dict() if doc else None

        if doc is None or not check_password_hash(dados["senha_hash"], senha):
            db.collection("acessos_falhos").add(
                {
                    "email_tentativa": email,
                    "ip": request.remote_addr,
                    "motivo": "usuário não encontrado" if doc is None else "senha incorreta",
                }
            )
            flash("E-mail ou senha inválidos.", "erro")
            return render_template("auth/login.html")

        if not dados.get("ativo", True):
            db.collection("acessos_falhos").add(
                {"email_tentativa": email, "ip": request.remote_addr, "motivo": "usuário desativado"}
            )
            flash("Este usuário está desativado. Fale com um administrador.", "erro")
            return render_template("auth/login.html")

        db.collection("usuarios").document(doc.id).update({"ultimo_login": firestore_timestamp()})
        db.collection("log_acessos").add({"usuario_id": doc.id, "ip": request.remote_addr})

        login_user(User(doc.id, dados), remember=bool(request.form.get("lembrar")))
        flash(f"Bem-vindo(a), {dados['nome']}!", "sucesso")
        proximo = request.args.get("next")
        return redirect(proximo or url_for("dashboard.index"))

    return render_template("auth/login.html")


def firestore_timestamp():
    from firebase_admin import firestore

    return firestore.SERVER_TIMESTAMP


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("auth.login"))


def validar_senha(senha):
    # Política de senha (config_senha) ainda não migrada — usa o mínimo padrão por enquanto.
    erros = []
    if len(senha) < 6:
        erros.append("A senha deve ter ao menos 6 caracteres.")
    return erros


@bp.route("/registrar", methods=["GET", "POST"])
def registrar():
    db = get_db()
    existe_usuario = len(list(db.collection("usuarios").limit(1).get())) > 0

    if existe_usuario:
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Apenas administradores podem cadastrar novos usuários.", "erro")
            return redirect(url_for("auth.login"))

    unidades = [
        {**doc.to_dict(), "id": doc.id}
        for doc in db.collection("unidades").where("ativo", "==", True).order_by("nome").stream()
    ]
    grupos = []  # grupos_usuarios ainda não migrado

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        cargo = request.form.get("cargo", "tecnico")
        telefone = request.form.get("telefone", "").strip()
        unidade_id = request.form.get("unidade_id") or None

        erros = []
        if not nome:
            erros.append("Informe o nome completo.")
        if not email or "@" not in email:
            erros.append("Informe um e-mail válido.")
        erros += validar_senha(senha)
        if senha != confirmar_senha:
            erros.append("As senhas não coincidem.")
        if cargo not in CARGOS_VALIDOS:
            erros.append("Cargo inválido.")
        if db.collection("usuarios").where("email", "==", email).limit(1).get():
            erros.append("Já existe um usuário com este e-mail.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "auth/registrar.html", unidades=unidades, grupos=grupos, primeiro_usuario=not existe_usuario
            )

        cargo_final = "admin" if not existe_usuario else cargo

        db.collection("usuarios").add(
            {
                "nome": nome,
                "email": email,
                "senha_hash": generate_password_hash(senha),
                "cargo": cargo_final,
                "telefone": telefone,
                "unidade_id": unidade_id,
                "ativo": True,
                "criado_em": firestore_timestamp(),
            }
        )

        if not existe_usuario:
            flash("Usuário administrador criado com sucesso! Faça login.", "sucesso")
            return redirect(url_for("auth.login"))

        flash(f"Usuário {nome} cadastrado com sucesso.", "sucesso")
        return redirect(url_for("cadastros.usuarios"))

    return render_template(
        "auth/registrar.html", unidades=unidades, grupos=grupos, primeiro_usuario=not existe_usuario
    )

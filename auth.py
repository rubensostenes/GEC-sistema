from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

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
    def __init__(self, row):
        self.id = row["id"]
        self.nome = row["nome"]
        self.email = row["email"]
        self.cargo = row["cargo"]
        self.unidade_id = row["unidade_id"]
        self.ativo = row["ativo"]

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
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    if row is None or not row["ativo"]:
        return None
    return User(row)


def validar_senha(db, senha):
    """Valida a senha conforme a política definida em Configuração > Configurações de Senha."""
    config = db.execute("SELECT * FROM config_senha ORDER BY id LIMIT 1").fetchone()
    comprimento_minimo = config["comprimento_minimo"] if config else 6
    erros = []
    if len(senha) < comprimento_minimo:
        erros.append(f"A senha deve ter ao menos {comprimento_minimo} caracteres.")
    if config and config["exigir_numero"] and not any(c.isdigit() for c in senha):
        erros.append("A senha deve conter ao menos um número.")
    if config and config["exigir_maiusculo"] and not any(c.isupper() for c in senha):
        erros.append("A senha deve conter ao menos uma letra maiúscula.")
    return erros


def admin_required(view):
    from functools import wraps

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
        row = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

        if row is None or not check_password_hash(row["senha_hash"], senha):
            db.execute(
                "INSERT INTO acessos_falhos (email_tentativa, ip, motivo) VALUES (?, ?, ?)",
                (email, request.remote_addr, "usuário não encontrado" if row is None else "senha incorreta"),
            )
            db.commit()
            flash("E-mail ou senha inválidos.", "erro")
            return render_template("auth/login.html")

        if not row["ativo"]:
            db.execute(
                "INSERT INTO acessos_falhos (email_tentativa, ip, motivo) VALUES (?, ?, ?)",
                (email, request.remote_addr, "usuário desativado"),
            )
            db.commit()
            flash("Este usuário está desativado. Fale com um administrador.", "erro")
            return render_template("auth/login.html")

        db.execute(
            "UPDATE usuarios SET ultimo_login = datetime('now', 'localtime') WHERE id = ?",
            (row["id"],),
        )
        db.execute(
            "INSERT INTO log_acessos (usuario_id, ip) VALUES (?, ?)", (row["id"], request.remote_addr)
        )
        db.commit()

        login_user(User(row), remember=bool(request.form.get("lembrar")))
        flash(f"Bem-vindo(a), {row['nome']}!", "sucesso")
        proximo = request.args.get("next")
        return redirect(proximo or url_for("dashboard.index"))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("auth.login"))


@bp.route("/registrar", methods=["GET", "POST"])
def registrar():
    db = get_db()
    existe_usuario = db.execute("SELECT COUNT(*) AS c FROM usuarios").fetchone()["c"] > 0

    # Após o primeiro usuário (que vira admin automaticamente), só admin cadastra novos usuários.
    if existe_usuario:
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Apenas administradores podem cadastrar novos usuários.", "erro")
            return redirect(url_for("auth.login"))

    unidades = db.execute("SELECT * FROM unidades WHERE ativo = 1 ORDER BY nome").fetchall()
    grupos = db.execute("SELECT * FROM grupos_usuarios ORDER BY nome").fetchall()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        cargo = request.form.get("cargo", "tecnico")
        telefone = request.form.get("telefone", "").strip()
        unidade_id = request.form.get("unidade_id") or None
        grupo_id = request.form.get("grupo_id") or None

        erros = []
        if not nome:
            erros.append("Informe o nome completo.")
        if not email or "@" not in email:
            erros.append("Informe um e-mail válido.")
        erros += validar_senha(db, senha)
        if senha != confirmar_senha:
            erros.append("As senhas não coincidem.")
        if cargo not in CARGOS_VALIDOS:
            erros.append("Cargo inválido.")
        if db.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone():
            erros.append("Já existe um usuário com este e-mail.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "auth/registrar.html", unidades=unidades, grupos=grupos, primeiro_usuario=not existe_usuario
            )

        # O primeiro usuário do sistema vira administrador automaticamente.
        cargo_final = "admin" if not existe_usuario else cargo

        db.execute(
            """INSERT INTO usuarios (nome, email, senha_hash, cargo, telefone, unidade_id, grupo_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nome, email, generate_password_hash(senha), cargo_final, telefone, unidade_id, grupo_id),
        )

        if not existe_usuario:
            db.commit()
            flash("Usuário administrador criado com sucesso! Faça login.", "sucesso")
            return redirect(url_for("auth.login"))

        from configuracao import _registrar_log

        _registrar_log(db, "usuario", "criar", f"{nome} ({email})")
        db.commit()
        flash(f"Usuário {nome} cadastrado com sucesso.", "sucesso")
        return redirect(url_for("cadastros.usuarios"))

    return render_template(
        "auth/registrar.html", unidades=unidades, grupos=grupos, primeiro_usuario=not existe_usuario
    )

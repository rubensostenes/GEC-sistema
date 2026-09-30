from pathlib import Path

from flask import Flask, Response, abort

import db
from auth import CARGO_LABELS, login_manager
from config import Config


def registrar_rota_uploads(app):
    """Serve anexos gravados no banco (GEC_STORAGE_BACKEND=db) nas mesmas URLs
    de quando ficavam em disco: /static/uploads/<nome>.

    A rota é mais específica que a estática padrão do Flask, então o Werkzeug
    a escolhe automaticamente para arquivos dentro de uploads/.
    """
    MIMES = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    @app.route("/static/uploads/<nome>")
    def arquivo_do_banco(nome):
        if app.config["STORAGE_BACKEND"] != "db":
            # Modo disco (local/docker): o nome continua chegando aqui porque a
            # rota é mais específica que a estática padrão — servimos do disco.
            from flask import send_from_directory

            return send_from_directory(app.config["UPLOAD_FOLDER"], nome)
        row = db.get_db().execute(
            "SELECT nome_original, conteudo FROM arquivos_storage WHERE nome = ?", (nome,)
        ).fetchone()
        if row is None:
            abort(404)
        extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
        return Response(
            bytes(row["conteudo"]),
            mimetype=MIMES.get(extensao, "application/octet-stream"),
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["STORAGE_BACKEND"] == "fs":
        # Com backend=db (serverless) o filesystem é read-only; nada é gravado em disco.
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    # Roda sempre: cria o banco na primeira vez e garante que tabelas/colunas
    # novas do schema sejam adicionadas em bancos já existentes.
    with app.app_context():
        db.init_db(app)

    registrar_rota_uploads(app)

    login_manager.init_app(app)

    from ajuda import bp as ajuda_bp
    from ativos import bp as ativos_bp
    from auth import bp as auth_bp
    from cadastros import bp as cadastros_bp
    from consumo import bp as consumo_bp
    from dashboard import bp as dashboard_bp
    from equipamentos import bp as equipamentos_bp
    from estoque import bp as estoque_bp
    from financeiro import bp as financeiro_bp
    from configuracao import bp as configuracao_bp
    from gestao import bp as gestao_bp
    from ordens_servico import bp as ordens_servico_bp
    from perfil import bp as perfil_bp

    app.register_blueprint(ajuda_bp)
    app.register_blueprint(ativos_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cadastros_bp)
    app.register_blueprint(configuracao_bp)
    app.register_blueprint(consumo_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(equipamentos_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(gestao_bp)
    app.register_blueprint(ordens_servico_bp)
    app.register_blueprint(perfil_bp)

    @app.context_processor
    def injetar_globais():
        from flask_login import current_user

        alertas_ativos = []
        if current_user.is_authenticated:
            alertas_ativos = db.get_db().execute(
                "SELECT * FROM alertas_gerais WHERE ativo = 1 ORDER BY criado_em DESC"
            ).fetchall()
        return {
            "nome_organizacao": app.config["NOME_ORGANIZACAO"],
            "cargo_labels": CARGO_LABELS,
            "alertas_ativos": alertas_ativos,
        }

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

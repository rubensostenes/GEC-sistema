from pathlib import Path

from flask import Flask

import db
from auth import CARGO_LABELS, login_manager
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    # Roda sempre: cria o banco na primeira vez e garante que tabelas/colunas
    # novas do schema sejam adicionadas em bancos já existentes.
    with app.app_context():
        db.init_db(app)

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

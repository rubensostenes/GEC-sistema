"""App Flask standalone pra testar a migração Firestore isoladamente,
sem tocar no app.py / SQLite em uso todo dia (ver MIGRACAO_FIRESTORE.md).

Reaproveita os templates e o CSS do app principal (mesma pasta templates/ e
static/), só troca a camada de dados por trás. Roda em porta separada.

Uso:
    set GOOGLE_APPLICATION_CREDENTIALS=caminho/para/a/chave.json
    set GEC_SECRET_KEY=qualquer-coisa-para-teste
    python firestore_app/app.py
"""
import os
import sys
from pathlib import Path

from flask import Flask

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # pra importar "firestore_app.*" e achar templates/static


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("GEC_SECRET_KEY", "dev-secret-key-teste-firestore")

    from firestore_app.auth import bp as auth_bp
    from firestore_app.auth import login_manager
    from firestore_app.cadastros import bp as cadastros_bp
    from firestore_app.dashboard import bp as dashboard_bp
    from firestore_app.stubs import registrar_stubs

    login_manager.init_app(app)

    blueprints_reais = {"auth": auth_bp, "cadastros": cadastros_bp, "dashboard": dashboard_bp}
    registrar_stubs(app, blueprints_reais)  # completa endpoints que faltam nesses blueprints

    app.register_blueprint(auth_bp)
    app.register_blueprint(cadastros_bp)
    app.register_blueprint(dashboard_bp)

    @app.context_processor
    def injetar_globais():
        from auth import CARGO_LABELS

        return {
            "nome_organizacao": "Fundação Altino Ventura (Firestore — teste)",
            "cargo_labels": CARGO_LABELS,
            "alertas_ativos": [],  # módulo de alertas ainda não migrado
        }

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

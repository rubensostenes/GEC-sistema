from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from db import get_db

bp = Blueprint("dashboard", __name__, url_prefix="/")


@bp.route("/")
@login_required
def index():
    return render_template("dashboard/inicio.html")


@bp.route("/indicadores")
@login_required
def indicadores():
    db = get_db()
    hoje = date.today().isoformat()
    em_30_dias = (date.today() + timedelta(days=30)).isoformat()

    total_equipamentos = db.execute("SELECT COUNT(*) AS c FROM equipamentos WHERE status != 'baixado'").fetchone()["c"]

    os_abertas = db.execute(
        "SELECT COUNT(*) AS c FROM ordens_servico WHERE status IN ('aberta','em_andamento','aguardando_peca')"
    ).fetchone()["c"]
    os_atrasadas = db.execute(
        """SELECT COUNT(*) AS c FROM ordens_servico
           WHERE status IN ('aberta','em_andamento','aguardando_peca') AND data_agendada IS NOT NULL AND data_agendada < ?""",
        (hoje,),
    ).fetchone()["c"]

    calibracoes = db.execute(
        """SELECT id, nome, data_proxima_calibracao AS data, 'Calibração' AS tipo
           FROM equipamentos
           WHERE necessita_calibracao = 1 AND data_proxima_calibracao IS NOT NULL
           AND data_proxima_calibracao < ? AND status != 'baixado'""",
        (em_30_dias,),
    ).fetchall()
    preventivas = db.execute(
        """SELECT id, nome, data_proxima_preventiva AS data, 'Preventiva' AS tipo
           FROM equipamentos
           WHERE data_proxima_preventiva IS NOT NULL
           AND data_proxima_preventiva < ? AND status != 'baixado'""",
        (em_30_dias,),
    ).fetchall()

    vencimentos = sorted(
        [dict(v, vencida=v["data"] < hoje) for v in list(calibracoes) + list(preventivas)],
        key=lambda v: v["data"],
    )
    total_vencidas = sum(1 for v in vencimentos if v["vencida"])

    ultimas_os = db.execute(
        """SELECT os.*, e.nome AS equipamento_nome FROM ordens_servico os
           LEFT JOIN equipamentos e ON e.id = os.equipamento_id
           ORDER BY os.data_abertura DESC LIMIT 5"""
    ).fetchall()

    return render_template(
        "dashboard/indicadores.html",
        total_equipamentos=total_equipamentos,
        os_abertas=os_abertas,
        os_atrasadas=os_atrasadas,
        vencimentos=vencimentos[:6],
        total_vencidas=total_vencidas,
        ultimas_os=ultimas_os,
    )

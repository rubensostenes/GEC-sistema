"""Registra endpoints "em construção" pra tudo que o menu (templates/base.html)
referencia mas ainda não foi migrado pro Firestore.

Sem isso, `url_for(...)` no menu quebra a página inteira assim que uma rota
não existe — mesmo problema que os stubs "em_construcao.html" já resolvem no
app atual, só que aqui é durante o desenvolvimento da migração: cada módulo
sai da lista de stub conforme vai sendo implementado de verdade (ver
MIGRACAO_FIRESTORE.md pra ordem).

Lista extraída de todo `url_for('blueprint.endpoint')` usado em
templates/base.html.
"""
from flask import Blueprint, render_template
from flask_login import login_required

# blueprint -> lista de endpoints que o menu espera existir
ENDPOINTS_POR_BLUEPRINT = {
    "ajuda": ["area_cliente", "documentacao", "ideias", "manual", "sobre", "teste_velocidade"],
    "ativos": [
        "busca", "cadastros_basicos", "contadores", "custo_substituicao", "fabricantes",
        "modelos", "novo_transporte", "novos_modelos_fabricantes", "padroes_preferenciais",
        "plano_descricoes", "rastreabilidade_padroes", "reservas", "sem_data_instalacao",
        "terceiros", "transportes",
    ],
    "cadastros": ["estoque", "usuarios"],  # "unidades" já é real, não entra aqui
    "configuracao": [
        "acessos_falhos", "alertas", "config_listagem", "config_senha", "empresa", "feriados",
        "grupos_usuarios", "labels", "licencas", "log_acessos", "log_dados",
        "parametros_calibracao", "parametros_globais", "parametros_locais", "unidades_medida",
    ],
    "consumo": ["grupos", "informacoes", "metas", "relatorios", "tabelas"],
    "dashboard": ["indicadores"],  # "index" já é real
    "equipamentos": ["lista", "novo"],
    "estoque": [
        "baixas", "cadastros_basicos", "entradas", "inventarios", "pedidos", "relatorios",
        "solicitacoes", "transferencias",
    ],
    "financeiro": ["cadastros_basicos", "centros_custo", "relatorios", "resumo"],
    "gestao": [
        "agendador_relatorios", "cadastros_basicos", "colaboradores", "contratos",
        "dados_consolidados", "fornecedores", "gec_maps", "horas_trabalhadas", "manuais",
        "planos_manutencao", "procedimentos", "relatorios_gerenciais", "sensores", "setores",
        "vincular_procedimentos",
    ],
    "ordens_servico": [
        "administrar_requisicoes", "agenda_equipe", "auditoria", "cadastros_basicos",
        "certificados", "certificados_aguardando_analise", "kanban", "lista", "lista_gec",
        "manutencoes_previstas", "minhas_requisicoes", "monitor", "monitor_gec", "nova",
        "pendencias", "rapida", "servicos_externos_orcamento",
    ],
    "perfil": [
        "agenda_telefonica", "chat", "cursos", "gec_sign", "meu_perfil", "minha_agenda",
        "minhas_tarefas", "notificacoes", "tokens", "trocar_empresa",
    ],
}


def _view_em_construcao(nome_modulo):
    @login_required
    def view():
        return render_template(
            "ajuda/em_construcao.html",
            titulo=nome_modulo,
            descricao="Este módulo ainda não foi migrado para o Firestore — ver MIGRACAO_FIRESTORE.md.",
        )

    return view


def registrar_stubs(app, blueprints_reais):
    """blueprints_reais: dict {nome: objeto Blueprint} dos módulos já
    implementados de verdade (ex: {"cadastros": bp_cadastros}). Endpoints
    reais nunca são sobrescritos."""
    for nome_bp, endpoints in ENDPOINTS_POR_BLUEPRINT.items():
        bp_real = blueprints_reais.get(nome_bp)
        if bp_real is not None:
            alvo = bp_real
            ja_registrado_em_app = True
        else:
            alvo = Blueprint(nome_bp, __name__, url_prefix=f"/{nome_bp}")
            ja_registrado_em_app = False

        for endpoint in endpoints:
            alvo.add_url_rule(
                f"/_stub/{endpoint}",
                endpoint=endpoint,
                view_func=_view_em_construcao(f"{nome_bp}.{endpoint}"),
            )

        if not ja_registrado_em_app:
            app.register_blueprint(alvo)

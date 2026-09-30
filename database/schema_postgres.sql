-- GERADO AUTOMATICAMENTE a partir de schema.sql por scripts/gerar_schema_postgres.py
-- Não edite este arquivo diretamente — edite schema.sql e rode o script de novo.

-- ===================== USUÁRIOS E ACESSO =====================
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    cargo TEXT NOT NULL DEFAULT 'tecnico' CHECK (cargo IN ('admin', 'gestor', 'tecnico', 'solicitante')),
    telefone TEXT,
    unidade_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    ultimo_login TEXT
);

-- ===================== TOKENS DE ACESSO PESSOAL =====================
CREATE TABLE IF NOT EXISTS tokens_acesso (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    token_prefixo TEXT NOT NULL,
    revogado INTEGER NOT NULL DEFAULT 0,
    ultimo_uso TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== UNIDADES E SETORES =====================
CREATE TABLE IF NOT EXISTS unidades (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    endereco TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS setores (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    codigo TEXT,
    cor TEXT,
    responsavel_id INTEGER,
    eh_almoxarifado INTEGER NOT NULL DEFAULT 0,
    codigo_integracao TEXT,
    localizacao TEXT,
    contato TEXT,
    telefone TEXT,
    ramal TEXT,
    pais TEXT,
    cep TEXT,
    logradouro TEXT,
    numero TEXT,
    complemento TEXT,
    bairro TEXT,
    cidade TEXT,
    estado TEXT,
    observacao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    UNIQUE (unidade_id, nome)
);

CREATE TABLE IF NOT EXISTS setor_centro_custo (
    id SERIAL PRIMARY KEY,
    setor_id INTEGER NOT NULL,
    centro_custo_id INTEGER NOT NULL,
    percentual REAL NOT NULL DEFAULT 100,
    UNIQUE (setor_id, centro_custo_id)
);

CREATE TABLE IF NOT EXISTS setor_usuarios_liberados (
    id SERIAL PRIMARY KEY,
    setor_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    UNIQUE (setor_id, usuario_id)
);

-- ===================== EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS equipamentos (
    id SERIAL PRIMARY KEY,
    tag TEXT,
    patrimonio TEXT UNIQUE,
    nome TEXT NOT NULL,
    categoria TEXT,
    fabricante TEXT,
    modelo TEXT,
    numero_serie TEXT,
    registro_anvisa TEXT,
    unidade_id INTEGER,
    setor_id INTEGER,
    localizacao TEXT,
    criticidade TEXT NOT NULL DEFAULT 'media' CHECK (criticidade IN ('baixa', 'media', 'alta', 'critica')),
    status TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'em_manutencao', 'inativo', 'baixado', 'emprestado')),
    data_aquisicao TEXT,
    valor_aquisicao REAL,
    fornecedor TEXT,
    data_fim_garantia TEXT,
    necessita_calibracao INTEGER NOT NULL DEFAULT 0,
    periodicidade_calibracao_meses INTEGER,
    data_ultima_calibracao TEXT,
    data_proxima_calibracao TEXT,
    periodicidade_preventiva_meses INTEGER,
    data_ultima_preventiva TEXT,
    data_proxima_preventiva TEXT,
    data_instalacao TEXT,
    valor_reposicao REAL,
    de_terceiros INTEGER NOT NULL DEFAULT 0,
    proprietario_terceiro TEXT,
    eh_padrao_calibracao INTEGER NOT NULL DEFAULT 0,
    certificado_rastreabilidade TEXT,
    orgao_certificador TEXT,
    data_validade_rastreabilidade TEXT,
    foto_path TEXT,
    observacoes TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX IF NOT EXISTS idx_equipamentos_unidade ON equipamentos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_equipamentos_status ON equipamentos(status);
CREATE INDEX IF NOT EXISTS idx_equipamentos_criticidade ON equipamentos(criticidade);

-- ===================== ORDENS DE SERVIÇO =====================
CREATE TABLE IF NOT EXISTS ordens_servico (
    id SERIAL PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    equipamento_id INTEGER,
    tipo TEXT NOT NULL DEFAULT 'corretiva' CHECK (tipo IN ('corretiva', 'preventiva', 'calibracao', 'instalacao', 'inspecao', 'administrativo', 'gerencial', 'inventario', 'qualificacao', 'recebimento', 'ronda', 'seguranca_eletrica', 'transporte', 'treinamento', 'inspecao_tecnica', 'pesquisa_clinica', 'reuniao_estrategica')),
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    status TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta', 'em_andamento', 'aguardando_peca', 'concluida', 'cancelada')),
    descricao_problema TEXT NOT NULL,
    solucao TEXT,
    solicitante TEXT,
    tecnico_id INTEGER,
    empresa_terceirizada TEXT,
    data_abertura TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    data_agendada TEXT,
    data_inicio TEXT,
    data_conclusao TEXT,
    tempo_parado_horas REAL,
    custo_pecas REAL NOT NULL DEFAULT 0,
    custo_mao_obra REAL NOT NULL DEFAULT 0,
    aguardando_aprovacao_orcamento INTEGER NOT NULL DEFAULT 0,
    valor_orcamento REAL,
    centro_custo_id INTEGER,
    observacoes TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX IF NOT EXISTS idx_os_equipamento ON ordens_servico(equipamento_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON ordens_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_tipo ON ordens_servico(tipo);

-- ===================== REQUISIÇÕES DE SERVIÇO (triagem antes de virar OS) =====================
CREATE TABLE IF NOT EXISTS requisicoes_servico (
    id SERIAL PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    equipamento_id INTEGER,
    descricao_equipamento_setor TEXT,
    solicitante_nome TEXT NOT NULL,
    ocorrencia TEXT,
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'negada', 'convertida')),
    ordem_servico_id INTEGER,
    motivo_negativa TEXT,
    data_abertura TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_requisicoes_status ON requisicoes_servico(status);

-- ===================== ESTOQUE DE PEÇAS =====================
CREATE TABLE IF NOT EXISTS pecas_estoque (
    id SERIAL PRIMARY KEY,
    codigo TEXT UNIQUE,
    nome TEXT NOT NULL,
    unidade_medida TEXT DEFAULT 'un',
    quantidade REAL NOT NULL DEFAULT 0,
    quantidade_minima REAL NOT NULL DEFAULT 0,
    custo_unitario REAL DEFAULT 0,
    fornecedor TEXT,
    localizacao TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS ordem_servico_pecas (
    id SERIAL PRIMARY KEY,
    ordem_servico_id INTEGER NOT NULL,
    peca_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    custo_unitario REAL NOT NULL DEFAULT 0
);

-- ===================== ANEXOS (manuais, certificados, laudos) =====================
CREATE TABLE IF NOT EXISTS anexos (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER,
    ordem_servico_id INTEGER,
    nome_arquivo TEXT NOT NULL,
    caminho TEXT NOT NULL,
    tipo TEXT,
    revisado INTEGER NOT NULL DEFAULT 0,
    enviado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== ARMAZENAMENTO DE ARQUIVOS NO BANCO =====================
-- Usado quando GEC_STORAGE_BACKEND=db (deploy serverless, ex.: Vercel, onde o
-- filesystem é efêmero). Os caminhos continuam "uploads/<nome>", mas o conteúdo
-- fica aqui e é servido pela rota /static/uploads/<nome> do app.
CREATE TABLE IF NOT EXISTS arquivos_storage (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    nome_original TEXT,
    conteudo BYTEA NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== HISTÓRICO DE STATUS DA OS (auditoria/rastreio) =====================
CREATE TABLE IF NOT EXISTS ordem_servico_historico (
    id SERIAL PRIMARY KEY,
    ordem_servico_id INTEGER NOT NULL,
    status_anterior TEXT,
    status_novo TEXT NOT NULL,
    usuario_id INTEGER,
    observacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== FORNECEDORES =====================
CREATE TABLE IF NOT EXISTS fornecedores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cnpj TEXT,
    contato TEXT,
    telefone TEXT,
    email TEXT,
    servicos_prestados TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== CONTRATOS DE MANUTENÇÃO =====================
CREATE TABLE IF NOT EXISTS contratos_manutencao (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER,
    unidade_id INTEGER,
    equipamento_id INTEGER,
    descricao TEXT NOT NULL,
    tipo_servico TEXT,
    data_inicio TEXT,
    data_fim TEXT,
    valor REAL,
    status TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'encerrado', 'cancelado')),
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== COLABORADORES (equipe técnica e apoio) =====================
CREATE TABLE IF NOT EXISTS colaboradores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    funcao TEXT,
    unidade_id INTEGER,
    telefone TEXT,
    email TEXT,
    carga_horaria_semanal REAL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS apontamentos_horas (
    id SERIAL PRIMARY KEY,
    colaborador_id INTEGER NOT NULL,
    ordem_servico_id INTEGER,
    data TEXT NOT NULL,
    horas REAL NOT NULL,
    observacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== MANUAIS (biblioteca técnica) =====================
CREATE TABLE IF NOT EXISTS manuais (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    categoria TEXT,
    equipamento_id INTEGER,
    arquivo_path TEXT NOT NULL,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== FABRICANTES E MODELOS =====================
CREATE TABLE IF NOT EXISTS fabricantes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    site TEXT,
    contato TEXT,
    telefone TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS modelos (
    id SERIAL PRIMARY KEY,
    fabricante_id INTEGER,
    nome TEXT NOT NULL,
    categoria TEXT,
    padrao_preferencial INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== PLANO DE DESCRIÇÕES (padronização de nomenclatura) =====================
CREATE TABLE IF NOT EXISTS plano_descricoes (
    id SERIAL PRIMARY KEY,
    categoria TEXT NOT NULL UNIQUE,
    descricao_padrao TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== RESERVA DE EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS reservas_equipamento (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER NOT NULL,
    solicitante TEXT NOT NULL,
    data_inicio TEXT NOT NULL,
    data_fim TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'reservado' CHECK (status IN ('reservado', 'em_uso', 'devolvido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== TRANSPORTE DE EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS transportes_equipamento (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER NOT NULL,
    origem TEXT,
    destino TEXT NOT NULL,
    data_transporte TEXT NOT NULL,
    responsavel TEXT,
    status TEXT NOT NULL DEFAULT 'programado' CHECK (status IN ('programado', 'em_transito', 'concluido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== CONTADORES DE USO DO EQUIPAMENTO =====================
CREATE TABLE IF NOT EXISTS contadores_equipamento (
    id SERIAL PRIMARY KEY,
    equipamento_id INTEGER NOT NULL,
    tipo_contador TEXT NOT NULL,
    valor_atual REAL NOT NULL DEFAULT 0,
    unidade_medida TEXT DEFAULT 'ciclos',
    atualizado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    atualizado_por INTEGER
);

-- ===================== ESTOQUE: COMPRAS =====================
CREATE TABLE IF NOT EXISTS solicitacoes_compra (
    id SERIAL PRIMARY KEY,
    peca_id INTEGER,
    descricao TEXT NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    justificativa TEXT,
    solicitante_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'aprovada', 'rejeitada', 'comprada')),
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS pedidos_compra (
    id SERIAL PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    fornecedor_id INTEGER,
    data_pedido TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')),
    status TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'enviado', 'recebido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS pedido_compra_itens (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL,
    peca_id INTEGER,
    descricao TEXT,
    quantidade REAL NOT NULL DEFAULT 1,
    valor_unitario REAL DEFAULT 0
);

-- ===================== ESTOQUE: ENTRADAS (NOTAS FISCAIS) =====================
CREATE TABLE IF NOT EXISTS entradas_estoque (
    id SERIAL PRIMARY KEY,
    numero_nota TEXT,
    fornecedor_id INTEGER,
    pedido_id INTEGER,
    data_entrada TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')),
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS entrada_estoque_itens (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER NOT NULL,
    peca_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    valor_unitario REAL DEFAULT 0
);

-- ===================== ESTOQUE: TRANSFERÊNCIAS E BAIXAS =====================
CREATE TABLE IF NOT EXISTS almoxarifados (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    unidade_id INTEGER,
    setor_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transferencias_estoque (
    id SERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    origem_id INTEGER,
    destino_id INTEGER,
    data_transferencia TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')),
    responsavel TEXT,
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS baixas_estoque (
    id SERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    motivo TEXT NOT NULL,
    data_baixa TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')),
    responsavel_id INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== ESTOQUE: INVENTÁRIOS =====================
CREATE TABLE IF NOT EXISTS inventarios (
    id SERIAL PRIMARY KEY,
    descricao TEXT,
    data_inventario TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD')),
    status TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'fechado')),
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS inventario_itens (
    id SERIAL PRIMARY KEY,
    inventario_id INTEGER NOT NULL,
    peca_id INTEGER NOT NULL,
    quantidade_sistema REAL NOT NULL,
    quantidade_contada REAL,
    UNIQUE (inventario_id, peca_id)
);

-- ===================== FINANCEIRO: CENTROS DE CUSTO =====================
CREATE TABLE IF NOT EXISTS centros_custo (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    unidade_id INTEGER,
    tipo TEXT NOT NULL DEFAULT 'custo' CHECK (tipo IN ('custo', 'lucro')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== CONSUMO (utilidades/insumos por período) =====================
CREATE TABLE IF NOT EXISTS grupos_consumo (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS tabelas_consumo (
    id SERIAL PRIMARY KEY,
    grupo_id INTEGER,
    nome TEXT NOT NULL,
    unidade_id INTEGER,
    unidade_medida TEXT NOT NULL DEFAULT 'un',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS informacoes_consumo (
    id SERIAL PRIMARY KEY,
    tabela_id INTEGER NOT NULL,
    periodo TEXT NOT NULL,
    valor REAL NOT NULL,
    observacao TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    UNIQUE (tabela_id, periodo)
);

CREATE TABLE IF NOT EXISTS metas_consumo (
    id SERIAL PRIMARY KEY,
    tabela_id INTEGER NOT NULL,
    periodo TEXT NOT NULL,
    valor_meta REAL NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS')),
    UNIQUE (tabela_id, periodo)
);

-- ===================== CONFIGURAÇÃO: USUÁRIOS E EMPRESA =====================
CREATE TABLE IF NOT EXISTS grupos_usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS empresa (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cnpj TEXT,
    endereco TEXT,
    telefone TEXT,
    email TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== CONFIGURAÇÃO: ALERTAS =====================
CREATE TABLE IF NOT EXISTS alertas_gerais (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== CONFIGURAÇÃO: CATÁLOGOS DE APOIO =====================
CREATE TABLE IF NOT EXISTS unidades_medida (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    simbolo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feriados (
    id SERIAL PRIMARY KEY,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    unidade_id INTEGER,
    UNIQUE (data, unidade_id)
);

CREATE TABLE IF NOT EXISTS labels (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT NOT NULL DEFAULT '#2f80c4'
);

-- ===================== CONFIGURAÇÃO: PARÂMETROS =====================
CREATE TABLE IF NOT EXISTS parametros_locais (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL,
    chave TEXT NOT NULL,
    valor TEXT,
    UNIQUE (unidade_id, chave)
);

CREATE TABLE IF NOT EXISTS parametros_globais (
    id SERIAL PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    valor TEXT,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS parametros_calibracao (
    id SERIAL PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    valor TEXT,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS config_senha (
    id SERIAL PRIMARY KEY,
    comprimento_minimo INTEGER NOT NULL DEFAULT 6,
    exigir_numero INTEGER NOT NULL DEFAULT 0,
    exigir_maiusculo INTEGER NOT NULL DEFAULT 0,
    dias_expiracao INTEGER
);

CREATE TABLE IF NOT EXISTS config_listagem (
    id SERIAL PRIMARY KEY,
    itens_por_pagina INTEGER NOT NULL DEFAULT 25
);

-- ===================== CONFIGURAÇÃO: SEGURANÇA E AUDITORIA =====================
CREATE TABLE IF NOT EXISTS acessos_falhos (
    id SERIAL PRIMARY KEY,
    email_tentativa TEXT NOT NULL,
    ip TEXT,
    motivo TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS log_acessos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    ip TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS log_dados_sistema (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    entidade TEXT NOT NULL,
    acao TEXT NOT NULL,
    detalhe TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== PROCEDIMENTOS DE MANUTENÇÃO =====================
CREATE TABLE IF NOT EXISTS procedimentos_manutencao (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'preventiva' CHECK (tipo IN ('preventiva', 'calibracao', 'inspecao')),
    categoria TEXT,
    titulo_relatorio TEXT,
    procedimento_generico INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    versao TEXT NOT NULL DEFAULT '1.0',
    publicado INTEGER NOT NULL DEFAULT 0,
    data_publicacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS procedimento_blocos (
    id SERIAL PRIMARY KEY,
    procedimento_id INTEGER NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0,
    descricao TEXT NOT NULL,
    calibra_componente INTEGER NOT NULL DEFAULT 0,
    instrucoes_gerais TEXT
);

CREATE TABLE IF NOT EXISTS procedimento_itens (
    id SERIAL PRIMARY KEY,
    procedimento_id INTEGER NOT NULL,
    bloco_id INTEGER,
    ordem INTEGER NOT NULL DEFAULT 0,
    descricao TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS modelo_procedimentos (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL,
    procedimento_id INTEGER NOT NULL,
    UNIQUE (modelo_id, procedimento_id)
);

-- ===================== CHAT INTERNO =====================
CREATE TABLE IF NOT EXISTS mensagens_chat (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    mensagem TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== ASSINATURA ELETRÔNICA SIMPLES =====================
CREATE TABLE IF NOT EXISTS assinaturas (
    id SERIAL PRIMARY KEY,
    ordem_servico_id INTEGER NOT NULL,
    usuario_id INTEGER,
    nome_declarado TEXT NOT NULL,
    ip TEXT,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== SENSORES (leitura manual) =====================
CREATE TABLE IF NOT EXISTS sensores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    equipamento_id INTEGER,
    tipo_medida TEXT NOT NULL,
    unidade_medida TEXT NOT NULL DEFAULT 'un',
    valor_minimo REAL,
    valor_maximo REAL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS leituras_sensor (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL,
    valor REAL NOT NULL,
    registrado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== NOTIFICAÇÕES (preferências) =====================
CREATE TABLE IF NOT EXISTS preferencias_notificacao (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE,
    email_os_atribuida INTEGER NOT NULL DEFAULT 1,
    email_calibracao_vencendo INTEGER NOT NULL DEFAULT 1,
    email_alerta_geral INTEGER NOT NULL DEFAULT 1
);

-- ===================== AGENDADOR DE RELATÓRIOS (configuração) =====================
CREATE TABLE IF NOT EXISTS agendamentos_relatorio (
    id SERIAL PRIMARY KEY,
    relatorio TEXT NOT NULL,
    frequencia TEXT NOT NULL DEFAULT 'semanal' CHECK (frequencia IN ('diaria', 'semanal', 'mensal')),
    destinatarios TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

-- ===================== BANCO DE IDEIAS =====================
CREATE TABLE IF NOT EXISTS ideias (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER,
    titulo TEXT NOT NULL,
    descricao TEXT,
    status TEXT NOT NULL DEFAULT 'nova' CHECK (status IN ('nova', 'em_analise', 'aprovada', 'rejeitada', 'implementada')),
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS ideia_votos (
    id SERIAL PRIMARY KEY,
    ideia_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    UNIQUE (ideia_id, usuario_id)
);

-- ===================== PLANOS DE MANUTENÇÃO (modelo reutilizável) =====================
CREATE TABLE IF NOT EXISTS planos_manutencao (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    oficina TEXT NOT NULL DEFAULT 'Engenharia Clínica',
    abrangencia TEXT NOT NULL DEFAULT 'equipamentos' CHECK (abrangencia IN ('equipamentos', 'setores', 'predial')),
    categoria_equipamento TEXT,
    pausado INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    tipo_manutencao TEXT NOT NULL DEFAULT 'preventiva' CHECK (tipo_manutencao IN ('preventiva', 'calibracao', 'inspecao', 'inspecao_tecnica', 'inventario', 'seguranca_eletrica', 'qualificacao', 'pesquisa_clinica', 'reuniao_estrategica', 'ronda')),
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    responsavel_id INTEGER,
    pendencia TEXT,
    ocorrencia TEXT,
    causa TEXT,
    procedimento_id INTEGER,
    exigir_checklist INTEGER NOT NULL DEFAULT 0,
    observacao TEXT,
    fornecedor_id INTEGER,
    contrato_id INTEGER,
    abrir_os_externa INTEGER NOT NULL DEFAULT 0,
    periodicidade_meses INTEGER NOT NULL DEFAULT 12,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Recife', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS plano_manutencao_checklist (
    id SERIAL PRIMARY KEY,
    ordem_servico_id INTEGER NOT NULL,
    procedimento_item_id INTEGER NOT NULL,
    concluido INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ordem_servico_id, procedimento_item_id)
);


-- ============================================================
-- CHAVES ESTRANGEIRAS — emitidas no final porque o Postgres
-- valida a existência da tabela referenciada na criação (e o
-- schema original do SQLite depende de ordem/tem ciclos).
-- ============================================================
ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE tokens_acesso ADD CONSTRAINT fk_tokens_acesso_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
ALTER TABLE setores ADD CONSTRAINT fk_setores_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE CASCADE;
ALTER TABLE setores ADD CONSTRAINT fk_setores_responsavel_id FOREIGN KEY (responsavel_id) REFERENCES colaboradores(id) ON DELETE SET NULL;
ALTER TABLE setor_centro_custo ADD CONSTRAINT fk_setor_centro_custo_setor_id FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE;
ALTER TABLE setor_centro_custo ADD CONSTRAINT fk_setor_centro_custo_centro_custo_id FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id) ON DELETE CASCADE;
ALTER TABLE setor_usuarios_liberados ADD CONSTRAINT fk_setor_usuarios_liberados_setor_id FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE CASCADE;
ALTER TABLE setor_usuarios_liberados ADD CONSTRAINT fk_setor_usuarios_liberados_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
ALTER TABLE equipamentos ADD CONSTRAINT fk_equipamentos_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE equipamentos ADD CONSTRAINT fk_equipamentos_setor_id FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL;
ALTER TABLE equipamentos ADD CONSTRAINT fk_equipamentos_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE ordens_servico ADD CONSTRAINT fk_ordens_servico_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE SET NULL;
ALTER TABLE ordens_servico ADD CONSTRAINT fk_ordens_servico_tecnico_id FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE ordens_servico ADD CONSTRAINT fk_ordens_servico_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE requisicoes_servico ADD CONSTRAINT fk_requisicoes_servico_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE SET NULL;
ALTER TABLE requisicoes_servico ADD CONSTRAINT fk_requisicoes_servico_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE SET NULL;
ALTER TABLE ordem_servico_pecas ADD CONSTRAINT fk_ordem_servico_pecas_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE CASCADE;
ALTER TABLE ordem_servico_pecas ADD CONSTRAINT fk_ordem_servico_pecas_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE RESTRICT;
ALTER TABLE anexos ADD CONSTRAINT fk_anexos_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE;
ALTER TABLE anexos ADD CONSTRAINT fk_anexos_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE CASCADE;
ALTER TABLE anexos ADD CONSTRAINT fk_anexos_enviado_por FOREIGN KEY (enviado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE ordem_servico_historico ADD CONSTRAINT fk_ordem_servico_historico_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE CASCADE;
ALTER TABLE ordem_servico_historico ADD CONSTRAINT fk_ordem_servico_historico_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE contratos_manutencao ADD CONSTRAINT fk_contratos_manutencao_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL;
ALTER TABLE contratos_manutencao ADD CONSTRAINT fk_contratos_manutencao_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE contratos_manutencao ADD CONSTRAINT fk_contratos_manutencao_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE SET NULL;
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE apontamentos_horas ADD CONSTRAINT fk_apontamentos_horas_colaborador_id FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id) ON DELETE CASCADE;
ALTER TABLE apontamentos_horas ADD CONSTRAINT fk_apontamentos_horas_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE SET NULL;
ALTER TABLE manuais ADD CONSTRAINT fk_manuais_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE SET NULL;
ALTER TABLE manuais ADD CONSTRAINT fk_manuais_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE modelos ADD CONSTRAINT fk_modelos_fabricante_id FOREIGN KEY (fabricante_id) REFERENCES fabricantes(id) ON DELETE SET NULL;
ALTER TABLE reservas_equipamento ADD CONSTRAINT fk_reservas_equipamento_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE;
ALTER TABLE reservas_equipamento ADD CONSTRAINT fk_reservas_equipamento_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE transportes_equipamento ADD CONSTRAINT fk_transportes_equipamento_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE;
ALTER TABLE transportes_equipamento ADD CONSTRAINT fk_transportes_equipamento_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE contadores_equipamento ADD CONSTRAINT fk_contadores_equipamento_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE;
ALTER TABLE contadores_equipamento ADD CONSTRAINT fk_contadores_equipamento_atualizado_por FOREIGN KEY (atualizado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE SET NULL;
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_solicitante_id FOREIGN KEY (solicitante_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE pedidos_compra ADD CONSTRAINT fk_pedidos_compra_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL;
ALTER TABLE pedidos_compra ADD CONSTRAINT fk_pedidos_compra_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE pedido_compra_itens ADD CONSTRAINT fk_pedido_compra_itens_pedido_id FOREIGN KEY (pedido_id) REFERENCES pedidos_compra(id) ON DELETE CASCADE;
ALTER TABLE pedido_compra_itens ADD CONSTRAINT fk_pedido_compra_itens_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE SET NULL;
ALTER TABLE entradas_estoque ADD CONSTRAINT fk_entradas_estoque_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL;
ALTER TABLE entradas_estoque ADD CONSTRAINT fk_entradas_estoque_pedido_id FOREIGN KEY (pedido_id) REFERENCES pedidos_compra(id) ON DELETE SET NULL;
ALTER TABLE entradas_estoque ADD CONSTRAINT fk_entradas_estoque_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE entrada_estoque_itens ADD CONSTRAINT fk_entrada_estoque_itens_entrada_id FOREIGN KEY (entrada_id) REFERENCES entradas_estoque(id) ON DELETE CASCADE;
ALTER TABLE entrada_estoque_itens ADD CONSTRAINT fk_entrada_estoque_itens_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE RESTRICT;
ALTER TABLE almoxarifados ADD CONSTRAINT fk_almoxarifados_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE almoxarifados ADD CONSTRAINT fk_almoxarifados_setor_id FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL;
ALTER TABLE transferencias_estoque ADD CONSTRAINT fk_transferencias_estoque_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE CASCADE;
ALTER TABLE transferencias_estoque ADD CONSTRAINT fk_transferencias_estoque_origem_id FOREIGN KEY (origem_id) REFERENCES almoxarifados(id) ON DELETE SET NULL;
ALTER TABLE transferencias_estoque ADD CONSTRAINT fk_transferencias_estoque_destino_id FOREIGN KEY (destino_id) REFERENCES almoxarifados(id) ON DELETE SET NULL;
ALTER TABLE transferencias_estoque ADD CONSTRAINT fk_transferencias_estoque_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE baixas_estoque ADD CONSTRAINT fk_baixas_estoque_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE CASCADE;
ALTER TABLE baixas_estoque ADD CONSTRAINT fk_baixas_estoque_responsavel_id FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE inventarios ADD CONSTRAINT fk_inventarios_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE inventario_itens ADD CONSTRAINT fk_inventario_itens_inventario_id FOREIGN KEY (inventario_id) REFERENCES inventarios(id) ON DELETE CASCADE;
ALTER TABLE inventario_itens ADD CONSTRAINT fk_inventario_itens_peca_id FOREIGN KEY (peca_id) REFERENCES pecas_estoque(id) ON DELETE CASCADE;
ALTER TABLE centros_custo ADD CONSTRAINT fk_centros_custo_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE tabelas_consumo ADD CONSTRAINT fk_tabelas_consumo_grupo_id FOREIGN KEY (grupo_id) REFERENCES grupos_consumo(id) ON DELETE SET NULL;
ALTER TABLE tabelas_consumo ADD CONSTRAINT fk_tabelas_consumo_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE SET NULL;
ALTER TABLE informacoes_consumo ADD CONSTRAINT fk_informacoes_consumo_tabela_id FOREIGN KEY (tabela_id) REFERENCES tabelas_consumo(id) ON DELETE CASCADE;
ALTER TABLE informacoes_consumo ADD CONSTRAINT fk_informacoes_consumo_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE metas_consumo ADD CONSTRAINT fk_metas_consumo_tabela_id FOREIGN KEY (tabela_id) REFERENCES tabelas_consumo(id) ON DELETE CASCADE;
ALTER TABLE alertas_gerais ADD CONSTRAINT fk_alertas_gerais_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE feriados ADD CONSTRAINT fk_feriados_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE CASCADE;
ALTER TABLE parametros_locais ADD CONSTRAINT fk_parametros_locais_unidade_id FOREIGN KEY (unidade_id) REFERENCES unidades(id) ON DELETE CASCADE;
ALTER TABLE log_acessos ADD CONSTRAINT fk_log_acessos_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE log_dados_sistema ADD CONSTRAINT fk_log_dados_sistema_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE procedimento_blocos ADD CONSTRAINT fk_procedimento_blocos_procedimento_id FOREIGN KEY (procedimento_id) REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE;
ALTER TABLE procedimento_itens ADD CONSTRAINT fk_procedimento_itens_procedimento_id FOREIGN KEY (procedimento_id) REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE;
ALTER TABLE procedimento_itens ADD CONSTRAINT fk_procedimento_itens_bloco_id FOREIGN KEY (bloco_id) REFERENCES procedimento_blocos(id) ON DELETE CASCADE;
ALTER TABLE modelo_procedimentos ADD CONSTRAINT fk_modelo_procedimentos_modelo_id FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE CASCADE;
ALTER TABLE modelo_procedimentos ADD CONSTRAINT fk_modelo_procedimentos_procedimento_id FOREIGN KEY (procedimento_id) REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE;
ALTER TABLE mensagens_chat ADD CONSTRAINT fk_mensagens_chat_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE assinaturas ADD CONSTRAINT fk_assinaturas_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE CASCADE;
ALTER TABLE assinaturas ADD CONSTRAINT fk_assinaturas_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE sensores ADD CONSTRAINT fk_sensores_equipamento_id FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE SET NULL;
ALTER TABLE leituras_sensor ADD CONSTRAINT fk_leituras_sensor_sensor_id FOREIGN KEY (sensor_id) REFERENCES sensores(id) ON DELETE CASCADE;
ALTER TABLE leituras_sensor ADD CONSTRAINT fk_leituras_sensor_registrado_por FOREIGN KEY (registrado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE preferencias_notificacao ADD CONSTRAINT fk_preferencias_notificacao_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
ALTER TABLE agendamentos_relatorio ADD CONSTRAINT fk_agendamentos_relatorio_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE ideias ADD CONSTRAINT fk_ideias_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE ideia_votos ADD CONSTRAINT fk_ideia_votos_ideia_id FOREIGN KEY (ideia_id) REFERENCES ideias(id) ON DELETE CASCADE;
ALTER TABLE ideia_votos ADD CONSTRAINT fk_ideia_votos_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
ALTER TABLE planos_manutencao ADD CONSTRAINT fk_planos_manutencao_responsavel_id FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE planos_manutencao ADD CONSTRAINT fk_planos_manutencao_procedimento_id FOREIGN KEY (procedimento_id) REFERENCES procedimentos_manutencao(id) ON DELETE SET NULL;
ALTER TABLE planos_manutencao ADD CONSTRAINT fk_planos_manutencao_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL;
ALTER TABLE planos_manutencao ADD CONSTRAINT fk_planos_manutencao_contrato_id FOREIGN KEY (contrato_id) REFERENCES contratos_manutencao(id) ON DELETE SET NULL;
ALTER TABLE planos_manutencao ADD CONSTRAINT fk_planos_manutencao_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE plano_manutencao_checklist ADD CONSTRAINT fk_plano_manutencao_checklist_ordem_servico_id FOREIGN KEY (ordem_servico_id) REFERENCES ordens_servico(id) ON DELETE CASCADE;
ALTER TABLE plano_manutencao_checklist ADD CONSTRAINT fk_plano_manutencao_checklist_procedimento_item_id FOREIGN KEY (procedimento_item_id) REFERENCES procedimento_itens(id) ON DELETE CASCADE;
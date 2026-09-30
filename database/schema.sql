PRAGMA foreign_keys = ON;

-- ===================== USUÁRIOS E ACESSO =====================
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    cargo TEXT NOT NULL DEFAULT 'tecnico' CHECK (cargo IN ('admin', 'gestor', 'tecnico', 'solicitante')),
    telefone TEXT,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ultimo_login TEXT
);

-- ===================== TOKENS DE ACESSO PESSOAL =====================
CREATE TABLE IF NOT EXISTS tokens_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    token_prefixo TEXT NOT NULL,
    revogado INTEGER NOT NULL DEFAULT 0,
    ultimo_uso TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== UNIDADES E SETORES =====================
CREATE TABLE IF NOT EXISTS unidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    endereco TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS setores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidade_id INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    codigo TEXT,
    cor TEXT,
    responsavel_id INTEGER REFERENCES colaboradores(id) ON DELETE SET NULL,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setor_id INTEGER NOT NULL REFERENCES setores(id) ON DELETE CASCADE,
    centro_custo_id INTEGER NOT NULL REFERENCES centros_custo(id) ON DELETE CASCADE,
    percentual REAL NOT NULL DEFAULT 100,
    UNIQUE (setor_id, centro_custo_id)
);

CREATE TABLE IF NOT EXISTS setor_usuarios_liberados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setor_id INTEGER NOT NULL REFERENCES setores(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE (setor_id, usuario_id)
);

-- ===================== EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS equipamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT,
    patrimonio TEXT UNIQUE,
    nome TEXT NOT NULL,
    categoria TEXT,
    fabricante TEXT,
    modelo TEXT,
    numero_serie TEXT,
    registro_anvisa TEXT,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    setor_id INTEGER REFERENCES setores(id) ON DELETE SET NULL,
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
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_equipamentos_unidade ON equipamentos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_equipamentos_status ON equipamentos(status);
CREATE INDEX IF NOT EXISTS idx_equipamentos_criticidade ON equipamentos(criticidade);

-- ===================== ORDENS DE SERVIÇO =====================
CREATE TABLE IF NOT EXISTS ordens_servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE SET NULL,
    tipo TEXT NOT NULL DEFAULT 'corretiva' CHECK (tipo IN ('corretiva', 'preventiva', 'calibracao', 'instalacao', 'inspecao', 'administrativo', 'gerencial', 'inventario', 'qualificacao', 'recebimento', 'ronda', 'seguranca_eletrica', 'transporte', 'treinamento', 'inspecao_tecnica', 'pesquisa_clinica', 'reuniao_estrategica')),
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    status TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta', 'em_andamento', 'aguardando_peca', 'concluida', 'cancelada')),
    descricao_problema TEXT NOT NULL,
    solucao TEXT,
    solicitante TEXT,
    tecnico_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    empresa_terceirizada TEXT,
    data_abertura TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
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
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_os_equipamento ON ordens_servico(equipamento_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON ordens_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_tipo ON ordens_servico(tipo);

-- ===================== REQUISIÇÕES DE SERVIÇO (triagem antes de virar OS) =====================
CREATE TABLE IF NOT EXISTS requisicoes_servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE SET NULL,
    descricao_equipamento_setor TEXT,
    solicitante_nome TEXT NOT NULL,
    ocorrencia TEXT,
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'negada', 'convertida')),
    ordem_servico_id INTEGER REFERENCES ordens_servico(id) ON DELETE SET NULL,
    motivo_negativa TEXT,
    data_abertura TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_requisicoes_status ON requisicoes_servico(status);

-- ===================== ESTOQUE DE PEÇAS =====================
CREATE TABLE IF NOT EXISTS pecas_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,
    nome TEXT NOT NULL,
    unidade_medida TEXT DEFAULT 'un',
    quantidade REAL NOT NULL DEFAULT 0,
    quantidade_minima REAL NOT NULL DEFAULT 0,
    custo_unitario REAL DEFAULT 0,
    fornecedor TEXT,
    localizacao TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ordem_servico_pecas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_servico_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES pecas_estoque(id) ON DELETE RESTRICT,
    quantidade REAL NOT NULL DEFAULT 1,
    custo_unitario REAL NOT NULL DEFAULT 0
);

-- ===================== ANEXOS (manuais, certificados, laudos) =====================
CREATE TABLE IF NOT EXISTS anexos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
    ordem_servico_id INTEGER REFERENCES ordens_servico(id) ON DELETE CASCADE,
    nome_arquivo TEXT NOT NULL,
    caminho TEXT NOT NULL,
    tipo TEXT,
    revisado INTEGER NOT NULL DEFAULT 0,
    enviado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== ARMAZENAMENTO DE ARQUIVOS NO BANCO =====================
-- Usado quando GEC_STORAGE_BACKEND=db (deploy serverless, ex.: Vercel, onde o
-- filesystem é efêmero). Os caminhos continuam "uploads/<nome>", mas o conteúdo
-- fica aqui e é servido pela rota /static/uploads/<nome> do app.
CREATE TABLE IF NOT EXISTS arquivos_storage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    nome_original TEXT,
    conteudo BLOB NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== HISTÓRICO DE STATUS DA OS (auditoria/rastreio) =====================
CREATE TABLE IF NOT EXISTS ordem_servico_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_servico_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    status_anterior TEXT,
    status_novo TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== FORNECEDORES =====================
CREATE TABLE IF NOT EXISTS fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cnpj TEXT,
    contato TEXT,
    telefone TEXT,
    email TEXT,
    servicos_prestados TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== CONTRATOS DE MANUTENÇÃO =====================
CREATE TABLE IF NOT EXISTS contratos_manutencao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id INTEGER REFERENCES fornecedores(id) ON DELETE SET NULL,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE SET NULL,
    descricao TEXT NOT NULL,
    tipo_servico TEXT,
    data_inicio TEXT,
    data_fim TEXT,
    valor REAL,
    status TEXT NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'encerrado', 'cancelado')),
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== COLABORADORES (equipe técnica e apoio) =====================
CREATE TABLE IF NOT EXISTS colaboradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    funcao TEXT,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    telefone TEXT,
    email TEXT,
    carga_horaria_semanal REAL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS apontamentos_horas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colaborador_id INTEGER NOT NULL REFERENCES colaboradores(id) ON DELETE CASCADE,
    ordem_servico_id INTEGER REFERENCES ordens_servico(id) ON DELETE SET NULL,
    data TEXT NOT NULL,
    horas REAL NOT NULL,
    observacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== MANUAIS (biblioteca técnica) =====================
CREATE TABLE IF NOT EXISTS manuais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    categoria TEXT,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE SET NULL,
    arquivo_path TEXT NOT NULL,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== FABRICANTES E MODELOS =====================
CREATE TABLE IF NOT EXISTS fabricantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    site TEXT,
    contato TEXT,
    telefone TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS modelos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fabricante_id INTEGER REFERENCES fabricantes(id) ON DELETE SET NULL,
    nome TEXT NOT NULL,
    categoria TEXT,
    padrao_preferencial INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== PLANO DE DESCRIÇÕES (padronização de nomenclatura) =====================
CREATE TABLE IF NOT EXISTS plano_descricoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT NOT NULL UNIQUE,
    descricao_padrao TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== RESERVA DE EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS reservas_equipamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    solicitante TEXT NOT NULL,
    data_inicio TEXT NOT NULL,
    data_fim TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'reservado' CHECK (status IN ('reservado', 'em_uso', 'devolvido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== TRANSPORTE DE EQUIPAMENTOS =====================
CREATE TABLE IF NOT EXISTS transportes_equipamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    origem TEXT,
    destino TEXT NOT NULL,
    data_transporte TEXT NOT NULL,
    responsavel TEXT,
    status TEXT NOT NULL DEFAULT 'programado' CHECK (status IN ('programado', 'em_transito', 'concluido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== CONTADORES DE USO DO EQUIPAMENTO =====================
CREATE TABLE IF NOT EXISTS contadores_equipamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    tipo_contador TEXT NOT NULL,
    valor_atual REAL NOT NULL DEFAULT 0,
    unidade_medida TEXT DEFAULT 'ciclos',
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ===================== ESTOQUE: COMPRAS =====================
CREATE TABLE IF NOT EXISTS solicitacoes_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peca_id INTEGER REFERENCES pecas_estoque(id) ON DELETE SET NULL,
    descricao TEXT NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    justificativa TEXT,
    solicitante_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'aprovada', 'rejeitada', 'comprada')),
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pedidos_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    fornecedor_id INTEGER REFERENCES fornecedores(id) ON DELETE SET NULL,
    data_pedido TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    status TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'enviado', 'recebido', 'cancelado')),
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pedido_compra_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos_compra(id) ON DELETE CASCADE,
    peca_id INTEGER REFERENCES pecas_estoque(id) ON DELETE SET NULL,
    descricao TEXT,
    quantidade REAL NOT NULL DEFAULT 1,
    valor_unitario REAL DEFAULT 0
);

-- ===================== ESTOQUE: ENTRADAS (NOTAS FISCAIS) =====================
CREATE TABLE IF NOT EXISTS entradas_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_nota TEXT,
    fornecedor_id INTEGER REFERENCES fornecedores(id) ON DELETE SET NULL,
    pedido_id INTEGER REFERENCES pedidos_compra(id) ON DELETE SET NULL,
    data_entrada TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS entrada_estoque_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entrada_id INTEGER NOT NULL REFERENCES entradas_estoque(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES pecas_estoque(id) ON DELETE RESTRICT,
    quantidade REAL NOT NULL DEFAULT 1,
    valor_unitario REAL DEFAULT 0
);

-- ===================== ESTOQUE: TRANSFERÊNCIAS E BAIXAS =====================
CREATE TABLE IF NOT EXISTS almoxarifados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    setor_id INTEGER REFERENCES setores(id) ON DELETE SET NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transferencias_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peca_id INTEGER NOT NULL REFERENCES pecas_estoque(id) ON DELETE CASCADE,
    quantidade REAL NOT NULL,
    origem_id INTEGER REFERENCES almoxarifados(id) ON DELETE SET NULL,
    destino_id INTEGER REFERENCES almoxarifados(id) ON DELETE SET NULL,
    data_transferencia TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    responsavel TEXT,
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS baixas_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peca_id INTEGER NOT NULL REFERENCES pecas_estoque(id) ON DELETE CASCADE,
    quantidade REAL NOT NULL,
    motivo TEXT NOT NULL,
    data_baixa TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    responsavel_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== ESTOQUE: INVENTÁRIOS =====================
CREATE TABLE IF NOT EXISTS inventarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT,
    data_inventario TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    status TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'fechado')),
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS inventario_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventario_id INTEGER NOT NULL REFERENCES inventarios(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES pecas_estoque(id) ON DELETE CASCADE,
    quantidade_sistema REAL NOT NULL,
    quantidade_contada REAL,
    UNIQUE (inventario_id, peca_id)
);

-- ===================== FINANCEIRO: CENTROS DE CUSTO =====================
CREATE TABLE IF NOT EXISTS centros_custo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    tipo TEXT NOT NULL DEFAULT 'custo' CHECK (tipo IN ('custo', 'lucro')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== CONSUMO (utilidades/insumos por período) =====================
CREATE TABLE IF NOT EXISTS grupos_consumo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tabelas_consumo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grupo_id INTEGER REFERENCES grupos_consumo(id) ON DELETE SET NULL,
    nome TEXT NOT NULL,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    unidade_medida TEXT NOT NULL DEFAULT 'un',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS informacoes_consumo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela_id INTEGER NOT NULL REFERENCES tabelas_consumo(id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    valor REAL NOT NULL,
    observacao TEXT,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tabela_id, periodo)
);

CREATE TABLE IF NOT EXISTS metas_consumo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela_id INTEGER NOT NULL REFERENCES tabelas_consumo(id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    valor_meta REAL NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tabela_id, periodo)
);

-- ===================== CONFIGURAÇÃO: USUÁRIOS E EMPRESA =====================
CREATE TABLE IF NOT EXISTS grupos_usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cnpj TEXT,
    endereco TEXT,
    telefone TEXT,
    email TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== CONFIGURAÇÃO: ALERTAS =====================
CREATE TABLE IF NOT EXISTS alertas_gerais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== CONFIGURAÇÃO: CATÁLOGOS DE APOIO =====================
CREATE TABLE IF NOT EXISTS unidades_medida (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    simbolo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feriados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    unidade_id INTEGER REFERENCES unidades(id) ON DELETE CASCADE,
    UNIQUE (data, unidade_id)
);

CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT NOT NULL DEFAULT '#2f80c4'
);

-- ===================== CONFIGURAÇÃO: PARÂMETROS =====================
CREATE TABLE IF NOT EXISTS parametros_locais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidade_id INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    chave TEXT NOT NULL,
    valor TEXT,
    UNIQUE (unidade_id, chave)
);

CREATE TABLE IF NOT EXISTS parametros_globais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    valor TEXT,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS parametros_calibracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    valor TEXT,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS config_senha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comprimento_minimo INTEGER NOT NULL DEFAULT 6,
    exigir_numero INTEGER NOT NULL DEFAULT 0,
    exigir_maiusculo INTEGER NOT NULL DEFAULT 0,
    dias_expiracao INTEGER
);

CREATE TABLE IF NOT EXISTS config_listagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itens_por_pagina INTEGER NOT NULL DEFAULT 25
);

-- ===================== CONFIGURAÇÃO: SEGURANÇA E AUDITORIA =====================
CREATE TABLE IF NOT EXISTS acessos_falhos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_tentativa TEXT NOT NULL,
    ip TEXT,
    motivo TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS log_acessos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    ip TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS log_dados_sistema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    entidade TEXT NOT NULL,
    acao TEXT NOT NULL,
    detalhe TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== PROCEDIMENTOS DE MANUTENÇÃO =====================
CREATE TABLE IF NOT EXISTS procedimentos_manutencao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS procedimento_blocos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedimento_id INTEGER NOT NULL REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL DEFAULT 0,
    descricao TEXT NOT NULL,
    calibra_componente INTEGER NOT NULL DEFAULT 0,
    instrucoes_gerais TEXT
);

CREATE TABLE IF NOT EXISTS procedimento_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedimento_id INTEGER NOT NULL REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE,
    bloco_id INTEGER REFERENCES procedimento_blocos(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL DEFAULT 0,
    descricao TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS modelo_procedimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo_id INTEGER NOT NULL REFERENCES modelos(id) ON DELETE CASCADE,
    procedimento_id INTEGER NOT NULL REFERENCES procedimentos_manutencao(id) ON DELETE CASCADE,
    UNIQUE (modelo_id, procedimento_id)
);

-- ===================== CHAT INTERNO =====================
CREATE TABLE IF NOT EXISTS mensagens_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    mensagem TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== ASSINATURA ELETRÔNICA SIMPLES =====================
CREATE TABLE IF NOT EXISTS assinaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_servico_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    nome_declarado TEXT NOT NULL,
    ip TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== SENSORES (leitura manual) =====================
CREATE TABLE IF NOT EXISTS sensores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE SET NULL,
    tipo_medida TEXT NOT NULL,
    unidade_medida TEXT NOT NULL DEFAULT 'un',
    valor_minimo REAL,
    valor_maximo REAL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS leituras_sensor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id INTEGER NOT NULL REFERENCES sensores(id) ON DELETE CASCADE,
    valor REAL NOT NULL,
    registrado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== NOTIFICAÇÕES (preferências) =====================
CREATE TABLE IF NOT EXISTS preferencias_notificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    email_os_atribuida INTEGER NOT NULL DEFAULT 1,
    email_calibracao_vencendo INTEGER NOT NULL DEFAULT 1,
    email_alerta_geral INTEGER NOT NULL DEFAULT 1
);

-- ===================== AGENDADOR DE RELATÓRIOS (configuração) =====================
CREATE TABLE IF NOT EXISTS agendamentos_relatorio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relatorio TEXT NOT NULL,
    frequencia TEXT NOT NULL DEFAULT 'semanal' CHECK (frequencia IN ('diaria', 'semanal', 'mensal')),
    destinatarios TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ===================== BANCO DE IDEIAS =====================
CREATE TABLE IF NOT EXISTS ideias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    status TEXT NOT NULL DEFAULT 'nova' CHECK (status IN ('nova', 'em_analise', 'aprovada', 'rejeitada', 'implementada')),
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS ideia_votos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ideia_id INTEGER NOT NULL REFERENCES ideias(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE (ideia_id, usuario_id)
);

-- ===================== PLANOS DE MANUTENÇÃO (modelo reutilizável) =====================
CREATE TABLE IF NOT EXISTS planos_manutencao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    oficina TEXT NOT NULL DEFAULT 'Engenharia Clínica',
    abrangencia TEXT NOT NULL DEFAULT 'equipamentos' CHECK (abrangencia IN ('equipamentos', 'setores', 'predial')),
    categoria_equipamento TEXT,
    pausado INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    tipo_manutencao TEXT NOT NULL DEFAULT 'preventiva' CHECK (tipo_manutencao IN ('preventiva', 'calibracao', 'inspecao', 'inspecao_tecnica', 'inventario', 'seguranca_eletrica', 'qualificacao', 'pesquisa_clinica', 'reuniao_estrategica', 'ronda')),
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta', 'critica')),
    responsavel_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    pendencia TEXT,
    ocorrencia TEXT,
    causa TEXT,
    procedimento_id INTEGER REFERENCES procedimentos_manutencao(id) ON DELETE SET NULL,
    exigir_checklist INTEGER NOT NULL DEFAULT 0,
    observacao TEXT,
    fornecedor_id INTEGER REFERENCES fornecedores(id) ON DELETE SET NULL,
    contrato_id INTEGER REFERENCES contratos_manutencao(id) ON DELETE SET NULL,
    abrir_os_externa INTEGER NOT NULL DEFAULT 0,
    periodicidade_meses INTEGER NOT NULL DEFAULT 12,
    criado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS plano_manutencao_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_servico_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    procedimento_item_id INTEGER NOT NULL REFERENCES procedimento_itens(id) ON DELETE CASCADE,
    concluido INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ordem_servico_id, procedimento_item_id)
);

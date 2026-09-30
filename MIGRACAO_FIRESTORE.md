# Migração GEC: SQLite → Firestore

Documento de arquitetura da migração completa. Serve de mapa para o trabalho —
cada tabela do `database/schema.sql` (67 no total) vira uma coleção (ou
subcoleção) do Firestore, com anotação de como cada JOIN que existia em SQL
vai ser resolvido sem JOIN.

**Status**: desenho concluído. Implementação em andamento, módulo por módulo,
em cima de código novo — o app Flask/SQLite atual continua rodando sem
alteração até a virada final.

## Princípios gerais

1. **IDs**: os documentos do Firestore usam o mesmo `id` inteiro do SQLite,
   como string (ex: `equipamentos/42`). Isso evita ter que remapear toda
   referência (`equipamento_id`, `setor_id` etc.) durante a migração de dados
   — quem hoje é `equipamento_id = 42` continua apontando pro documento `42`.
2. **Referência simples**: campos tipo `unidade_id`, `setor_id`,
   `tecnico_id` continuam existindo como string (o id do documento
   referenciado). O Firestore não valida FK — a validação de
   existência/integridade que o SQLite fazia automaticamente passa a ser
   responsabilidade do código Python em cada rota.
3. **Denormalização para leitura**: toda tela que hoje faz
   `SELECT ... JOIN` só pra mostrar um nome (ex: nome do equipamento na lista
   de OS) passa a guardar esse nome copiado no próprio documento
   (`equipamento_nome`) no momento da escrita. Custo: se o nome do
   equipamento mudar, as OS antigas mantêm o nome antigo até serem
   reabertas/salvas — aceitável pro GEC, que é basicamente "append-only" em
   histórico.
4. **Números sequenciais** (`numero` de OS, pedidos, requisições): Firestore
   não tem AUTOINCREMENT. Uso um documento contador
   (`contadores/{tipo}`) com transação atômica (`increment`) pra gerar o
   próximo número sem colisão.
5. **Tabelas de associação N:N** (`setor_centro_custo`,
   `modelo_procedimentos`, `ideia_votos`...) viram **subcoleções** do
   documento "dono" em vez de coleção own com duas FKs.
6. **Índices compostos**: toda query que hoje faz `WHERE x = ? ORDER BY y`
   em mais de um campo (bem comum no GEC) precisa de um índice composto
   criado manualmente no console do Firestore — vou listar quais no rodapé
   de cada módulo conforme for implementando.

---

## Mapeamento por módulo

### 1. Usuários e acesso
| SQLite | Firestore |
|---|---|
| `usuarios` | coleção `usuarios` (doc id = id antigo) |
| `tokens_acesso` | subcoleção `usuarios/{id}/tokens` |

Login continua pelo sistema (Flask-Login + hash de senha), Firestore é só
onde os dados moram — **sem Firebase Auth**, como já combinado.

### 2. Unidades e setores
| SQLite | Firestore |
|---|---|
| `unidades` | coleção `unidades` |
| `setores` | coleção `setores`, com `unidade_nome` e `responsavel_nome` denormalizados |
| `setor_centro_custo` | subcoleção `setores/{id}/centros_custo` |
| `setor_usuarios_liberados` | subcoleção `setores/{id}/usuarios_liberados` |

Esse é o formulário mais "join-pesado" do sistema (Setor cruza Unidade,
Colaboradores, Centro de Custo e Usuários). Vira 1 leitura do setor + 2
leituras de subcoleção (em vez de 4 JOINs) — mais chamadas, mas cada uma
simples.

### 3. Equipamentos
| SQLite | Firestore |
|---|---|
| `equipamentos` | coleção `equipamentos`, com `unidade_nome` e `setor_nome` denormalizados |

Tabela grande (2.508 linhas reais) mas sem sub-relações — migração direta.

### 4. Ordens de Serviço
| SQLite | Firestore |
|---|---|
| `ordens_servico` | coleção `ordens_servico`, com `equipamento_nome`, `tecnico_nome`, `centro_custo_nome`, `label_nome` denormalizados |
| `requisicoes_servico` | coleção `requisicoes` |
| `ordem_servico_pecas` | subcoleção `ordens_servico/{id}/pecas` |
| `anexos` | subcoleção `ordens_servico/{id}/anexos` (ou `equipamentos/{id}/anexos`, conforme o dono) |
| `ordem_servico_historico` | subcoleção `ordens_servico/{id}/historico` |
| `assinaturas` | subcoleção `ordens_servico/{id}/assinaturas` |
| `plano_manutencao_checklist` | subcoleção `ordens_servico/{id}/checklist` |

Maior módulo do sistema (9.810 OS reais) e o mais lido/escrito no dia a dia
— vai ser o último a migrar, depois de validar o padrão nos módulos
menores.

### 5. Estoque
| SQLite | Firestore |
|---|---|
| `pecas_estoque` | coleção `pecas` |
| `solicitacoes_compra` | coleção `solicitacoes_compra` |
| `pedidos_compra` + `pedido_compra_itens` | coleção `pedidos_compra`, itens como subcoleção `pedidos_compra/{id}/itens` |
| `entradas_estoque` + `entrada_estoque_itens` | coleção `entradas_estoque`, itens como subcoleção |
| `almoxarifados` | coleção `almoxarifados` |
| `transferencias_estoque` | coleção `transferencias_estoque` |
| `baixas_estoque` | coleção `baixas_estoque` |
| `inventarios` + `inventario_itens` | coleção `inventarios`, itens como subcoleção `inventarios/{id}/itens` |

Atenção especial: dar baixa/entrada em peça precisa atualizar
`pecas/{id}.quantidade` — isso deixa de ser uma transação SQL automática e
passa a ser uma **transação explícita do Firestore** (`runTransaction`) pra
não perder atualização concorrente.

### 6. Fornecedores, contratos, colaboradores
| SQLite | Firestore |
|---|---|
| `fornecedores` | coleção `fornecedores` |
| `contratos_manutencao` | coleção `contratos`, com `fornecedor_nome` denormalizado |
| `colaboradores` | coleção `colaboradores` |
| `apontamentos_horas` | subcoleção `colaboradores/{id}/apontamentos` |

### 7. Manuais, fabricantes, modelos
| SQLite | Firestore |
|---|---|
| `manuais` | coleção `manuais` |
| `fabricantes` | coleção `fabricantes` |
| `modelos` | coleção `modelos`, com `fabricante_nome` denormalizado |
| `plano_descricoes` | coleção `plano_descricoes` |
| `modelo_procedimentos` | subcoleção `modelos/{id}/procedimentos` |

### 8. Reserva, transporte e contadores de equipamento
| SQLite | Firestore |
|---|---|
| `reservas_equipamento` | subcoleção `equipamentos/{id}/reservas` |
| `transportes_equipamento` | subcoleção `equipamentos/{id}/transportes` |
| `contadores_equipamento` | subcoleção `equipamentos/{id}/contadores` |

### 9. Financeiro e consumo
| SQLite | Firestore |
|---|---|
| `centros_custo` | coleção `centros_custo` |
| `grupos_consumo` | coleção `grupos_consumo` |
| `tabelas_consumo` | coleção `tabelas_consumo` |
| `informacoes_consumo` | subcoleção `tabelas_consumo/{id}/informacoes` |
| `metas_consumo` | subcoleção `tabelas_consumo/{id}/metas` |

### 10. Configuração
| SQLite | Firestore |
|---|---|
| `grupos_usuarios` | coleção `grupos_usuarios` |
| `empresa` | documento único `configuracao/empresa` |
| `alertas_gerais` | coleção `alertas_gerais` |
| `unidades_medida`, `feriados`, `labels` | coleções próprias |
| `parametros_locais` | subcoleção `unidades/{id}/parametros` |
| `parametros_globais`, `parametros_calibracao` | coleções próprias (chave/valor) |
| `config_senha`, `config_listagem` | documentos únicos `configuracao/senha`, `configuracao/listagem` |
| `acessos_falhos`, `log_acessos`, `log_dados_sistema` | coleções próprias (grandes, só append — boas candidatas a TTL automático do Firestore pra não crescer pra sempre) |

### 11. Procedimentos e planos de manutenção
| SQLite | Firestore |
|---|---|
| `procedimentos_manutencao` | coleção `procedimentos` |
| `procedimento_blocos` | subcoleção `procedimentos/{id}/blocos` |
| `procedimento_itens` | subcoleção `procedimentos/{id}/itens` (com `bloco_id` apontando pro doc do bloco) |
| `planos_manutencao` | coleção `planos_manutencao`, com nomes denormalizados (procedimento, fornecedor, contrato, responsável) |

### 12. Chat, sensores, notificações, relatórios, ideias
| SQLite | Firestore |
|---|---|
| `mensagens_chat` | coleção `mensagens_chat` |
| `sensores` | coleção `sensores` |
| `leituras_sensor` | subcoleção `sensores/{id}/leituras` |
| `preferencias_notificacao` | subcoleção `usuarios/{id}/preferencias` (doc único `notificacao`) |
| `agendamentos_relatorio` | coleção `agendamentos_relatorio` |
| `ideias` | coleção `ideias` |
| `ideia_votos` | subcoleção `ideias/{id}/votos` |

---

## Ordem de implementação

1. Camada de acesso ao Firestore (`db_firestore.py`) — equivalente ao
   `get_db()` atual, mas devolvendo o client do Firestore.
2. Módulos sem relacionamento (cadastros simples): Unidades, Fornecedores,
   Fabricantes, Colaboradores, Labels, Unidades de Medida.
3. Módulos com denormalização simples (1 nível): Equipamentos, Setores,
   Modelos, Contratos.
4. Módulos com subcoleção: Estoque (pedidos/entradas/inventários),
   Procedimentos.
5. Ordens de Serviço + Planos de Manutenção (o núcleo do sistema,
   migrado por último, com mais tempo de teste antes da virada).
6. Configuração, logs, chat, ideias (telas administrativas, baixo risco).
7. Corte final: trocar o `app.py` pra usar `db_firestore.py`, rodar a
   migração de dados completa (script equivalente ao
   `scripts/migrar_sqlite_para_postgres.py`, mas escrevendo no Firestore),
   validar, e só então essa vira a versão em uso.

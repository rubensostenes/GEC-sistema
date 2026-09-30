# GEC — Gestão de Engenharia Clínica

Sistema local de **engenharia clínica, assistência técnica, manutenção e infraestrutura hospitalar**, feito reunindo o que há de melhor no [Neovero](https://www.neovero.com/) e no [Arkmeds](https://arkmeds.com/en/):

- Do **Neovero**: ordens de serviço com fluxo de status, planos de recorrência de preventiva/calibração vinculados ao equipamento, estoque de peças integrado às OS, dashboards operacionais por unidade.
- Do **Arkmeds**: classificação de **criticidade/risco** do equipamento, foco em compliance (registro ANVISA, calibração com vencimento rastreado), anexos de laudos/certificados por equipamento e por OS, cadastro multiunidade/multisetor.

Por enquanto roda **100% local** neste computador (Flask + SQLite, sem necessidade de internet depois de instalado).

## Como iniciar

Dê duplo clique em [iniciar.bat](iniciar.bat), ou pelo terminal:

```bash
pip install -r requirements.txt
python app.py
```

Depois acesse **http://localhost:5000** no navegador.

No primeiro acesso, a tela pedirá para criar o **usuário administrador** — esse primeiro cadastro vira admin automaticamente. Os próximos usuários (técnicos, gestores, solicitantes) só podem ser cadastrados por um administrador, em **Usuários → Novo Usuário**.

## Módulos

- **Usuários**: login, cargos (Administrador, Gestor, Técnico, Solicitante), ativar/desativar, redefinir senha — tudo pelo admin.
- **Unidades / Setores**: cadastro das unidades (ex: Iputinga, Boa Vista, Jaboatão...) e dos setores/polos dentro de cada uma.
- **Equipamentos**: ficha técnica completa (fabricante, modelo, série, registro ANVISA, patrimônio), localização, criticidade, status, aquisição/garantia, foto e anexos (manual, certificado, nota fiscal). Datas de calibração e preventiva são calculadas automaticamente a partir da periodicidade.
- **Ordens de Serviço**: corretiva, preventiva, calibração, instalação ou inspeção. Fluxo de status (aberta → em andamento → aguardando peça → concluída/cancelada) com histórico auditável, técnico responsável, tempo parado (para MTTR), custos de peça/mão de obra e anexos. Ao concluir uma OS de preventiva ou calibração, a próxima data do equipamento é recalculada automaticamente.
- **Estoque de peças**: quantidade, quantidade mínima (alerta), custo unitário; peças usadas em uma OS baixam do estoque automaticamente.
- **Painel (Dashboard)**: equipamentos ativos, OS abertas/atrasadas/concluídas no mês, MTTR médio, calibrações e preventivas vencidas ou a vencer nos próximos 30 dias, distribuição por unidade e por criticidade.

## Estrutura do projeto

```
gec-sistema/
  app.py                 # ponto de entrada / registro dos módulos
  config.py               # configurações (segredo, caminhos)
  db.py                    # conexão SQLite
  auth.py                  # login, cadastro de usuário, cargos
  cadastros.py              # unidades, setores, usuários, estoque
  equipamentos.py            # CRUD de equipamentos e anexos
  ordens_servico.py           # CRUD de OS, status, peças, anexos
  dashboard.py                 # KPIs do painel
  utils.py                      # upload de arquivo, cálculo de datas, numeração de OS
  database/schema.sql            # estrutura do banco (SQLite)
  templates/, static/             # HTML (Jinja2) e CSS
```

O banco de dados fica em `database/gec.db` (criado automaticamente no primeiro uso). Os arquivos anexados (fotos, manuais, laudos) ficam em `static/uploads/`.

## Próximos passos possíveis

- Exportar relatórios em Excel/PDF (equipamentos, OS, calibrações vencidas).
- Checklist de preventiva por tipo de equipamento.
- Acesso multiusuário pela rede local (hoje limitado a este computador — basta trocar `127.0.0.1` por `0.0.0.0` em [app.py](app.py) quando quiser liberar na rede da unidade).
- Importar o inventário existente (`Inventario_Equipamentos_FAV_2026.xlsx`) direto para o cadastro de equipamentos.

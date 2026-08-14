# Registros — Digitalização de planilhas de qualidade

Sistema web para digitalizar o preenchimento de planilhas/formulários
de controle de qualidade numa indústria de alimentos (carnes).
Pensado para uso em tablets/celulares no chão de fábrica (tela de
registro) e em computador para acompanhamento (painel).

O sistema suporta **múltiplos tipos de registro** (ex.: Temperatura
de Processo, e outros que forem adicionados depois) — uma tela
inicial deixa o usuário escolher qual planilha quer preencher. Veja
["Arquitetura: tipos de registro"](#arquitetura-tipos-de-registro)
para como adicionar um novo tipo.

## Stack

- **Backend:** Python + Flask
- **Banco de dados:** SQLite (arquivo único, uma tabela por tipo de registro)
- **Frontend:** HTML + Bootstrap 5 (botões grandes, poucos campos)
- **Gráficos:** Chart.js
- **Exportação:** Excel (.xlsx) via openpyxl
- **Deploy:** preparado para Render ou Railway

## Regras de negócio — Temperatura de Processo

| Etapa | Limite (conforme até) |
|---|---|
| Moídas | 4°C |
| Aparas, Bifes, Temperados, Embalagem, Selagem | 7°C |

Registros acima do limite mostram **"⚠️ Fora do padrão"** na hora, mas
são salvos normalmente — o sistema nunca bloqueia o registro, apenas
avisa. (Cada tipo de registro define suas próprias regras — as de
outros tipos ficam documentadas junto do respectivo tipo, como abaixo.)

## Regras de negócio — Temperatura de Setor/Câmara

17 setores/câmaras fixos, cada um com seu próprio limite máximo
(conforme quando a temperatura registrada é `<=` o limite — vários são
negativos, para câmaras e túneis de congelamento):

| Setor/Câmara | Limite (conforme até) |
|---|---|
| Câmara 1 - Estoque de congelados | -18°C |
| Câmara 2 - Estoque de congelados | -18°C |
| Setor de expedição | 16°C |
| Câmara 3 - Estoque de resfriados | 4°C |
| Túnel de congelamento 3 | -25°C |
| Setor de selagem | 16°C |
| Túnel de congelamento 2 - Giro freezer | -25°C |
| Setor de embalagem primária | 16°C |
| Setor de industrializados | 10°C |
| Câmara de industrializados | 4°C |
| Câmara de retalhos 2 | 4°C |
| Setor de carne moída | 10°C |
| Câmara de retalhos 1 | 4°C |
| Câmara de carcaças | 4°C |
| Setor de cortes | 16°C |
| Túnel de congelamento 4 - Serra | -25°C |
| Setor de temperados | 16°C |

Mesma regra de "aviso mas não bloqueia" da Temperatura de Processo.
Os limites são fixos no código
(`app/tipos/temperatura_setor/models.py`), não editáveis pela tela.

## Regras de negócio — PAC 03-A - Água de Abastecimento (Cloro e pH)

Dois valores independentes, cada um com sua própria faixa de
conformidade:

| Medida | Faixa conforme |
|---|---|
| pH | 6,0 a 9,0 |
| Cloro | 0,2 a 5,0 ppm |

Se qualquer um dos dois estiver fora da faixa, o alerta indica **qual**
(pH, Cloro, ou os dois) — mesma regra de "aviso mas não bloqueia" dos
outros tipos. O "ponto de coleta" é selecionado por botões, entre 9
pontos fixos (mesmo padrão de etapa/setor dos outros tipos) — na
prática é monitorado 1 ponto por dia, em rodízio entre eles. Limites
fixos em `app/tipos/agua_abastecimento/models.py`.

## Regras de negócio — PAC 04-C - Temperatura dos Produtos na Produção

O limite depende da **categoria** escolhida, não é fixo por produto:

| Categoria | Limite (conforme até) |
|---|---|
| Corte | 7°C |
| Carne Moída | 4°C |

"Local" (Produto em Processo / Produto na Câmara de Retalhos) é só
descritivo, não afeta a conformidade. "Produto" é texto livre (nome
específico, ex.: "Bife", "Isca") — sem limite de quantos registros por
dia. Limites fixos em `app/tipos/temp_produto/models.py`.

## Regras de negócio — PAC 04-D - Temperatura dos Produtos nas Câmaras de Expedição

O limite depende da combinação **local + categoria** (aqui sim, ao
contrário do PAC 04-C, o local também importa):

| Local | Corte | Carne Moída |
|---|---|---|
| Câmara de Congelado 1 | -12°C | -18°C |
| Câmara de Congelado 2 | -12°C | -18°C |
| Câmara de Resfriados | 7°C | 4°C |

| Local (sem categoria) | Limite |
|---|---|
| Matéria Prima - Quebra de Gelo | -8°C |

"Matéria Prima - Quebra de Gelo" é o único local sem o conceito de
categoria — a tela de registro esconde esse campo dinamicamente
quando esse local é escolhido (e o backend ignora/zera qualquer valor
de categoria enviado para ele, por segurança). Limites fixos em
`app/tipos/temp_expedicao/models.py`.

## Regras de negócio — PAC 06-D - Monitoramento de Peso (Produto Embalado)

Diferente dos demais tipos, este registro é **relacional**: um
registro de avaliação do produto (`registros_peso_produto`) tem
várias pesagens individuais associadas (`pesagens_individuais`), em
quantidade variável — não há um número fixo de pesagens por produto.

- Para cada produto avaliado, informa-se o **peso líquido nominal** e
  o **peso da embalagem**. A soma dos dois é o **padrão mínimo**
  (`peso_minimo`) que cada pesagem individual precisa atingir.
- Cada pesagem é **conforme** quando `peso_medido >= peso_minimo`
  (igual ao padrão mínimo conta como conforme). Cada pesagem **não
  conforme (NC)** é a que ficar abaixo do padrão.
- O sistema calcula automaticamente, por registro: total de
  pesagens, total de NCs e percentual de conformidade.
- Na tela de registro, as pesagens são acumuladas no navegador (uma a
  uma, com lista visual verde/vermelho e resumo ao vivo) e só são
  enviadas ao servidor junto com o registro do produto, em um único
  envio, ao clicar em "Finalizar registro do produto". Não é possível
  finalizar sem pelo menos uma pesagem lançada.
- O registro é salvo mesmo havendo pesagens fora do padrão (mesma
  filosofia dos demais tipos: registrar sempre, sinalizar o desvio).
- Modelo de dados e regras em `app/tipos/peso_produto/models.py`.

## Regras de negócio — PAC 06-E - Monitoramento de Gramatura de Bifes e Cubos

Mesma estrutura relacional do PAC 06-D (um registro de avaliação do
produto, tabela `registros_gramatura`, com várias pesagens
individuais associadas, tabela `pesagens_individuais_gramatura`, em
quantidade variável), mas **sem embalagem**: aqui são pesados
bifes/cubos soltos, comparados direto com uma **faixa de gramatura**
(mínima e máxima) — sem margem de tolerância além da própria faixa.

- Para cada produto avaliado, informa-se a **gramatura mínima** e a
  **gramatura máxima** aceitas (ex.: 80 a 100, ou 140 a 160), além do
  **operador** (quem produziu) e do **responsável** (quem
  registrou/aferiu) — dois campos de pessoa distintos, diferente dos
  demais tipos que só têm responsável.
- Cada pesagem é **conforme** quando
  `gramatura_minima <= peso_medido <= gramatura_maxima`. Cada pesagem
  **não conforme (NC)** é qualquer valor fora dessa faixa — tanto
  abaixo do mínimo quanto acima do máximo.
- O sistema calcula automaticamente, por registro: total de
  pesagens, total de NCs e percentual de conformidade.
- Tela de registro e comportamento de acumular pesagens no navegador
  antes de um único envio final são idênticos ao PAC 06-D — ver seção
  acima.
- O registro é salvo mesmo havendo pesagens fora do padrão.
- Modelo de dados e regras em `app/tipos/gramatura/models.py`.

## Regras de negócio — PAC 11 - Monitoramento dos PSO's (Procedimentos Sanitários Operacionais)

Bem mais simples que os demais: um checklist diário com 7 PSOs
fixos, cada um avaliado só como Conforme (C) ou Não Conforme (NC) —
sem número, sem observação. Um checklist salvo gera **7 linhas** na
tabela `registros_pso` (uma por PSO), todas com a mesma data e o
mesmo responsável (o "Monitor" do dia).

- Lista fixa dos 7 PSOs, em `app/tipos/pso/models.py`: PSO 1 a PSO 6
  e PSO 8 — **não existe PSO 7** nesta lista (numeração do
  procedimento original, mantida como está).
- Não há limite numérico nem cálculo: o status de cada PSO é
  informado diretamente pelo usuário (C ou NC), não derivado de uma
  medição.
- Um checklist pode ser enviado mais de uma vez no mesmo dia (ex.:
  correção) — assim como os demais tipos, o sistema sempre registra,
  nunca bloqueia ou sobrescreve o registro anterior. Na exportação em
  matriz (ver abaixo), quando há mais de um registro do mesmo PSO no
  mesmo dia, o mais recente é o que aparece na célula.
- Diferente de todos os outros tipos, este não tem campo de
  `horario` — só `data` (é um checklist diário, não uma medição
  pontual ao longo do dia).

## Regras de negócio — PAC 17 - Monitoramento de Integridade de Componentes de Máquinas

Unifica 3 planilhas antigas (PAC 17-A, 17-C e 17-G) que avaliam o
mesmo risco — agulhas/lâminas quebradas ou com partes faltantes,
risco de contaminação física do produto — em 3 equipamentos
diferentes. Um registro é uma checagem (equipamento + momento),
avaliada só como C (conforme) ou NC (não conforme), como no PAC 11.

- Os 3 equipamentos, seus componentes e momentos de checagem são
  fixos em `EQUIPAMENTOS_INFO` (`app/tipos/integridade_componente/models.py`):

  | Equipamento | Componente | Momentos |
  |---|---|---|
  | Agulhas Tenderizadora | Agulhas | Início, Final |
  | Máquina de Cubos e Iscas | Lâminas de Corte | Início, Troca de Lâminas, Final |
  | Agulhas Injetora | Agulhas | Início, Final |

  "Troca de Lâminas" só existe pra Máquina de Cubos e Iscas — a tela
  de registro esconde essa opção de momento dinamicamente quando
  outro equipamento é escolhido (e o backend rejeita a combinação
  inválida, por segurança).
- Diferente de todos os outros tipos, o `horario` **não** é
  preenchido automaticamente — o usuário digita, porque a checagem
  pode ser registrada depois de ter acontecido (ex.: anotada em
  papel e digitada mais tarde). Só a `data` é automática.
- **Verificação RT**: uma segunda tabela independente
  (`verificacoes_rt`), sem relação com os registros de integridade e
  sem conceito de conformidade — só guarda equipamento + data/hora
  automática. Existe uma tela dedicada e rápida
  (`/integridade_componente/verificacao-rt`, com um atalho fixo "⚡
  Verificação RT" na barra de navegação, visível em qualquer tela do
  sistema) onde um toque no botão do equipamento já salva, sem
  formulário. Serve pra conferências extras do RT ao longo do dia,
  à parte do checklist formal de integridade.
- Modelo de dados e regras em `app/tipos/integridade_componente/models.py`.

## Regras de negócio — PAC 08-E - Monitoramento da Ventilação

O primeiro tipo **semanal** do sistema (`categoria="semanal"` — ver
"Navegação por categoria" abaixo). Checklist com 22 setores fixos,
cada um avaliado em conjunto quanto a 4 critérios (ausência de
condensação, odores, presença de gelo, contra-fluxo de ar) e
resumido num único status geral: C (conforme) ou NC (não conforme) —
o formulário não distingue qual dos 4 critérios falhou, só se o
setor está conforme como um todo. Uma checagem salva gera **22
linhas** na tabela `registros_ventilacao` (uma por setor), todas com
a mesma data e responsável.

- Os 22 setores são fixos em `SETORES_POR_GRUPO`
  (`app/tipos/ventilacao/models.py`), divididos em 2 grupos — a mesma
  divisão da planilha em papel original:

  | Grupo | Setores |
  |---|---|
  | Setor Produção | 14: Selagem, Túnel de congelamento 3, Embalagem primária, Setor de carne moída, Sala de lavação de caixas, Depósito de caixas limpas, Sala de esterilização de facas, Câmara de matéria-prima (carcaças), Sala de cortes, Túnel de congelamento 4, Setor de temperados, Barreira Sanitária Principal, Depósito de condimentos (almoxarifado), Depósito de embalagens primárias (almoxarifado) |
  | Setor Embalagem Secundária e Expedição | 8: Barreira Sanitária Expedição, Câmara de congelados 1, Câmara de congelados 2, Abertura de caixas de papelão, Expedição, Câmara de resfriados, Depósito de embalagens secundárias, Embalagem Secundária |

- Diferente da maioria dos outros tipos, `data` **não** tem valor
  automático — é semanal, então o usuário escolhe a data da checagem
  no formulário (não é sempre "hoje"). Não há campo de `horario`,
  como no PAC 11.
- Assim como o PAC 11, não há limite numérico nem cálculo: o status é
  informado diretamente pelo usuário, e um checklist pode ser
  reenviado no mesmo dia (correção) sem bloquear ou sobrescrever o
  anterior.
- O painel (`/dashboard/ventilacao`) filtra por setor (dropdown
  agrupado pelos mesmos 2 grupos) e mostra NCs ao longo do tempo,
  igual ao filtro por PSO do PAC 11; a legenda do gráfico se esconde
  sozinha quando mais de 8 setores aparecem juntos (evita poluir o
  gráfico com até 22 linhas).
- Exportação em Excel replica o formato de matriz original: setores
  nas linhas (sempre os 22, agrupados pelas mesmas 2 seções, cada
  grupo com sua própria linha de cabeçalho destacada em azul), datas
  do período nas colunas, C/NC em cada célula (NC em vermelho).
- Modelo de dados e regras em `app/tipos/ventilacao/models.py`.

## Regras de negócio — PAC 08-G - Aferição das Balanças

O segundo tipo semanal (`categoria="semanal"`), e o primeiro a
depender de uma **tabela mestre** — o cadastro fixo das 20 balanças
da fábrica (tabela `balancas`), separado da tabela de leituras
(`registros_afericao_balanca`). Uma checagem consiste em pesar uma
massa de teste padrão de 1000g em cada balança e anotar a leitura
mostrada; o status (C/NC) é **calculado automaticamente** a partir da
leitura, não escolhido pelo usuário como nos outros checklists (PAC
11, PAC 08-E).

- **Massa de teste e faixa aceitável são fixas para todas as
  balanças** — não há configuração por balança: `MASSA_TESTE_G =
  1000.0`, faixa `FAIXA_MINIMA_G = 999.0` a `FAIXA_MAXIMA_G = 1001.0`
  (±1g), em `app/tipos/afericao_balanca/models.py`.
  `status_para_leitura(leitura)` decide C ou NC a partir daí — usada
  tanto no backend (ao salvar) quanto reimplementada em JS no
  formulário (feedback ao vivo, sem precisar salvar pra saber).
- **Cadastro mestre auto-populado**: as 20 balanças (setor,
  equipamento, nº balança, nº série, marca, carga máxima) vêm
  hard-coded em `BALANCAS_SEED` e são inseridas na tabela `balancas`
  automaticamente no primeiro boot, via `seed_balancas_se_vazio()`.
  Isso usa uma extensão nova do `TipoRegistro`: o campo opcional
  `seed` (`app/tipos/base.py`) — uma função sem argumentos que
  `app/__init__.py` chama a cada boot, depois da migração de colunas,
  pra qualquer tipo que precise de uma tabela mestre com dados fixos.
  É idempotente (só insere se a tabela estiver vazia), então é seguro
  chamar em todo boot e não sobrescreve edições manuais feitas depois
  direto no banco. Tipos que não precisam disso (a grande maioria)
  simplesmente não passam `seed=...` — fica `None` por padrão.
- **Registro parcial, ao contrário do PAC 08-E**: não é obrigatório
  preencher a leitura de todas as 20 balanças na mesma checagem — só
  as balanças com leitura preenchida naquele envio geram linha
  (`RegistroAfericaoBalanca`). Isso porque a fábrica pode aferir um
  subconjunto numa semana e completar o resto depois.
- Aceita tanto ponto quanto vírgula decimal na leitura (`"998,5"` ou
  `"998.5"`) — convertido no backend antes de calcular o status.
- O painel (`/dashboard/afericao_balanca`) filtra por balança
  específica (dropdown agrupado por setor) e mostra NCs ao longo do
  tempo, mesmo padrão do PAC 08-E.
- Exportação em Excel replica o formato de matriz original: as 20
  balanças nas linhas (agrupadas por setor, cada grupo com sua
  própria linha de cabeçalho em azul), datas nas colunas, cada célula
  com leitura (g) **e** status juntos (ex.: "1000.0g (C)"), NC
  destacado em vermelho.
- Modelo de dados e regras em `app/tipos/afericao_balanca/models.py`.

## Regras de negócio — PAC 08-F - Aferição dos Termômetros

O terceiro tipo semanal, e o segundo com tabela mestre (a exemplo do
PAC 08-G) — o cadastro fixo dos 4 termômetros/equipamentos (tabela
`termometros`). Cada aferição compara um equipamento contra um
**termômetro padrão de referência** (código `AK240607938`, fixo em
`TERMOMETRO_PADRAO_CODIGO` — não é um equipamento cadastrado, só um
valor de contexto mostrado na tela) em duas condições: quente e fria.

**A leitura do padrão é tomada uma única vez por sessão de
registro**, não repetida por equipamento — por isso o esquema de
dados é dividido em duas tabelas (mesmo padrão "sessão + itens" do
PAC 06-D/06-E, pesagens individuais):

- `registros_afericao_termometro` — uma linha por **sessão**: `data`,
  `temp_quente_padrao`, `temp_fria_padrao` (as duas leituras do
  padrão, tomadas uma vez) e `responsavel`.
- `leituras_termometro_equipamento` — uma linha por **equipamento
  aferido** dentro da sessão: `registro_id` (FK pra sessão),
  `termometro_id`, `temp_quente_equipamento`, `temp_fria_equipamento`
  e `status` (calculado). As leituras do padrão não se repetem aqui —
  ficam só na sessão, acessadas via `self.registro` (relationship).

Fluxo da tela de registro, nessa ordem: (1) data, (2) temperatura
quente do padrão — campo único, (3) temperatura quente de cada um
dos 4 equipamentos, (4) temperatura fria do padrão — campo único de
novo, (5) temperatura fria de cada equipamento (com o status C/NC
aparecendo ao lado assim que as 4 temperaturas relevantes daquele
equipamento — 2 do padrão + 2 dele — estiverem preenchidas), (6)
responsável.

- **Duas diferenças, não uma**: `diferenca_quente = abs(quente_padrão
  - quente_equipamento)` e `diferenca_fria = abs(fria_padrão -
  fria_equipamento)`. Status **C só se as duas** ficarem dentro da
  variação aceitável (`DIFERENCA_MAXIMA_C = 1.0`, ±1°C, fixa para
  todos os equipamentos); **NC se qualquer uma das duas** ultrapassar
  — `status_para_leituras()`, em
  `app/tipos/afericao_termometro/models.py`. Nunca escolhido pelo
  usuário, sempre calculado — no backend ao salvar, e reimplementado
  em JS no formulário pra dar feedback ao vivo sem precisar salvar
  pra saber (mudar a leitura do padrão recalcula o status dos 4
  equipamentos de uma vez, já que ela é compartilhada).
- **As 4 leituras dos 4 equipamentos + as 2 leituras do padrão são
  todas obrigatórias**, diferente do PAC 08-G (que aceita
  preenchimento parcial): um envio só salva se tudo estiver
  preenchido — "tudo ou nada", porque a aferição descreve uma única
  sessão de calibração completa, não visitas independentes por
  equipamento. `db.session.flush()` é usado depois de criar a sessão
  (pra garantir o `id` antes de criar as leituras filhas) — tudo
  dentro do mesmo commit, então uma falha no meio não deixa sessão
  órfã sem leituras.
- Aceita ponto ou vírgula decimal, igual aos outros tipos com campos
  numéricos livres (inclusive nas leituras do padrão).
- O painel (`/dashboard/afericao_termometro`) continua mostrando uma
  linha por equipamento aferido (a "unidade" que interessa pro
  filtro e pro gráfico), agora buscada com um `JOIN` entre as duas
  tabelas — filtra por termômetro específico (só 4 opções, sem
  precisar de agrupamento) e mostra NCs ao longo do tempo.
- **Exportação em Excel não é uma matriz** (diferente do PAC 08-E e
  do PAC 08-G) — é uma linha por leitura de equipamento, replicando o
  formato original da planilha: Dia, Nº Equipamento, Equipamento, as
  4 leituras de temperatura (as 2 do padrão vêm da sessão e se
  repetem em cada linha de equipamento daquela sessão), Variação
  Aceitável, C/NC, Responsável. Linhas NC destacadas em vermelho.
- `colunas_backup` do `TipoRegistro` cobre só a tabela da sessão
  (igual ao PAC 06-D/06-E: a tabela de itens/leituras fica de fora do
  CSV automático por tipo — o backup binário `.db` sempre inclui
  tudo, sem exceção).
- Modelo de dados e regras em `app/tipos/afericao_termometro/models.py`.

## Estrutura do projeto

```
temperaturas/
├── app/
│   ├── __init__.py           # application factory
│   ├── extensions.py         # instância do SQLAlchemy
│   ├── backup_utils.py       # dispara backup em segundo plano após salvar (todos os tipos)
│   ├── routes/
│   │   ├── home.py           # "/" splash + "/inicio" categoria (Diárias/Semanais/Mensais) + "/diarias", "/semanais", "/mensais"
│   │   ├── dashboard.py      # painel: decide entre o painel de um tipo específico ou a visão combinada
│   │   └── backup.py         # endpoint HTTP protegido para disparar backup
│   ├── tipos/                # um pacote por tipo de registro — ver seção abaixo
│   │   ├── base.py           # TipoRegistro (dataclass, com campo categoria) + registro central
│   │   └── temperatura/      # tipo "Temperatura de Processo"
│   │       ├── __init__.py    # monta o TipoRegistro e se cadastra
│   │       ├── models.py       # modelo RegistroTemperatura + regras de negócio
│   │       ├── formulario.py    # tela de registro (tablet)
│   │       └── dashboard.py      # painel, API de dados e exportação Excel deste tipo
│   ├── templates/
│   │   ├── splash.html        # tela de splash/abertura (autocontida, sem base.html)
│   │   ├── home_categorias.html  # tela "Categoria de Registro" (Diárias/Semanais/Mensais)
│   │   ├── home_tipos.html    # grade de tipos de uma categoria (usada por /diarias, /semanais, /mensais)
│   │   ├── dashboard_combinado.html  # visão combinada (2+ tipos)
│   │   └── tipos/temperatura/  # templates específicos do tipo
│   └── static/
│       └── tipos/temperatura/   # JS/CSS específicos do tipo
├── backup.py               # script de backup (rodar via cron)
├── config.py
├── wsgi.py                 # ponto de entrada (gunicorn wsgi:app)
├── requirements.txt
├── Procfile                 # Render / Railway
├── render.yaml               # blueprint do Render (opcional)
├── railway.json               # config do Railway (opcional)
└── .python-version
```

## Arquitetura: tipos de registro

Cada "planilha" (Temperatura de Processo, e futuras) é um **tipo de
registro** — um pacote isolado em `app/tipos/<slug>/` com sua própria
tabela, formulário e painel. As telas de navegação (`/diarias`,
`/semanais`, `/mensais`) e o painel (`/dashboard`) são genéricos: eles
descobrem os tipos disponíveis automaticamente a partir de um
registro central (`app/tipos/base.py`), sem precisar saber de
antemão quais tipos existem. Cada tipo também declara sua
**categoria** — `"diaria"` (padrão), `"semanal"` ou `"mensal"` — que
decide em qual das três telas ele aparece; ver "Navegação por
categoria" logo abaixo.

### Como adicionar um novo tipo de registro

Usando `app/tipos/temperatura/` como referência, para um novo tipo
`<slug>` (ex.: `limpeza`):

1. **Crie o pacote** `app/tipos/<slug>/` com 4 arquivos:
   - `models.py` — o modelo SQLAlchemy (`__tablename__` próprio) e as
     regras de validação/conformidade específicas deste tipo.
   - `formulario.py` — um Blueprint **chamado exatamente `<slug>`**,
     com `url_prefix="/<slug>"`, uma rota `""` (GET) chamada `index`
     e uma rota de submissão (ex. `/registrar`, POST). Depois de
     salvar, chame `app.backup_utils.agendar_backup_apos_registro()`.
   - `dashboard.py` — um Blueprint **chamado `<slug>_dashboard`**,
     com `url_prefix="/dashboard/<slug>"` e rota `""` (GET) chamada
     `index` com o painel completo deste tipo (siga
     `app/tipos/temperatura/dashboard.py` como modelo: filtros, API
     JSON, exportação Excel). Também exponha três funções usadas pela
     visão combinada de vários tipos:
     - `contar(inicio, fim) -> int`
     - `linhas_combinadas(inicio, fim) -> list[dict]` — cada dict:
       `{"tipo", "icone", "data", "horario", "resumo", "conforme", "ordenacao"}`
       (`conforme` pode ser `None` se o tipo não tiver esse conceito)
     - `adicionar_planilha(workbook, inicio, fim, filtros_extra)` —
       acrescenta uma aba ao workbook (`wb.create_sheet(...)`, nunca
       assuma que é a única aba)
   - `__init__.py` — monta um `TipoRegistro` (slug, nome de exibição,
     ícone/emoji, nome da tabela SQL, colunas para o backup CSV, e as
     3 funções acima) e chama `registrar_tipo(TIPO, formulario_bp, dashboard_bp)`.
     Passe também `categoria="semanal"` ou `categoria="mensal"` se o
     novo tipo não for diário (o padrão é `"diaria"`, usado pelos 9
     tipos originais) — é só isso que decide se ele aparece em
     `/diarias`, `/semanais` ou `/mensais`. Se o tipo depender de uma
     tabela mestre com dados fixos que precisam existir populados
     desde o primeiro boot (ex.: um cadastro de equipamentos — ver
     PAC 08-G), passe também `seed=<função sem argumentos>`; ela é
     chamada automaticamente a cada boot (precisa ser idempotente —
     ver `seed_balancas_se_vazio` em
     `app/tipos/afericao_balanca/models.py` como referência).

2. **Registre o pacote**: adicione `from app.tipos import <slug>` no
   final de `app/tipos/__init__.py`.

3. **Templates**: crie `app/templates/tipos/<slug>/formulario.html` e
   `dashboard.html`, estendendo `base.html` (copie os de temperatura
   como ponto de partida). Estáticos específicos (JS/CSS) vão em
   `app/static/tipos/<slug>/`.

4. Pronto — a tela da categoria correspondente (`/diarias`,
   `/semanais` ou `/mensais`, conforme o `categoria` escolhido), o
   `/dashboard` combinado e a exportação combinada
   (`/exportar?tipo=todos`) passam a incluir o novo tipo
   automaticamente, e o backup (local + S3) passa a cobrir a nova
   tabela sozinho (via `colunas_backup`/`tabela` do `TipoRegistro`).

Nada no `RegistroTemperatura` original muda ao adicionar um novo
tipo — cada tipo é isolado no seu próprio pacote/tabela.

### Navegação por categoria (Diárias / Semanais / Mensais)

A navegação tem uma camada a mais antes da grade de tipos: depois da
splash, `/inicio` mostra três botões — Diárias, Semanais e Mensais —
e cada um leva pra grade de tipos daquela frequência (`/diarias`,
`/semanais`, `/mensais`, todas renderizadas pelo mesmo template
`home_tipos.html`, filtrando `TIPOS_REGISTRO` pelo campo `categoria`
de cada um via `tipos_por_categoria()`). Os 9 tipos originais são
diários; PAC 08-E (Monitoramento da Ventilação), PAC 08-G (Aferição
das Balanças) e PAC 08-F (Aferição dos Termômetros) são semanais —
cada um só precisou de `categoria="semanal"` no seu
`TipoRegistro(...)`, sem tocar em `app/routes/home.py` nem nos
templates, e `/semanais` já mostra os três lado a lado (ver
`app/tipos/ventilacao/__init__.py`, `app/tipos/afericao_balanca/__init__.py`
e `app/tipos/afericao_termometro/__init__.py` como referência de
ponta a ponta pra um tipo não-diário — os dois últimos também mostram
como plugar `seed` pra um tipo com tabela mestre, inclusive um
segundo caso de tabela mestre pra comparar). `/mensais` ainda não tem
nenhum tipo, então mostra "nenhum registro cadastrado ainda" — o
próximo tipo com `categoria="mensal"` aparece lá do mesmo jeito. O painel
(`/dashboard`) e a exportação continuam ignorando a categoria —
sempre mostram/exportam todos os tipos juntos, independente de
frequência.

### Alterando os campos de um tipo que já está em produção

`db.create_all()` só **cria** tabelas que ainda não existem — nunca
altera uma tabela que já existe. Então, se um tipo que já está no ar
ganha um campo novo ou renomeado no `models.py` (ex.: o PAC 06-E
trocou `gramatura_nominal` por `gramatura_minima`/`gramatura_maxima`
depois do primeiro deploy), o banco em produção fica desatualizado, e
tudo que toca a coluna nova quebra com `no such column` — inclusive o
backup automático.

Pra isso não exigir mexer no banco manualmente a cada mudança dessas,
`_migrar_colunas_faltantes()` (`app/__init__.py`) roda sozinha em
todo boot, depois de `db.create_all()`, e resolve nos dois sentidos:
adiciona (via `ALTER TABLE ADD COLUMN`) qualquer coluna que o modelo
tenha e a tabela real não tenha, e remove (via `ALTER TABLE DROP
COLUMN`) qualquer coluna "órfã" que a tabela real ainda tenha mas o
modelo não usa mais — importante porque uma coluna órfã com `NOT
NULL` bloquearia todo INSERT novo, já que o SQLAlchemy nem menciona
mais essa coluna. Genérica: não lista tipo por tipo, cobre qualquer
tabela conhecida pelo SQLAlchemy. Basta dar `git push` — o próximo
boot se autocorrige.

Como segunda linha de defesa, `_exportar_csv()` (`backup.py`) isola
cada tipo num `try/except` — mesmo que a auto-migração falhe por
algum motivo (ex.: SQLite antigo demais sem suporte a `DROP COLUMN`),
um tipo com problema de esquema não derruba mais o backup inteiro: o
`.db` binário e os demais tipos continuam sendo gerados e enviados
normalmente.

## Rodando localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python wsgi.py
```

Acesse `http://localhost:5000` (splash de abertura, redireciona
sozinha em alguns segundos para `/inicio` — a tela de escolha da
categoria: Diárias/Semanais/Mensais) e `http://localhost:5000/dashboard`
(painel). O banco `instance/temperaturas.db` é criado automaticamente
no primeiro acesso.

## Fuso horário

Hospedagens como o Render rodam o servidor com o relógio em UTC.
Para que `data`/`horario` de todo registro (em todos os tipos) e os
filtros "Hoje"/"Última semana"/"Último mês" do painel reflitam o
horário de Brasília (não o horário "cru" do servidor), o sistema usa
`agora_brasilia()` (`app/timezone_utils.py`) — um deslocamento fixo
de -3h sobre o UTC — em vez de `date.today()`/`datetime.now()`
diretos. O Brasil não usa mais horário de verão desde 2019, então
esse deslocamento fixo é seguro e não depende de tabela de fuso
horário (tzdata) no servidor.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | chave de desenvolvimento | Troque em produção |
| `DATABASE_PATH` | `instance/temperaturas.db` | Caminho do arquivo SQLite |
| `BACKUP_DIR` | `backups/` | Pasta onde os backups são salvos |
| `BACKUP_MANTER_ULTIMOS` | `30` | Quantos backups recentes manter |
| `BACKUP_TOKEN` | (vazio) | Se definido, habilita `POST /backup/executar` |
| `RESET_TOKEN` | (vazio) | Se definido, habilita a tela `/admin/resetar` (apaga todos os registros — ver seção abaixo) |
| `BACKUP_S3_BUCKET` | (vazio) | Se definido, faz backup a cada registro salvo para um bucket S3/compatível e restaura automaticamente na inicialização |
| `BACKUP_S3_ENDPOINT_URL` | (vazio) | Endpoint do serviço S3-compatível (ex.: Cloudflare R2). Não definir para AWS S3 de verdade |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | (vazio) | Credenciais do bucket (S3/R2/compatível) |
| `BACKUP_AUTOMATICO` | `false` | Se `true`, roda o backup periodicamente em segundo plano além do backup por registro (reforço extra, útil com disco persistente) |
| `BACKUP_INTERVALO_HORAS` | `6` | Intervalo entre backups automáticos, quando `BACKUP_AUTOMATICO=true` |
| `PORT` | `5000` | Porta usada por `wsgi.py` em execução direta |

## ⚠️ Atenção: persistência do SQLite na nuvem

Tanto Render quanto Railway usam **sistema de arquivos efêmero** por
padrão: a cada novo deploy (ou reinício do container), tudo que foi
gravado em disco — incluindo o arquivo `.db` — é apagado, a menos que
você use um dos dois caminhos abaixo. Escolha um deles antes de ir
para produção.

### Opção A — Disco persistente (mais robusta, plano pago)

- **Render:** adicione um "Disk" ao serviço (a partir do plano
  Starter) e aponte `DATABASE_PATH`/`BACKUP_DIR` para dentro dele. O
  `render.yaml` incluso já faz isso (monta em `/var/data`).
- **Railway:** crie um "Volume" no serviço e aponte as mesmas
  variáveis para o caminho montado (ex.: `/data`).
- Não há janela de perda de dados: o arquivo nunca é apagado entre
  deploys.

### Opção B — Plano gratuito, com backup + restauração automática no S3

**Atenção com o plano Free do Render especificamente:** o disco não é
apagado só em redeploys — é apagado **toda vez que o serviço "dorme"
por inatividade** (~15 min sem acesso), que é bem mais frequente. Por
isso, nessa opção, o backup roda **a cada registro salvo** (não só
periodicamente) — é o único jeito de garantir que o registro sobreviva
até o próximo "sono" do serviço.

Basta definir `BACKUP_S3_BUCKET` (e as credenciais — veja tabela de
variáveis abaixo). Com isso:

1. Toda vez que alguém salva um registro (de qualquer tipo), um
   backup roda em segundo plano e sobe para o S3 (ou compatível:
   Cloudflare R2, Backblaze B2) — sem atrasar a resposta pro usuário.
2. Ao subir num disco vazio (ex.: logo após o serviço "dormir" e
   acordar, ou um redeploy), a aplicação **restaura automaticamente**
   o backup mais recente do S3 antes de criar um banco novo — os
   registros anteriores voltam sozinhos.
3. **Risco residual:** só o registro que está sendo salvo *no exato
   momento* de uma queda tem chance de se perder — o backup desse
   registro específico pode não ter terminado de subir ainda. Na
   prática, para o ritmo de uma fábrica, isso é raro.
4. `BACKUP_AUTOMATICO=true` (+ `BACKUP_INTERVALO_HORAS`) continua
   disponível como reforço periódico adicional, mas em planos Free não
   é a defesa principal — o disco costuma dormir antes do intervalo
   periódico chegar.
5. `boto3` já vem no `requirements.txt`.

#### Passo a passo com Cloudflare R2 (gratuito, sem cartão de crédito)

1. Crie uma conta em [dash.cloudflare.com](https://dash.cloudflare.com/sign-up)
   (gratuita).
2. No menu lateral, vá em **R2 Object Storage** → **Create bucket**.
   Dê um nome (ex.: `temperaturas-backup`) e crie.
3. Em **R2** → **Manage API Tokens** → **Create API Token**, permissão
   "Object Read & Write", escopo no bucket criado. Copie os 3 valores
   que ele mostrar: **Access Key ID**, **Secret Access Key** e o
   **Endpoint S3** (algo como
   `https://<account_id>.r2.cloudflarestorage.com`).
4. No serviço do Render (ou Railway), aba **Environment**, adicione:

   | Variável | Valor |
   |---|---|
   | `BACKUP_S3_BUCKET` | o nome do bucket (ex.: `temperaturas-backup`) |
   | `BACKUP_S3_ENDPOINT_URL` | o Endpoint S3 copiado no passo 3 |
   | `AWS_ACCESS_KEY_ID` | o Access Key ID copiado |
   | `AWS_SECRET_ACCESS_KEY` | o Secret Access Key copiado |

5. Salve — o Render/Railway reinicia o serviço sozinho com as novas
   variáveis. A partir daí, todo registro salvo já sobe backup
   automaticamente.

Em qualquer uma das opções, a rotina de backup (próxima seção)
continua útil como proteção extra contra exclusão acidental de dados,
não apenas contra deploys.

## Backup automático

O script `backup.py`:
1. Copia o arquivo SQLite de forma segura (API de backup nativa do
   SQLite, funciona com o banco em uso).
2. Exporta os dados também em CSV.
3. Mantém apenas os últimos `BACKUP_MANTER_ULTIMOS` backups (rotação).
4. Se `BACKUP_S3_BUCKET` estiver definido, também envia os arquivos
   para um bucket S3 (ou compatível: Cloudflare R2, Backblaze B2).
5. Se o app subir com `DATABASE_PATH` inexistente e `BACKUP_S3_BUCKET`
   definido, restaura sozinho o backup `.db` mais recente do S3 antes
   de criar um banco vazio (ver Opção B acima).

Rodar manualmente:

```bash
python backup.py
```

**Como agendar:**

- **Sem custo extra, dentro do próprio app:** defina
  `BACKUP_AUTOMATICO=true` — uma thread interna roda o backup a cada
  `BACKUP_INTERVALO_HORAS` (padrão 6h) enquanto a aplicação estiver no
  ar. É a opção usada na Opção B acima.
- **Render (Cron Job dedicado):** crie um "Cron Job" separado no mesmo
  projeto, apontando para este repositório, com o comando
  `python backup.py`. Configure o mesmo `DATABASE_PATH`/`BACKUP_DIR`
  do serviço web.
- **Railway:** crie um serviço com "Cron Schedule" e o mesmo comando.
- **Qualquer host (alternativa via HTTP):** defina `BACKUP_TOKEN` e
  use um cron externo (ex. cron-job.org, GitHub Actions agendado) para
  chamar periodicamente:
  ```bash
  curl -X POST https://seu-app.onrender.com/backup/executar \
       -H "X-Backup-Token: SEU_TOKEN"
  ```

> Rodando com mais de 1 worker do gunicorn, cada worker abriria sua
> própria thread de backup automático (redundante, mas inofensivo).
> Para esta aplicação (SQLite, baixo volume) o padrão de 1 worker do
> `Procfile` já é o recomendado — evite aumentar `--workers` sem
> migrar para um banco que suporte mais concorrência.

## Apagar todos os registros (reset)

Útil pra limpar dados de teste antes de começar a usar o sistema de
verdade — apaga **todos** os registros de **todos** os tipos de uma
vez (não dá pra escolher só alguns).

1. Defina a variável de ambiente `RESET_TOKEN` (qualquer senha sua,
   igual você já fez com `BACKUP_TOKEN`) nas configurações do seu
   serviço (Render → Environment). Sem essa variável, a tela de reset
   fica desabilitada.
2. Acesse `https://SEU-APP.onrender.com/admin/resetar?token=SEU_TOKEN`
   (troque pela URL do seu serviço e pelo valor que você definiu em
   `RESET_TOKEN`).
3. A tela mostra quantos registros existem hoje, com o nome de cada
   módulo (ex.: "PAC 11 - Monitoramento dos PSO's") e o nome técnico
   da tabela logo abaixo. Quer conferir os dados antes de decidir?
   Tem um link "Baixe uma prévia em JSON agora, sem apagar nada" —
   baixa um arquivo com tudo que existe hoje, sem mexer em nada.
4. Digite **APAGAR TUDO** no campo de confirmação pra habilitar o
   botão vermelho, e clique nele.
5. Antes de apagar de verdade, o sistema salva sozinho um backup
   completo em JSON de tudo que existia (localmente e no S3/B2, se
   configurado) — a tela de sucesso mostra o nome do arquivo e um
   link **"📥 Baixar esse backup agora (JSON)"**, com a contagem de
   quantos registros foram apagados, módulo por módulo.
6. Pronto — todas as tabelas voltam a ficar vazias, e (se
   `BACKUP_S3_BUCKET` estiver configurado) um backup "normal" também é
   disparado na hora, automaticamente.

O backup logo depois do reset (o "normal", não o JSON pré-reset) é
importante, não só decorativo: sem ele, o **último** backup salvo no
S3/B2 continuaria com os dados antigos, e a próxima vez que o Render
"acordasse" do plano Free (disco apagado) restauraria justamente o
que você acabou de apagar. Com o backup atualizado na hora, o estado
"vazio" já fica salvo.

O backup em JSON pré-reset fica salvo com um nome fixo
(`pre_reset_<data>_<hora>.json`, fora do padrão usado pelos backups
de rotina) — não é apagado pela limpeza automática de backups
antigos, então continua disponível pra consulta bem depois do reset,
tanto localmente (`/admin/resetar/backup/<nome_do_arquivo>?token=...`)
quanto no S3/B2 (se configurado).

Depois de usar, não precisa remover `RESET_TOKEN` — a tela continua
protegida pelo token, então só quem souber a senha consegue acessá-la
de novo (e você pode trocá-la ou apagá-la quando quiser desabilitar
de vez).

## Deploy

### Render (recomendado — já tem `render.yaml` pronto)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/qualidadeparaforms-web/temperaturas)

1. Clique no botão acima (leva à tela de login/criação de conta do
   Render, se ainda não tiver uma).
2. O Render lê o `render.yaml` deste repositório sozinho e já propõe:
   um Web Service (`gunicorn wsgi:app`) com um Disk persistente
   montado em `/var/data` e `SECRET_KEY`/`BACKUP_TOKEN` gerados
   automaticamente. Confirme e clique em "Apply" — a build leva
   1-2 minutos.
3. Esse plano (`starter`, por causa do Disk) é pago. Se quiser testar
   de graça primeiro, edite o `render.yaml` antes de clicar no botão
   (ou os campos na tela do Render) seguindo a "Opção B" comentada no
   próprio arquivo — remove o Disk e usa backup/restore automático via
   S3 em vez de disco persistente.
4. Ao terminar, o Render mostra a URL pública (algo como
   `https://temperaturas-app.onrender.com`) — abra essa URL no tablet.

**Sem passar pelo botão:** "New +" → "Blueprint" → selecione o
repositório, **ou** crie manualmente um "Web Service" com Build
command `pip install -r requirements.txt` e Start command
`gunicorn wsgi:app`.

### Railway (alternativa)
1. Suba este repositório no GitHub (já está).
2. No Railway, "New Project" → "Deploy from GitHub repo" → selecione
   `qualidadeparaforms-web/temperaturas`.
3. O Railway detecta o `Procfile`/`railway.json` e usa
   `gunicorn wsgi:app` como comando de start automaticamente.
4. Configure as variáveis de ambiente (veja tabela acima) na aba
   "Variables" do serviço.
5. Adicione um Volume (aba "Volumes") se quiser persistência, ou use
   `BACKUP_AUTOMATICO=true` + `BACKUP_S3_BUCKET` (Opção B) sem custo
   extra de disco.
6. O Railway gera a URL pública em "Settings" → "Networking" →
   "Generate Domain".

## Telas

1. **Splash de abertura** (`/`) — a primeira coisa que aparece ao
   acessar a URL do sistema: fundo navy, o logo da Resplendor
   Alimentos com um leve fade-in, o texto "Sistema de Controle de
   Qualidade" e uma barra de progresso decorativa. Puramente
   estática — depois de ~3,6s redireciona sozinha (via JS, com
   `<meta http-equiv="refresh">` de reforço caso o JS não rode) para
   a tela de início (`/inicio`). Página autocontida (não estende
   `base.html`, sem navbar) — ver `app/templates/splash.html`. O logo
   é um SVG desenhado à mão (leque de raios + "Resplendor"), recriado
   visualmente a partir da imagem enviada no chat — sem acesso ao
   arquivo original nesse ambiente, não dava pra usá-lo direto; troque
   o `<svg>` no template pelo arquivo oficial quando for conveniente,
   se quiser fidelidade exata ao logo real.
2. **Categoria de Registro** (`/inicio`) — primeira escolha depois da
   splash: três botões grandes, um por frequência — "📆 Diárias", "🗓️
   Semanais" e "📅 Mensais". O link "Início" da barra de navegação
   sempre aponta direto pra cá — a splash só aparece uma vez, ao
   acessar a URL raiz. Ver `app/routes/home.py` (`index()`) e
   `app/templates/home_categorias.html`.
3. **Diárias** (`/diarias`) — grade de botões grandes, um por tipo de
   registro diário cadastrado: hoje "🌡️ Temperatura de Processo", "🧊
   Temperatura de Setor/Câmara", "💧 PAC 03-A - Água de
   Abastecimento", "🥩 PAC 04-C - Temperatura dos Produtos", "📦
   PAC 04-D - Câmaras de Expedição", "⚖️ PAC 06-D - Monitoramento de
   Peso", "📏 PAC 06-E - Monitoramento de Gramatura", "🧼 PAC 11 -
   Monitoramento dos PSO's" e "🪡 PAC 17 - Integridade de Componentes
   de Máquinas" — os 9 tipos existentes hoje são todos diários. Ao
   clicar, leva ao formulário daquele tipo; "← Voltar" retorna pra
   `/inicio`.
4. **Semanais** (`/semanais`) — mesma tela de grade de "Diárias", já
   com os 3 tipos semanais cadastrados: "🌬️ PAC 08-E - Monitoramento
   da Ventilação" (item 16 abaixo), "🎯 PAC 08-F - Aferição dos
   Termômetros" (item 17 abaixo) e "⚙️ PAC 08-G - Aferição das
   Balanças" (item 18 abaixo). Um tipo semanal novo aparece aqui do
   lado, automaticamente.
5. **Mensais** (`/mensais`) — mesma tela de grade, ainda vazia
   ("Nenhum registro mensal cadastrado ainda"): é só a estrutura
   pronta pra receber o primeiro tipo dessa frequência (ver "Como
   adicionar um novo tipo de registro" acima — basta
   `categoria="mensal"` no `TipoRegistro`, sem mexer em rota nem
   template).
6. **Registro de temperatura** (`/temperatura`) — botões grandes por
   etapa, campo numérico de temperatura, campo de responsável (com
   sugestões dos últimos nomes digitados) e botão "Salvar" grande.
   Mostra alerta de sucesso ou de "fora do padrão" imediatamente após
   salvar.
7. **Registro de temperatura de setor/câmara** (`/temperatura_setor`)
   — mesma ideia, mas com um campo de busca no lugar da grade fixa de
   botões (17 setores é demais pra caber sem rolar a tela toda): a
   busca filtra os botões em tempo real por nome, sem diferenciar
   acento. Temperatura aceita negativos.
8. **Registro de água de abastecimento** (`/agua_abastecimento`) —
   botões grandes pro ponto de coleta (9 pontos fixos, mesmo padrão de
   etapa/setor), campos numéricos de pH e Cloro. O alerta indica
   especificamente qual dos dois está fora do padrão.
9. **Registro de temperatura de produto** (`/temp_produto`) — botões
   pra local e categoria, campo de texto pro nome do produto (com
   sugestões dos últimos produtos digitados), temperatura numérica. O
   limite de conformidade depende da categoria escolhida (Corte vs.
   Carne Moída), não é fixo. Sem limite de quantos registros por dia.
10. **Registro de temperatura de expedição** (`/temp_expedicao`) —
    botões pra local (4 câmaras/pontos), e o seletor de categoria
    aparece ou some dinamicamente dependendo do local escolhido ("Matéria
    Prima - Quebra de Gelo" não tem categoria). O limite depende da
    combinação local + categoria. Temperatura aceita negativos.
11. **Registro de monitoramento de peso** (`/peso_produto`) — dados do
    produto (nome, peso líquido nominal, peso da embalagem,
    responsável) e, em seguida, uma seção pra ir lançando pesagens
    individuais uma a uma (campo numérico + botão "+ Adicionar"): cada
    pesagem entra numa lista visual verde/vermelho conforme atinge ou
    não o padrão mínimo (peso líquido + embalagem), com um resumo ao
    vivo (total de pesagens, NCs, % conforme) e opção de remover
    qualquer pesagem antes de salvar. A seção de pesagens só aparece
    depois de preencher os dois pesos; o botão "Finalizar registro do
    produto" só habilita com pelo menos uma pesagem lançada. Um único
    envio salva o registro do produto e todas as pesagens juntos.
12. **Registro de monitoramento de gramatura** (`/gramatura`) — mesma
    ideia e mesma tela do PAC 06-D, adaptada: dados do produto (nome,
    faixa de gramatura mínima e máxima, operador, responsável) e a
    mesma seção de pesagens individuais com lista visual
    verde/vermelho e resumo ao vivo. Aqui não há peso de embalagem — a
    seção de pesagens libera assim que a faixa (mínima e máxima) é
    preenchida, e cada pesagem é comparada com ela: qualquer valor
    fora da faixa é NC.
13. **Registro de monitoramento dos PSOs** (`/pso`) — checklist com os
    7 PSOs fixos, cada um com um par de botões grandes "✅ C" (verde) e
    "⚠️ NC" (vermelho), seguido do campo Responsável (Monitor). O
    navegador exige uma seleção (C ou NC) em cada um dos 7 antes de
    deixar enviar; um único envio salva o status dos 7 PSOs do dia de
    uma vez.
14. **Registro de integridade de componentes** (`/integridade_componente`)
    — escolha do equipamento (3 botões, cada um com o nome do
    componente entre parênteses), momento da checagem (a opção
    "Troca de Lâminas" só aparece pra Máquina de Cubos e Iscas),
    horário digitado manualmente (não é preenchido sozinho — dá pra
    registrar depois), status C/NC (mesmo par de botões verde/vermelho
    do PAC 11) e responsável. O alerta de NC destaca o risco de
    contaminação física do produto.
15. **Verificação RT** (`/integridade_componente/verificacao-rt`, com
    atalho fixo "⚡ Verificação RT" na barra de navegação — a única
    ação disponível em qualquer tela do sistema) — três botões, um
    por equipamento; tocar em um já salva a data/hora e o
    equipamento, sem formulário. Mostra as verificações já feitas
    hoje logo abaixo, como confirmação visual.
16. **Registro de monitoramento da ventilação** (`/ventilacao`) — o
    primeiro tipo semanal: campo de data (o usuário escolhe qual
    checagem está registrando, não é sempre "hoje"), os 22 setores
    fixos organizados visualmente em 2 grupos com cabeçalho separador
    ("Setor Produção" e "Setor Embalagem Secundária e Expedição"),
    cada um com o mesmo par de botões "✅ C"/"⚠️ NC" do PAC 11, e
    Responsável (Monitor). Um único envio salva os 22 setores de uma
    vez. "← Escolher outro tipo de registro" volta pra `/semanais`
    (não pra `/inicio`), mesmo padrão dos tipos diários voltando pra
    `/diarias`.
17. **Registro de aferição dos termômetros** (`/afericao_termometro`)
    — o terceiro tipo semanal, em 6 passos: (1) data; (2) temperatura
    quente do **padrão** (`AK240607938`) — campo único, uma leitura
    só pra sessão inteira; (3) temperatura quente de cada um dos 4
    equipamentos; (4) temperatura fria do padrão — campo único de
    novo; (5) temperatura fria de cada equipamento, com o status
    conforme/NC aparecendo ao lado assim que as leituras relevantes
    daquele equipamento (as 2 do padrão + as 2 dele) estiverem
    preenchidas; (6) responsável. Mudar a leitura do padrão recalcula
    o status dos 4 equipamentos de uma vez, já que ela é
    compartilhada. As 4 leituras dos 4 equipamentos + as 2 do padrão
    são todas obrigatórias — "tudo ou nada" num único envio. "←
    Escolher outro tipo de registro" também volta pra `/semanais`.
18. **Registro de aferição das balanças** (`/afericao_balanca`) — o
    segundo tipo semanal: campo de data, e as 20 balanças cadastradas
    (organizadas em grupos por setor, mesmo padrão visual do PAC
    08-E), cada uma com um campo numérico pra leitura da massa de
    teste (1000g) — o status conforme/NC aparece ao lado, calculado
    ao vivo conforme digita, sem precisar salvar pra saber. Ao
    contrário do PAC 08-E, não é preciso preencher todas as balanças
    de uma vez: só as preenchidas são salvas no envio. "← Escolher
    outro tipo de registro" também volta pra `/semanais`.
19. **Painel** (`/dashboard`) — com um único tipo cadastrado, vai
    direto para o painel daquele tipo; com dois ou mais (como hoje),
    mostra uma visão combinada por padrão (cartões de contagem por tipo
    + tabela unificada), com um seletor para entrar no painel completo
    de cada tipo (filtros específicos, cartões de resumo, gráfico ao
    longo do tempo com pontos fora do padrão em vermelho — o painel de
    água de abastecimento usa dois eixos Y, um pra pH e outro pra
    Cloro, já que têm faixas e unidades diferentes — e tabela com
    destaque vermelho nas linhas fora do padrão). Nos painéis de
    monitoramento de peso e de gramatura, cada ponto do gráfico é uma
    avaliação de produto (não uma pesagem individual), com o eixo Y
    mostrando o total de NCs daquela avaliação. No painel do PAC 11,
    cada PSO é uma linha no gráfico, com um filtro adicional pra
    isolar o histórico de um PSO específico e identificar se algum é
    recorrente em NC — como não há horário, o eixo X é só por dia. O
    painel do PAC 17 segue o mesmo formato, com um filtro por
    equipamento e uma linha por equipamento no gráfico; a tela de
    Verificação RT não tem painel próprio (é só um log rápido, sem
    conceito de conformidade). Os painéis do PAC 08-E e do PAC 08-G
    seguem o mesmo formato do PAC 11: uma linha por setor (PAC 08-E)
    ou por balança (PAC 08-G) no gráfico, com filtro pra isolar um
    item específico — a legenda do gráfico se esconde sozinha quando
    mais de 8 linhas aparecem juntas, pra não poluir a tela. O painel
    do PAC 08-F segue a mesma ideia, mas com só 4 termômetros (a
    legenda sempre fica visível) e o filtro comparando as duas
    diferenças (quente e fria) no tooltip do gráfico.
20. **Exportar Excel** — botão no painel que baixa um `.xlsx` com as
    colunas do tipo em questão, respeitando os filtros aplicados.
    Linhas fora do padrão vêm destacadas em vermelho na planilha. O
    monitoramento de peso e o de gramatura geram duas abas cada: um
    resumo por avaliação de produto ("Peso Produto"/"Gramatura") e o
    detalhe de cada pesagem individual ("Peso Produto
    Detalhe"/"Gramatura Detalhe"). O PAC 11 gera uma aba no formato de
    matriz original: PSOs nas linhas (sempre os 7), um dia do período
    por coluna, C/NC em cada célula (NC destacado em vermelho) — esse
    formato ignora o filtro de PSO do painel de propósito, pra sempre
    mostrar o checklist completo. O PAC 08-E segue o mesmo formato de
    matriz, mas com os 22 setores nas linhas, agrupados em 2 seções
    (cada uma com sua própria linha de cabeçalho destacada em azul) —
    também ignora o filtro de setor do painel. O PAC 08-G usa a mesma
    matriz agrupada por setor, mas com as 20 balanças nas linhas e
    cada célula mostrando leitura **e** status juntos (ex.: "1000.0g
    (C)"), também ignorando o filtro de balança do painel. O PAC 08-F
    foge do formato de matriz — gera uma linha por aferição (igual à
    Temperatura de Processo e à maioria dos outros tipos), com as
    colunas exatas da planilha original: Dia, Nº Equipamento,
    Equipamento, as 4 leituras de temperatura, Variação Aceitável,
    C/NC, Responsável. O PAC 17 também gera duas abas: "Integridade
    Componentes" (os registros C/NC) e "Verificações RT" (o histórico
    de conferências rápidas, sempre com todos os equipamentos,
    ignorando o filtro do painel). Na visão combinada, "Exportar
    tudo" gera um único arquivo com uma aba por tipo
    (`/exportar?tipo=todos`, duas abas para os tipos que têm
    detalhe/verificação separados).

## Paleta de cores

| Cor | Hex | Uso |
|---|---|---|
| Navy | `#1F3864` | Cabeçalho, títulos, botão Salvar |
| Azul | `#2E75B6` | Botões de etapa, destaques primários |
| Amarelo | `#FFF2CC` | Fundo de avisos |
| Vermelho | `#C00000` | Destaque de registros fora do padrão |
| Verde | `#2E7D32` | Botão "C" (conforme) do checklist de PSOs (PAC 11) e da checagem de integridade (PAC 17) |

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

## Estrutura do projeto

```
temperaturas/
├── app/
│   ├── __init__.py           # application factory
│   ├── extensions.py         # instância do SQLAlchemy
│   ├── backup_utils.py       # dispara backup em segundo plano após salvar (todos os tipos)
│   ├── routes/
│   │   ├── home.py           # tela inicial — grade com um botão por tipo de registro
│   │   ├── dashboard.py      # painel: decide entre o painel de um tipo específico ou a visão combinada
│   │   └── backup.py         # endpoint HTTP protegido para disparar backup
│   ├── tipos/                # um pacote por tipo de registro — ver seção abaixo
│   │   ├── base.py           # TipoRegistro (dataclass) + registro central
│   │   └── temperatura/      # tipo "Temperatura de Processo"
│   │       ├── __init__.py    # monta o TipoRegistro e se cadastra
│   │       ├── models.py       # modelo RegistroTemperatura + regras de negócio
│   │       ├── formulario.py    # tela de registro (tablet)
│   │       └── dashboard.py      # painel, API de dados e exportação Excel deste tipo
│   ├── templates/
│   │   ├── home.html          # tela inicial
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
tabela, formulário e painel. A tela inicial (`/`) e o painel
(`/dashboard`) são genéricos: eles descobrem os tipos disponíveis
automaticamente a partir de um registro central
(`app/tipos/base.py`), sem precisar saber de antemão quais tipos
existem.

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

2. **Registre o pacote**: adicione `from app.tipos import <slug>` no
   final de `app/tipos/__init__.py`.

3. **Templates**: crie `app/templates/tipos/<slug>/formulario.html` e
   `dashboard.html`, estendendo `base.html` (copie os de temperatura
   como ponto de partida). Estáticos específicos (JS/CSS) vão em
   `app/static/tipos/<slug>/`.

4. Pronto — a tela inicial, o `/dashboard` combinado e a exportação
   combinada (`/exportar?tipo=todos`) passam a incluir o novo tipo
   automaticamente, e o backup (local + S3) passa a cobrir a nova
   tabela sozinho (via `colunas_backup`/`tabela` do `TipoRegistro`).

Nada no `RegistroTemperatura` original muda ao adicionar um novo
tipo — cada tipo é isolado no seu próprio pacote/tabela.

## Rodando localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python wsgi.py
```

Acesse `http://localhost:5000` (tela inicial, escolha do tipo de
registro) e `http://localhost:5000/dashboard` (painel). O banco
`instance/temperaturas.db` é criado automaticamente no primeiro acesso.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | chave de desenvolvimento | Troque em produção |
| `DATABASE_PATH` | `instance/temperaturas.db` | Caminho do arquivo SQLite |
| `BACKUP_DIR` | `backups/` | Pasta onde os backups são salvos |
| `BACKUP_MANTER_ULTIMOS` | `30` | Quantos backups recentes manter |
| `BACKUP_TOKEN` | (vazio) | Se definido, habilita `POST /backup/executar` |
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

1. **Início** (`/`) — grade de botões grandes, um por tipo de
   registro cadastrado: hoje "🌡️ Temperatura de Processo", "🧊
   Temperatura de Setor/Câmara", "💧 PAC 03-A - Água de
   Abastecimento", "🥩 PAC 04-C - Temperatura dos Produtos", "📦
   PAC 04-D - Câmaras de Expedição" e "⚖️ PAC 06-D - Monitoramento de
   Peso". Ao clicar, leva ao formulário daquele tipo.
2. **Registro de temperatura** (`/temperatura`) — botões grandes por
   etapa, campo numérico de temperatura, campo de responsável (com
   sugestões dos últimos nomes digitados) e botão "Salvar" grande.
   Mostra alerta de sucesso ou de "fora do padrão" imediatamente após
   salvar.
3. **Registro de temperatura de setor/câmara** (`/temperatura_setor`)
   — mesma ideia, mas com um campo de busca no lugar da grade fixa de
   botões (17 setores é demais pra caber sem rolar a tela toda): a
   busca filtra os botões em tempo real por nome, sem diferenciar
   acento. Temperatura aceita negativos.
4. **Registro de água de abastecimento** (`/agua_abastecimento`) —
   botões grandes pro ponto de coleta (9 pontos fixos, mesmo padrão de
   etapa/setor), campos numéricos de pH e Cloro. O alerta indica
   especificamente qual dos dois está fora do padrão.
5. **Registro de temperatura de produto** (`/temp_produto`) — botões
   pra local e categoria, campo de texto pro nome do produto (com
   sugestões dos últimos produtos digitados), temperatura numérica. O
   limite de conformidade depende da categoria escolhida (Corte vs.
   Carne Moída), não é fixo. Sem limite de quantos registros por dia.
6. **Registro de temperatura de expedição** (`/temp_expedicao`) —
   botões pra local (4 câmaras/pontos), e o seletor de categoria
   aparece ou some dinamicamente dependendo do local escolhido ("Matéria
   Prima - Quebra de Gelo" não tem categoria). O limite depende da
   combinação local + categoria. Temperatura aceita negativos.
7. **Registro de monitoramento de peso** (`/peso_produto`) — dados do
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
8. **Painel** (`/dashboard`) — com um único tipo cadastrado, vai
   direto para o painel daquele tipo; com dois ou mais (como hoje),
   mostra uma visão combinada por padrão (cartões de contagem por tipo
   + tabela unificada), com um seletor para entrar no painel completo
   de cada tipo (filtros específicos, cartões de resumo, gráfico ao
   longo do tempo com pontos fora do padrão em vermelho — o painel de
   água de abastecimento usa dois eixos Y, um pra pH e outro pra
   Cloro, já que têm faixas e unidades diferentes — e tabela com
   destaque vermelho nas linhas fora do padrão). No painel de
   monitoramento de peso, cada ponto do gráfico é uma avaliação de
   produto (não uma pesagem individual), com o eixo Y mostrando o
   total de NCs daquela avaliação.
9. **Exportar Excel** — botão no painel que baixa um `.xlsx` com as
   colunas do tipo em questão, respeitando os filtros aplicados.
   Linhas fora do padrão vêm destacadas em vermelho na planilha. O
   monitoramento de peso gera duas abas: um resumo por avaliação de
   produto ("Peso Produto") e o detalhe de cada pesagem individual
   ("Peso Produto Detalhe"). Na visão combinada, "Exportar tudo" gera
   um único arquivo com uma aba por tipo (`/exportar?tipo=todos`,
   duas abas no caso do monitoramento de peso).

## Paleta de cores

| Cor | Hex | Uso |
|---|---|---|
| Navy | `#1F3864` | Cabeçalho, títulos, botão Salvar |
| Azul | `#2E75B6` | Botões de etapa, destaques primários |
| Amarelo | `#FFF2CC` | Fundo de avisos |
| Vermelho | `#C00000` | Destaque de registros fora do padrão |

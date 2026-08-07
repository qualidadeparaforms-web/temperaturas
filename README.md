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
outros tipos ficam documentadas junto do respectivo tipo.)

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
   registro cadastrado (hoje só "Temperatura de Processo"). Ao
   clicar, leva ao formulário daquele tipo.
2. **Registro de temperatura** (`/temperatura`) — botões grandes por
   etapa, campo numérico de temperatura, campo de responsável (com
   sugestões dos últimos nomes digitados) e botão "Salvar" grande.
   Mostra alerta de sucesso ou de "fora do padrão" imediatamente após
   salvar.
3. **Painel** (`/dashboard`) — com um único tipo cadastrado, vai
   direto para o painel de temperatura: filtros de período
   (dia/semana/mês/personalizado) e etapa, cartões de resumo, gráfico
   de temperatura ao longo do tempo por etapa (pontos fora do padrão
   aparecem em vermelho) e tabela com destaque vermelho nas linhas
   fora do padrão. Com dois ou mais tipos cadastrados, `/dashboard`
   passa a mostrar uma visão combinada (cartões de contagem por tipo +
   tabela unificada), com um seletor para entrar no painel específico
   de cada tipo.
4. **Exportar Excel** — botão no painel que baixa um `.xlsx` com as
   colunas Dia, Horário, Etapa, Temperatura, Responsável e Conforme
   (Sim/Não), respeitando os filtros aplicados. Linhas fora do padrão
   vêm destacadas em vermelho na planilha. Com múltiplos tipos, é
   possível exportar tudo num único arquivo com uma aba por tipo
   (`/exportar?tipo=todos`).

## Paleta de cores

| Cor | Hex | Uso |
|---|---|---|
| Navy | `#1F3864` | Cabeçalho, títulos, botão Salvar |
| Azul | `#2E75B6` | Botões de etapa, destaques primários |
| Amarelo | `#FFF2CC` | Fundo de avisos |
| Vermelho | `#C00000` | Destaque de registros fora do padrão |

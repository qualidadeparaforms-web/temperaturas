# Controle de Temperatura — Registro de Processo

Sistema web simples para digitalizar o registro de temperatura de
processo em uma indústria de alimentos (carnes). Pensado para uso em
tablets/celulares no chão de fábrica (tela de registro) e em
computador para acompanhamento (painel).

## Stack

- **Backend:** Python + Flask
- **Banco de dados:** SQLite (arquivo único)
- **Frontend:** HTML + Bootstrap 5 (botões grandes, poucos campos)
- **Gráficos:** Chart.js
- **Exportação:** Excel (.xlsx) via openpyxl
- **Deploy:** preparado para Render ou Railway

## Regras de negócio

| Etapa | Limite (conforme até) |
|---|---|
| Moídas | 4°C |
| Aparas, Bifes, Temperados, Embalagem, Selagem | 7°C |

Registros acima do limite mostram **"⚠️ Fora do padrão"** na hora, mas
são salvos normalmente — o sistema nunca bloqueia o registro, apenas
avisa.

## Estrutura do projeto

```
temperaturas/
├── app/
│   ├── __init__.py        # application factory
│   ├── extensions.py      # instância do SQLAlchemy
│   ├── models.py          # modelo RegistroTemperatura + regras de negócio
│   ├── routes/
│   │   ├── registro.py    # tela de registro (tablet)
│   │   ├── dashboard.py   # painel, API de dados e exportação Excel
│   │   └── backup.py      # endpoint HTTP protegido para disparar backup
│   ├── templates/
│   └── static/
├── backup.py               # script de backup (rodar via cron)
├── config.py
├── wsgi.py                 # ponto de entrada (gunicorn wsgi:app)
├── requirements.txt
├── Procfile                 # Render / Railway
├── render.yaml               # blueprint do Render (opcional)
├── railway.json               # config do Railway (opcional)
└── .python-version
```

## Rodando localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python wsgi.py
```

Acesse `http://localhost:5000` (tela de registro) e
`http://localhost:5000/dashboard` (painel). O banco `instance/temperaturas.db`
é criado automaticamente no primeiro acesso.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | chave de desenvolvimento | Troque em produção |
| `DATABASE_PATH` | `instance/temperaturas.db` | Caminho do arquivo SQLite |
| `BACKUP_DIR` | `backups/` | Pasta onde os backups são salvos |
| `BACKUP_MANTER_ULTIMOS` | `30` | Quantos backups recentes manter |
| `BACKUP_TOKEN` | (vazio) | Se definido, habilita `POST /backup/executar` |
| `BACKUP_S3_BUCKET` | (vazio) | Se definido, envia backups também para um bucket S3/compatível (requer `pip install boto3`) |
| `PORT` | `5000` | Porta usada por `wsgi.py` em execução direta |

## ⚠️ Atenção: persistência do SQLite na nuvem

Tanto Render quanto Railway usam **sistema de arquivos efêmero** por
padrão: a cada novo deploy (ou reinício do container), tudo que foi
gravado em disco — incluindo o arquivo `.db` — é apagado, a menos que
você configure um **disco/volume persistente**.

- **Render:** adicione um "Disk" ao serviço (recurso pago, a partir do
  plano Starter) e aponte `DATABASE_PATH`/`BACKUP_DIR` para dentro
  dele. O `render.yaml` incluso já faz isso (monta em `/var/data`).
- **Railway:** crie um "Volume" no serviço e aponte as mesmas
  variáveis para o caminho montado (ex.: `/data`).

Por isso a rotina de **backup automático** (próxima seção) é
importante mesmo com disco persistente — ela protege contra exclusão
acidental do disco, não apenas contra deploys.

## Backup automático

O script `backup.py`:
1. Copia o arquivo SQLite de forma segura (API de backup nativa do
   SQLite, funciona com o banco em uso).
2. Exporta os dados também em CSV.
3. Mantém apenas os últimos `BACKUP_MANTER_ULTIMOS` backups (rotação).
4. Se `BACKUP_S3_BUCKET` estiver definido, também envia os arquivos
   para um bucket S3 (ou compatível: Cloudflare R2, Backblaze B2etc.).

Rodar manualmente:

```bash
python backup.py
```

**Como agendar:**

- **Render:** crie um "Cron Job" separado no mesmo projeto, apontando
  para este repositório, com o comando `python backup.py`. Configure o
  mesmo `DATABASE_PATH`/`BACKUP_DIR` do serviço web.
- **Railway:** crie um serviço com "Cron Schedule" e o mesmo comando.
- **Qualquer host (alternativa via HTTP):** defina `BACKUP_TOKEN` e
  use um cron externo (ex. cron-job.org, GitHub Actions agendado) para
  chamar periodicamente:
  ```bash
  curl -X POST https://seu-app.onrender.com/backup/executar \
       -H "X-Backup-Token: SEU_TOKEN"
  ```

## Deploy

### Render
1. Suba este repositório no GitHub.
2. No Render, "New +" → "Blueprint" → selecione o repositório (usa o
   `render.yaml` incluso automaticamente), **ou** crie manualmente um
   "Web Service" com:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn wsgi:app`
3. Configure as variáveis de ambiente (veja tabela acima).
4. Adicione um Disk se quiser persistência (ver seção acima).

### Railway
1. Suba este repositório no GitHub.
2. No Railway, "New Project" → "Deploy from GitHub repo".
3. O Railway detecta o `Procfile`/`railway.json` e usa
   `gunicorn wsgi:app` como comando de start.
4. Adicione um Volume para persistência e configure as variáveis de
   ambiente.

## Telas

1. **Registro** (`/`) — botões grandes por etapa, campo numérico de
   temperatura, campo de responsável (com sugestões dos últimos nomes
   digitados) e botão "Salvar" grande. Mostra alerta de sucesso ou de
   "fora do padrão" imediatamente após salvar.
2. **Painel** (`/dashboard`) — filtros de período (dia/semana/mês/
   personalizado) e etapa, cartões de resumo, gráfico de temperatura
   ao longo do tempo por etapa (pontos fora do padrão aparecem em
   vermelho) e tabela com destaque vermelho nas linhas fora do padrão.
3. **Exportar Excel** — botão no painel que baixa um `.xlsx` com as
   colunas Dia, Horário, Etapa, Temperatura, Responsável e Conforme
   (Sim/Não), respeitando os filtros aplicados. Linhas fora do padrão
   vêm destacadas em vermelho na planilha.

## Paleta de cores

| Cor | Hex | Uso |
|---|---|---|
| Navy | `#1F3864` | Cabeçalho, títulos, botão Salvar |
| Azul | `#2E75B6` | Botões de etapa, destaques primários |
| Amarelo | `#FFF2CC` | Fundo de avisos |
| Vermelho | `#C00000` | Destaque de registros fora do padrão |

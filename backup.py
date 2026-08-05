"""
Rotina de backup do banco de dados de registros de temperatura.

USO MANUAL:
    python backup.py

O script:
1. Faz uma cópia binária segura do arquivo SQLite (usando a API de
   backup nativa do SQLite, que funciona mesmo com o banco em uso).
2. Exporta os dados também em CSV (mais legível/portável, fácil de
   abrir em qualquer planilha).
3. Mantém apenas os últimos N backups (padrão: 30 — ver
   BACKUP_MANTER_ULTIMOS em config.py) para não acumular espaço em
   disco indefinidamente.
4. Opcionalmente, envia os arquivos para um bucket S3 (ou compatível,
   como Cloudflare R2 / Backblaze B2) se a variável de ambiente
   BACKUP_S3_BUCKET estiver definida (e as credenciais AWS/boto3
   configuradas). Requer `pip install boto3`.

COMO AGENDAR:
- Render: crie um "Cron Job" apontando para este repositório com o
  comando `python backup.py`, agendado (ex.: diariamente às 23h).
- Railway: crie um serviço com "Cron Schedule" configurado e o mesmo
  comando de início.
- Alternativa (qualquer host): use o endpoint HTTP protegido
  POST /backup/executar (ver app/routes/backup.py) chamado por um
  serviço externo de cron (ex.: cron-job.org, GitHub Actions
  agendado) enviando o cabeçalho X-Backup-Token.
- Alternativa sem Cron Job nenhum: defina BACKUP_AUTOMATICO=true e a
  própria aplicação roda esta rotina periodicamente em segundo plano
  (ver app/__init__.py). Combinado com BACKUP_S3_BUCKET, isso permite
  rodar em planos SEM disco persistente (ex.: Render free): a cada
  novo deploy o banco local começa vazio, mas é restaurado
  automaticamente a partir do último backup no S3 (ver
  `restaurar_ultimo_backup`), então os dados não se perdem — apenas
  os registros feitos depois do último backup ficam em risco.
"""

import csv
import os
import sqlite3
from datetime import datetime

from config import Config


def _backup_sqlite(origem: str, destino_dir: str, timestamp: str) -> str:
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, f"temperaturas_{timestamp}.db")
    con_origem = sqlite3.connect(origem)
    con_destino = sqlite3.connect(destino)
    with con_destino:
        con_origem.backup(con_destino)
    con_origem.close()
    con_destino.close()
    return destino


def _exportar_csv(origem: str, destino_dir: str, timestamp: str) -> str:
    destino = os.path.join(destino_dir, f"temperaturas_{timestamp}.csv")
    con = sqlite3.connect(origem)
    cur = con.cursor()
    cur.execute(
        "SELECT id, data, horario, etapa, temperatura, responsavel "
        "FROM registros_temperatura ORDER BY id"
    )
    linhas = cur.fetchall()
    con.close()

    with open(destino, "w", newline="", encoding="utf-8") as arquivo:
        writer = csv.writer(arquivo)
        writer.writerow(["id", "data", "horario", "etapa", "temperatura", "responsavel"])
        writer.writerows(linhas)
    return destino


def _limpar_antigos(destino_dir: str, prefixo: str, manter: int) -> None:
    arquivos = sorted(
        (f for f in os.listdir(destino_dir) if f.startswith(prefixo)),
        reverse=True,
    )
    for antigo in arquivos[manter:]:
        os.remove(os.path.join(destino_dir, antigo))


PREFIXO_S3 = "backups-temperaturas/"


def _cliente_s3():
    """Retorna um cliente boto3, ou None se a biblioteca não estiver instalada."""
    try:
        import boto3
    except ImportError:
        return None
    return boto3.client("s3")


def _upload_s3(caminho_arquivo: str) -> None:
    bucket = os.environ.get("BACKUP_S3_BUCKET")
    if not bucket:
        return

    s3 = _cliente_s3()
    if s3 is None:
        print("boto3 não instalado — pulando upload para S3 (pip install boto3).")
        return

    chave = f"{PREFIXO_S3}{os.path.basename(caminho_arquivo)}"
    s3.upload_file(caminho_arquivo, bucket, chave)
    print(f"Backup enviado para s3://{bucket}/{chave}")


def restaurar_ultimo_backup() -> bool:
    """Restaura o backup .db mais recente do S3 para DATABASE_PATH.

    Usado na inicialização da aplicação (ver app/__init__.py) quando o
    arquivo SQLite local não existe — situação comum em hospedagens
    com disco efêmero (ex.: Render/Railway sem disco/volume
    persistente) logo após um novo deploy. Assim os dados sobrevivem
    entre deploys mesmo sem pagar por armazenamento persistente,
    ficando em risco apenas os registros feitos após o último backup.

    Retorna True se algum backup foi restaurado.
    """
    bucket = os.environ.get("BACKUP_S3_BUCKET")
    if not bucket:
        return False

    s3 = _cliente_s3()
    if s3 is None:
        print("boto3 não instalado — não é possível restaurar backup do S3.")
        return False

    try:
        resposta = s3.list_objects_v2(Bucket=bucket, Prefix=PREFIXO_S3)
    except Exception as exc:  # depende de rede/credenciais — nunca deve travar o boot
        print(f"Não foi possível consultar backups no S3: {exc}")
        return False

    candidatos = [obj for obj in resposta.get("Contents", []) if obj["Key"].endswith(".db")]
    if not candidatos:
        print("Nenhum backup .db encontrado no S3 para restaurar.")
        return False

    mais_recente = max(candidatos, key=lambda obj: obj["LastModified"])
    destino = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    try:
        s3.download_file(bucket, mais_recente["Key"], destino)
    except Exception as exc:
        print(f"Falha ao baixar backup do S3: {exc}")
        return False

    print(f"Banco restaurado a partir de s3://{bucket}/{mais_recente['Key']}")
    return True


def executar_backup() -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    origem = Config.DATABASE_PATH
    destino_dir = Config.BACKUP_DIR

    if not os.path.exists(origem):
        mensagem = f"Banco de dados não encontrado em {origem} — nada para fazer backup."
        print(mensagem)
        return {"ok": False, "mensagem": mensagem}

    caminho_db = _backup_sqlite(origem, destino_dir, timestamp)
    caminho_csv = _exportar_csv(origem, destino_dir, timestamp)

    _limpar_antigos(destino_dir, "temperaturas_", manter=Config.BACKUP_MANTER_ULTIMOS)

    _upload_s3(caminho_db)
    _upload_s3(caminho_csv)

    mensagem = f"Backup concluído: {caminho_db} e {caminho_csv}"
    print(mensagem)
    return {"ok": True, "mensagem": mensagem, "arquivos": [caminho_db, caminho_csv]}


if __name__ == "__main__":
    executar_backup()

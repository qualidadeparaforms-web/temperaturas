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


def _upload_s3(caminho_arquivo: str) -> None:
    bucket = os.environ.get("BACKUP_S3_BUCKET")
    if not bucket:
        return
    try:
        import boto3
    except ImportError:
        print("boto3 não instalado — pulando upload para S3 (pip install boto3).")
        return

    s3 = boto3.client("s3")
    chave = f"backups-temperaturas/{os.path.basename(caminho_arquivo)}"
    s3.upload_file(caminho_arquivo, bucket, chave)
    print(f"Backup enviado para s3://{bucket}/{chave}")


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

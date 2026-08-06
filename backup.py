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
   BACKUP_S3_BUCKET estiver definida (e AWS_ACCESS_KEY_ID /
   AWS_SECRET_ACCESS_KEY configuradas — e BACKUP_S3_ENDPOINT_URL para
   serviços compatíveis que não sejam a AWS). boto3 já vem no
   requirements.txt.

COMO AGENDAR:
- Automático a cada registro salvo (padrão, sem configurar nada além
  de BACKUP_S3_BUCKET): toda vez que alguém salva uma temperatura em
  /registrar, um backup roda em segundo plano (ver
  app/routes/registro.py, `_agendar_backup_apos_registro`). É o que
  protege o plano Free do Render, cujo disco é apagado toda vez que o
  serviço "dorme" por inatividade (~15 min sem acesso) — não dá pra
  esperar um ciclo periódico de horas em horas nesse caso.
- Render/Railway com disco persistente: BACKUP_AUTOMATICO=true roda
  esta rotina periodicamente em segundo plano dentro do próprio app
  (ver app/__init__.py), a cada BACKUP_INTERVALO_HORAS — suficiente
  quando o disco já não é apagado sozinho.
- Cron Job dedicado: Render/Railway "Cron Job" / "Cron Schedule"
  apontando para este repositório com o comando `python backup.py`.
- Alternativa via HTTP (qualquer host): endpoint protegido
  POST /backup/executar (ver app/routes/backup.py) chamado por um
  serviço externo de cron (ex.: cron-job.org, GitHub Actions
  agendado) enviando o cabeçalho X-Backup-Token.

Em qualquer um desses casos, se BACKUP_S3_BUCKET estiver configurado
e o app subir com o banco local vazio (disco efêmero recém-criado),
o último backup é restaurado sozinho antes de criar um banco novo —
ver `restaurar_ultimo_backup`, chamada em app/__init__.py.
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
    """Retorna um cliente boto3, ou None se a biblioteca não estiver instalada.

    Suporta serviços compatíveis com S3 além da AWS (ex.: Cloudflare
    R2, Backblaze B2) via BACKUP_S3_ENDPOINT_URL. A AWS de fato não
    precisa dessa variável — só os compatíveis.
    """
    try:
        import boto3
    except ImportError:
        return None

    endpoint = os.environ.get("BACKUP_S3_ENDPOINT_URL")
    kwargs = {}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        # R2 e outros compatíveis costumam usar "auto" como região.
        kwargs["region_name"] = os.environ.get("AWS_DEFAULT_REGION", "auto")
    return boto3.client("s3", **kwargs)


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


def _podar_s3_antigos(manter: int) -> None:
    """Remove do bucket os backups mais antigos, mantendo só os últimos.

    Sem isso, rodar um backup a cada registro salvo (ver
    app/routes/registro.py) acumularia um objeto novo no bucket a cada
    registro, para sempre.
    """
    bucket = os.environ.get("BACKUP_S3_BUCKET")
    if not bucket:
        return
    s3 = _cliente_s3()
    if s3 is None:
        return

    try:
        resposta = s3.list_objects_v2(Bucket=bucket, Prefix=PREFIXO_S3)
    except Exception as exc:
        print(f"Não foi possível listar backups no S3 para poda: {exc}")
        return

    objetos = sorted(resposta.get("Contents", []), key=lambda obj: obj["LastModified"], reverse=True)
    for antigo in objetos[manter:]:
        try:
            s3.delete_object(Bucket=bucket, Key=antigo["Key"])
        except Exception as exc:
            print(f"Falha ao remover backup antigo do S3 ({antigo['Key']}): {exc}")


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
    # Microssegundos incluídos de propósito: com backup disparado a cada
    # registro salvo, dois backups podem cair no mesmo segundo e colidir
    # no mesmo nome de arquivo (sobrescrevendo um ao outro) sem isso.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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
    _podar_s3_antigos(manter=Config.BACKUP_MANTER_ULTIMOS)

    mensagem = f"Backup concluído: {caminho_db} e {caminho_csv}"
    print(mensagem)
    return {"ok": True, "mensagem": mensagem, "arquivos": [caminho_db, caminho_csv]}


if __name__ == "__main__":
    executar_backup()

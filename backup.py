"""
Rotina de backup do banco de dados (todos os tipos de registro
cadastrados em app/tipos — hoje só "Temperatura de Processo").

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
  de BACKUP_S3_BUCKET): toda vez que alguém salva um registro (de
  qualquer tipo), um backup roda em segundo plano (ver
  app/backup_utils.py, `agendar_backup_apos_registro`). É o que
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


def _exportar_csv(origem: str, destino_dir: str, timestamp: str) -> list:
    """Exporta um CSV por tipo de registro cadastrado (ver app/tipos) —
    hoje só "temperatura", mas cresce sozinho conforme novos tipos
    forem adicionados ao registro (nenhuma mudança necessária aqui).

    Cada tipo é isolado num try/except: se um tipo falhar (ex.:
    esquema desatualizado numa tabela — o app já se autocorrige no
    boot, ver _migrar_colunas_faltantes em app/__init__.py, mas essa
    blindagem aqui é a segunda linha de defesa), os demais tipos e o
    backup binário do banco inteiro (chamado antes deste, em
    executar_backup) não são afetados. Antes desta blindagem, uma
    falha em um único tipo interrompia a função inteira e derrubava o
    backup do zero — inclusive o upload do .db, que roda depois desta
    chamada.
    """
    from app.tipos import TIPOS_REGISTRO

    con = sqlite3.connect(origem)
    cur = con.cursor()
    caminhos = []
    for tipo in TIPOS_REGISTRO:
        try:
            # tipo.tabela/colunas_backup vêm do código-fonte (TipoRegistro),
            # nunca de entrada externa — seguro compor a query assim.
            colunas = tipo.colunas_backup
            cur.execute(f"SELECT {', '.join(colunas)} FROM {tipo.tabela} ORDER BY id")
            linhas = cur.fetchall()

            destino = os.path.join(destino_dir, f"temperaturas_{timestamp}_{tipo.slug}.csv")
            with open(destino, "w", newline="", encoding="utf-8") as arquivo:
                writer = csv.writer(arquivo)
                writer.writerow(colunas)
                writer.writerows(linhas)
        except Exception as exc:
            print(f"Falha ao exportar CSV do tipo '{tipo.slug}': {exc} (outros tipos e o backup binário seguem normalmente)")
            continue
        caminhos.append(destino)
    con.close()
    return caminhos


def _timestamp_do_nome(nome_arquivo: str) -> str:
    """Extrai o timestamp (data_hora_microssegundos) de um nome de
    backup, seja o .db (`temperaturas_<ts>.db`) ou um .csv por tipo
    (`temperaturas_<ts>_<slug>.csv`) — usado para agrupar os arquivos
    de uma mesma rodada de backup na hora de podar os antigos.
    """
    base = nome_arquivo.rsplit(".", 1)[0]
    partes = base.split("_")
    return "_".join(partes[1:4])  # data, hora, microssegundos


def _limpar_antigos(destino_dir: str, prefixo: str, manter: int) -> None:
    """Mantém só as últimas `manter` RODADAS de backup (não arquivos).

    Uma rodada gera vários arquivos (1 .db + 1 .csv por tipo
    cadastrado) — contar arquivo por arquivo encolheria a retenção
    real conforme mais tipos forem adicionados.
    """
    arquivos = sorted(
        (f for f in os.listdir(destino_dir) if f.startswith(prefixo)),
        reverse=True,
    )
    timestamps_em_ordem = list(dict.fromkeys(_timestamp_do_nome(f) for f in arquivos))
    manter_timestamps = set(timestamps_em_ordem[:manter])

    for arquivo in arquivos:
        if _timestamp_do_nome(arquivo) not in manter_timestamps:
            os.remove(os.path.join(destino_dir, arquivo))


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
    """Remove do bucket as RODADAS de backup mais antigas, mantendo só
    as últimas (mesma lógica de _limpar_antigos, mas no bucket).

    Sem isso, rodar um backup a cada registro salvo (ver
    app/backup_utils.py) acumularia objetos novos no bucket a cada
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

    objetos = resposta.get("Contents", [])
    objetos_ordenados = sorted(objetos, key=lambda obj: obj["LastModified"], reverse=True)
    timestamps_em_ordem = list(
        dict.fromkeys(_timestamp_do_nome(obj["Key"].rsplit("/", 1)[-1]) for obj in objetos_ordenados)
    )
    manter_timestamps = set(timestamps_em_ordem[:manter])

    for obj in objetos_ordenados:
        nome = obj["Key"].rsplit("/", 1)[-1]
        if _timestamp_do_nome(nome) not in manter_timestamps:
            try:
                s3.delete_object(Bucket=bucket, Key=obj["Key"])
            except Exception as exc:
                print(f"Falha ao remover backup antigo do S3 ({obj['Key']}): {exc}")


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
    caminhos_csv = _exportar_csv(origem, destino_dir, timestamp)

    _limpar_antigos(destino_dir, "temperaturas_", manter=Config.BACKUP_MANTER_ULTIMOS)

    _upload_s3(caminho_db)
    for caminho_csv in caminhos_csv:
        _upload_s3(caminho_csv)
    _podar_s3_antigos(manter=Config.BACKUP_MANTER_ULTIMOS)

    arquivos = [caminho_db] + caminhos_csv
    mensagem = f"Backup concluído: {', '.join(arquivos)}"
    print(mensagem)
    return {"ok": True, "mensagem": mensagem, "arquivos": arquivos}


if __name__ == "__main__":
    executar_backup()

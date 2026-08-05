import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuração da aplicação.

    Todos os valores podem ser sobrescritos por variáveis de ambiente,
    o que permite apontar o banco de dados para um disco persistente
    quando a aplicação estiver hospedada na nuvem (ver README.md).
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-troque-esta-chave-em-producao")

    # Caminho do arquivo SQLite. Em produção (Render/Railway) defina
    # DATABASE_PATH apontando para um disco/volume persistente,
    # caso contrário o banco é perdido a cada novo deploy.
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "instance", "temperaturas.db")
    )
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Diretório onde os backups (arquivo .db + .csv) são gravados.
    BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(BASE_DIR, "backups"))

    # Quantidade de backups recentes a manter no disco (rotação).
    BACKUP_MANTER_ULTIMOS = int(os.environ.get("BACKUP_MANTER_ULTIMOS", "30"))

    # Token para proteger o endpoint HTTP /backup/executar.
    # Se não for definido, o endpoint fica desabilitado.
    BACKUP_TOKEN = os.environ.get("BACKUP_TOKEN")

    # Se "true", a própria aplicação roda o backup periodicamente em
    # segundo plano (sem precisar de um Cron Job separado). Útil em
    # planos sem disco persistente, combinado com BACKUP_S3_BUCKET:
    # o banco é restaurado automaticamente do S3 quando o arquivo
    # local não existe (ex.: após um redeploy em disco efêmero).
    BACKUP_AUTOMATICO = os.environ.get("BACKUP_AUTOMATICO", "false").lower() in (
        "1",
        "true",
        "sim",
        "yes",
    )
    BACKUP_INTERVALO_HORAS = float(os.environ.get("BACKUP_INTERVALO_HORAS", "6"))

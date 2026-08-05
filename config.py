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

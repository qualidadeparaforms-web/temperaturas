import os
import threading
import time

from flask import Flask

from config import Config
from app.extensions import db


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Garante que as pastas do banco e de backup existam.
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)

    _restaurar_banco_se_necessario(app)

    db.init_app(app)

    from app.routes.admin import admin_bp
    from app.routes.backup import backup_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.home import home_bp
    from app.tipos import blueprints_registrados

    app.register_blueprint(home_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(admin_bp)
    for blueprint in blueprints_registrados():
        app.register_blueprint(blueprint)

    with app.app_context():
        db.create_all()
        _migrar_colunas_faltantes(app)

    _iniciar_backup_automatico(app)

    return app


def _restaurar_banco_se_necessario(app: Flask) -> None:
    """Restaura o último backup do S3 se o SQLite local não existir.

    Cobre o cenário de disco efêmero (hospedagens sem disco/volume
    persistente): a cada novo deploy o arquivo local começa vazio,
    então tentamos recuperar o backup mais recente antes de criar um
    banco novo do zero. Requer BACKUP_S3_BUCKET configurado — sem
    isso, esta função não faz nada.
    """
    if os.path.exists(app.config["DATABASE_PATH"]):
        return
    if not os.environ.get("BACKUP_S3_BUCKET"):
        return
    try:
        from backup import restaurar_ultimo_backup

        restaurar_ultimo_backup()
    except Exception as exc:  # a restauração nunca deve impedir a aplicação de subir
        app.logger.warning("Falha ao tentar restaurar backup do S3: %s", exc)


def _migrar_colunas_faltantes(app: Flask) -> None:
    """Autocorrige o esquema de tabelas já existentes pra bater com os
    modelos Python atuais — duas direções.

    db.create_all() só CRIA tabelas que ainda não existem — nunca
    altera uma tabela já existente. Então, quando um tipo já
    implantado tem seus campos alterados (ex.: PAC 06-E trocou
    "gramatura_nominal" por "gramatura_minima"/"gramatura_maxima"
    depois do primeiro deploy), o banco em produção fica com o
    esquema antigo:

    1. Coluna que o modelo tem e a tabela não tem — todo INSERT/SELECT
       que toca essa coluna falha com "no such column" (inclusive
       dentro do backup automático, que ficava interrompido antes de
       chegar no upload do .db pro S3 — ver _exportar_csv em
       backup.py, agora blindada por tipo como segunda linha de
       defesa). Corrige com ALTER TABLE ADD COLUMN.
    2. Coluna que a tabela tem mas o modelo não usa mais (o campo
       antigo "órfão", ex.: gramatura_nominal) — se essa coluna for
       NOT NULL, todo INSERT novo passa a falhar também, porque o
       INSERT gerado pelo SQLAlchemy nem menciona essa coluna (ela não
       existe mais no modelo) e o SQLite exige um valor pra ela.
       Corrige removendo a coluna órfã (ALTER TABLE DROP COLUMN,
       suportado desde o SQLite 3.35+).

    Genérico de propósito: não lista tipo por tipo, então cobre
    qualquer tipo (atual ou futuro) que tenha campos alterados depois
    de já estar em produção — só rodar `git push` e o próximo boot se
    autocorrige, sem precisar mexer no banco manualmente.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    tabelas_existentes = set(inspector.get_table_names())

    for tabela in db.metadata.tables.values():
        if tabela.name not in tabelas_existentes:
            continue  # tabela nova — db.create_all() já cuidou dela

        nomes_atuais = {coluna["name"] for coluna in inspector.get_columns(tabela.name)}
        nomes_modelo = {coluna.name for coluna in tabela.columns}

        for coluna in tabela.columns:
            if coluna.name in nomes_atuais:
                continue
            tipo_sql = coluna.type.compile(dialect=db.engine.dialect)
            db.session.execute(text(f'ALTER TABLE "{tabela.name}" ADD COLUMN "{coluna.name}" {tipo_sql}'))
            app.logger.warning(
                "Migração automática: coluna '%s' adicionada à tabela '%s' "
                "(linhas existentes ficam com valor nulo nessa coluna).",
                coluna.name,
                tabela.name,
            )

        for nome_orfao in nomes_atuais - nomes_modelo:
            try:
                db.session.execute(text(f'ALTER TABLE "{tabela.name}" DROP COLUMN "{nome_orfao}"'))
                app.logger.warning(
                    "Migração automática: coluna órfã '%s' removida da tabela '%s' "
                    "(não existe mais no modelo).",
                    nome_orfao,
                    tabela.name,
                )
            except Exception as exc:
                app.logger.warning(
                    "Não foi possível remover a coluna órfã '%s' da tabela '%s': %s. "
                    "Se ela tiver NOT NULL, inserts novos nessa tabela podem falhar "
                    "até isso ser corrigido manualmente.",
                    nome_orfao,
                    tabela.name,
                    exc,
                )
    db.session.commit()


def _iniciar_backup_automatico(app: Flask) -> None:
    """Inicia uma thread em segundo plano que roda o backup periodicamente.

    Alternativa sem custo extra a um Cron Job pago — habilitada via
    BACKUP_AUTOMATICO=true. Especialmente útil em planos sem disco
    persistente: combinado com BACKUP_S3_BUCKET, os dados ficam
    protegidos no S3 e são restaurados automaticamente no próximo
    deploy (ver _restaurar_banco_se_necessario).
    """
    if not app.config.get("BACKUP_AUTOMATICO"):
        return

    # Evita duplicar a thread quando o reloader do Flask (modo debug)
    # sobe dois processos para o mesmo comando.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    intervalo_segundos = max(app.config.get("BACKUP_INTERVALO_HORAS", 6), 0.1) * 3600

    def loop_backup():
        from backup import executar_backup

        while True:
            try:
                executar_backup()
            except Exception as exc:
                app.logger.warning("Falha na rotina de backup automático: %s", exc)
            time.sleep(intervalo_segundos)

    threading.Thread(target=loop_backup, daemon=True, name="backup-automatico").start()

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

    from app.routes.registro import registro_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.backup import backup_bp

    app.register_blueprint(registro_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(backup_bp)

    with app.app_context():
        db.create_all()

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

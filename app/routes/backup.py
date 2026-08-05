from flask import Blueprint, current_app, jsonify, request

backup_bp = Blueprint("backup", __name__)


@backup_bp.route("/backup/executar", methods=["POST"])
def executar():
    """Endpoint protegido para disparar o backup via HTTP.

    Útil em hospedagens sem suporte nativo a "cron job" — um serviço
    externo de agendamento (ex.: cron-job.org, GitHub Actions
    agendado) pode chamar esta rota periodicamente enviando o
    cabeçalho `X-Backup-Token` com o valor da variável de ambiente
    BACKUP_TOKEN.
    """
    token_configurado = current_app.config.get("BACKUP_TOKEN")
    if not token_configurado:
        return jsonify({"ok": False, "mensagem": "Backup via HTTP não configurado (defina BACKUP_TOKEN)."}), 503

    token_recebido = request.headers.get("X-Backup-Token")
    if token_recebido != token_configurado:
        return jsonify({"ok": False, "mensagem": "Token inválido."}), 401

    # Import tardio para evitar dependência circular na inicialização da app.
    from backup import executar_backup

    resultado = executar_backup()
    status = 200 if resultado.get("ok") else 500
    return jsonify(resultado), status

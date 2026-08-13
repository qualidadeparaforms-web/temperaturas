import os

from flask import Blueprint, current_app, render_template, request

from app.extensions import db

admin_bp = Blueprint("admin", __name__)


def _contagem_por_tabela() -> dict:
    """Conta as linhas de cada tabela conhecida pelo SQLAlchemy — sem
    precisar listar tipo por tipo, então funciona sozinho pra
    qualquer tipo novo que for adicionado no futuro (inclusive
    tabelas "extras" como verificacoes_rt, que não aparecem em
    TIPOS_REGISTRO)."""
    contagens = {}
    for nome_tabela in db.metadata.tables:
        try:
            resultado = db.session.execute(db.text(f"SELECT COUNT(*) FROM {nome_tabela}")).scalar()
            contagens[nome_tabela] = resultado or 0
        except Exception:
            contagens[nome_tabela] = None
    return contagens


def _token_valido() -> bool:
    token_configurado = current_app.config.get("RESET_TOKEN")
    if not token_configurado:
        return False
    token_recebido = request.values.get("token")
    return token_recebido == token_configurado


@admin_bp.route("/admin/resetar", methods=["GET"])
def resetar_confirmar():
    """Tela de confirmação — mostra quantos registros existem hoje em
    cada tabela antes de apagar, e só libera o botão depois de digitar
    a frase de confirmação (ver script no template)."""
    if not current_app.config.get("RESET_TOKEN"):
        return "Reset não configurado (defina RESET_TOKEN nas variáveis de ambiente).", 503
    if not _token_valido():
        return "Token inválido ou ausente. Acesse com ?token=SEU_TOKEN na URL.", 401

    contagens = _contagem_por_tabela()
    total = sum(v for v in contagens.values() if v is not None)
    return render_template(
        "admin_resetar.html",
        contagens=contagens,
        total=total,
        token=request.values.get("token"),
    )


@admin_bp.route("/admin/resetar", methods=["POST"])
def resetar_confirmado():
    """Apaga TODOS os registros de TODOS os tipos (drop_all +
    create_all — recria as tabelas vazias) e, na sequência, dispara um
    backup imediatamente. O backup logo depois é essencial: sem ele, o
    último backup no S3 continuaria com os dados antigos, e um
    'acordar' do Render free (disco apagado) restauraria justamente o
    que acabou de ser apagado."""
    if not current_app.config.get("RESET_TOKEN"):
        return "Reset não configurado (defina RESET_TOKEN nas variáveis de ambiente).", 503
    if not _token_valido():
        return "Token inválido ou ausente.", 401

    contagens_antes = _contagem_por_tabela()
    total_antes = sum(v for v in contagens_antes.values() if v is not None)

    db.session.remove()
    db.drop_all()
    db.create_all()

    resultado_backup = {"ok": False, "mensagem": "BACKUP_S3_BUCKET não configurado — backup não disparado."}
    if os.environ.get("BACKUP_S3_BUCKET"):
        from backup import executar_backup

        resultado_backup = executar_backup()

    return render_template(
        "admin_resetado.html",
        total_antes=total_antes,
        backup_ok=resultado_backup.get("ok"),
        backup_mensagem=resultado_backup.get("mensagem"),
    )

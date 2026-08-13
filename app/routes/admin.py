import json
import os
import re
from datetime import date, datetime, time

from flask import Blueprint, Response, current_app, render_template, request, send_file

from app.extensions import db

admin_bp = Blueprint("admin", __name__)

PADRAO_NOME_BACKUP_PRE_RESET = re.compile(r"^pre_reset_\d{8}_\d{6}\.json$")


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


def _nome_amigavel_tabela(nome_tabela: str) -> str:
    """Traduz o nome da tabela SQL pro nome exibido no menu (ex.:
    "registros_temperatura" -> "Temperatura de Processo"). Cobre
    também as tabelas auxiliares que não têm um TipoRegistro próprio
    (pesagens individuais, verificações RT)."""
    from app.tipos import TIPOS_REGISTRO

    for tipo in TIPOS_REGISTRO:
        if tipo.tabela == nome_tabela:
            return tipo.nome

    nomes_extras = {
        "pesagens_individuais": "Pesagens individuais (PAC 06-D)",
        "pesagens_individuais_gramatura": "Pesagens individuais (PAC 06-E)",
        "verificacoes_rt": "Verificações RT (PAC 17)",
    }
    return nomes_extras.get(nome_tabela, nome_tabela)


def _serializar_valor(valor):
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    return valor


def _dump_json_completo() -> dict:
    """Monta um dump com TODAS as linhas de TODAS as tabelas
    conhecidas pelo SQLAlchemy — nome da tabela -> lista de dicts (uma
    por linha). Genérico via db.metadata.tables, cobre qualquer tipo
    (atual ou futuro) sem precisar listar um por um."""
    dump = {}
    for nome_tabela in db.metadata.tables:
        try:
            resultado = db.session.execute(db.text(f"SELECT * FROM {nome_tabela}"))
            colunas = list(resultado.keys())
            linhas = [
                {coluna: _serializar_valor(valor) for coluna, valor in zip(colunas, linha)}
                for linha in resultado
            ]
            dump[nome_tabela] = linhas
        except Exception as exc:
            dump[nome_tabela] = {"erro_ao_exportar": str(exc)}
    return dump


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
    nomes_amigaveis = {tabela: _nome_amigavel_tabela(tabela) for tabela in contagens}
    return render_template(
        "admin_resetar.html",
        contagens=contagens,
        nomes_amigaveis=nomes_amigaveis,
        total=total,
        token=request.values.get("token"),
    )


@admin_bp.route("/admin/resetar/preview-json", methods=["GET"])
def resetar_preview_json():
    """Baixa um dump JSON com os dados ATUAIS, sem apagar nada — pra
    quem quiser conferir/guardar antes de decidir se vai mesmo
    apagar."""
    if not current_app.config.get("RESET_TOKEN"):
        return "Reset não configurado (defina RESET_TOKEN nas variáveis de ambiente).", 503
    if not _token_valido():
        return "Token inválido ou ausente.", 401

    dump = _dump_json_completo()
    conteudo = json.dumps(dump, ensure_ascii=False, indent=2)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return Response(
        conteudo,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="preview_{timestamp}.json"'},
    )


@admin_bp.route("/admin/resetar", methods=["POST"])
def resetar_confirmado():
    """Apaga TODOS os registros de TODOS os tipos (drop_all +
    create_all — recria as tabelas vazias, sem mexer no esquema/código).

    Duas camadas de segurança antes de apagar:
    1. Salva um dump JSON completo dos dados atuais em BACKUP_DIR (e
       envia pro S3, se configurado) — pra consulta posterior, mesmo
       depois do reset. Nome fixo "pre_reset_<timestamp>.json", fora
       do padrão "temperaturas_" usado pelos backups de rotina, então
       a limpeza automática de backups antigos não o apaga sozinho.
    2. Depois de apagar, dispara um backup "normal" na hora — sem
       isso, o último backup no S3 continuaria com os dados antigos, e
       um 'acordar' do Render free (disco apagado) restauraria
       justamente o que acabou de ser apagado.
    """
    if not current_app.config.get("RESET_TOKEN"):
        return "Reset não configurado (defina RESET_TOKEN nas variáveis de ambiente).", 503
    if not _token_valido():
        return "Token inválido ou ausente.", 401

    contagens_antes = _contagem_por_tabela()
    total_antes = sum(v for v in contagens_antes.values() if v is not None)
    nomes_amigaveis = {tabela: _nome_amigavel_tabela(tabela) for tabela in contagens_antes}

    # 1) Backup dos dados atuais em JSON, ANTES de apagar qualquer coisa.
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nome_arquivo_backup = f"pre_reset_{timestamp}.json"
    caminho_backup = os.path.join(current_app.config["BACKUP_DIR"], nome_arquivo_backup)
    dump = _dump_json_completo()
    with open(caminho_backup, "w", encoding="utf-8") as arquivo:
        json.dump(dump, arquivo, ensure_ascii=False, indent=2)

    backup_json_enviado_s3 = False
    if os.environ.get("BACKUP_S3_BUCKET"):
        try:
            from backup import _upload_s3

            _upload_s3(caminho_backup)
            backup_json_enviado_s3 = True
        except Exception as exc:
            current_app.logger.warning("Falha ao enviar backup pré-reset (JSON) pro S3: %s", exc)

    # 2) Apaga tudo e recria o esquema vazio.
    db.session.remove()
    db.drop_all()
    db.create_all()

    # 3) Backup "normal" pós-reset, pra não deixar o último backup de
    #    rotina desatualizado (ver docstring).
    resultado_backup = {"ok": False, "mensagem": "BACKUP_S3_BUCKET não configurado — backup não disparado."}
    if os.environ.get("BACKUP_S3_BUCKET"):
        from backup import executar_backup

        resultado_backup = executar_backup()

    return render_template(
        "admin_resetado.html",
        total_antes=total_antes,
        contagens_antes=contagens_antes,
        nomes_amigaveis=nomes_amigaveis,
        backup_ok=resultado_backup.get("ok"),
        backup_mensagem=resultado_backup.get("mensagem"),
        nome_arquivo_backup=nome_arquivo_backup,
        backup_json_enviado_s3=backup_json_enviado_s3,
        token=request.values.get("token"),
    )


@admin_bp.route("/admin/resetar/backup/<nome_arquivo>", methods=["GET"])
def baixar_backup_pre_reset(nome_arquivo):
    """Baixa um dos dumps JSON salvos antes de um reset anterior."""
    if not current_app.config.get("RESET_TOKEN"):
        return "Reset não configurado (defina RESET_TOKEN nas variáveis de ambiente).", 503
    if not _token_valido():
        return "Token inválido ou ausente.", 401

    # Só nomes no formato esperado — evita qualquer tentativa de
    # acessar outro arquivo do servidor via o nome na URL.
    if not PADRAO_NOME_BACKUP_PRE_RESET.fullmatch(nome_arquivo):
        return "Nome de arquivo inválido.", 400

    caminho = os.path.join(current_app.config["BACKUP_DIR"], nome_arquivo)
    if not os.path.exists(caminho):
        return "Arquivo não encontrado no disco local (pode ter sido apagado num redeploy — confira no S3/B2).", 404

    return send_file(caminho, as_attachment=True, download_name=nome_arquivo, mimetype="application/json")

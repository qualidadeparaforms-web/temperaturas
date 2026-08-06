import os
import threading
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import ETAPAS, RegistroTemperatura

registro_bp = Blueprint("registro", __name__)


def _agendar_backup_apos_registro() -> None:
    """Dispara um backup em segundo plano logo após salvar um registro.

    Importante em hospedagens de plano gratuito (ex.: Render Free):
    o disco local é apagado toda vez que o serviço "dorme" por
    inatividade (~15 min sem acesso), não só em redeploys. Fazer o
    backup na hora, em vez de esperar um ciclo periódico, é o que
    garante que o registro sobreviva a esse "sono". Só roda quando
    BACKUP_S3_BUCKET está configurado — sem isso, um backup só local
    não sobrevive ao mesmo apagão.
    """
    if not os.environ.get("BACKUP_S3_BUCKET"):
        return

    def _rodar():
        try:
            from backup import executar_backup

            executar_backup()
        except Exception as exc:  # nunca deve derrubar a resposta ao usuário
            print(f"Falha ao fazer backup após o registro: {exc}")

    threading.Thread(target=_rodar, daemon=True, name="backup-pos-registro").start()


@registro_bp.route("/", methods=["GET"])
def index():
    """Tela principal de registro, usada no chão de fábrica (tablet/celular)."""
    recentes = (
        db.session.query(RegistroTemperatura.responsavel)
        .distinct()
        .order_by(RegistroTemperatura.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template("registro.html", etapas=ETAPAS, responsaveis=responsaveis)


@registro_bp.route("/registrar", methods=["POST"])
def registrar():
    etapa = (request.form.get("etapa") or "").strip()
    temperatura_raw = (request.form.get("temperatura") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if etapa not in ETAPAS:
        erros.append("Selecione uma etapa válida.")

    temperatura = None
    if not temperatura_raw:
        erros.append("Informe a temperatura.")
    else:
        try:
            temperatura = float(temperatura_raw.replace(",", "."))
        except ValueError:
            erros.append("Temperatura inválida. Use apenas números.")

    if not responsavel:
        erros.append("Informe o responsável pelo registro.")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("registro.index"))

    registro = RegistroTemperatura(
        data=date.today(),
        horario=datetime.now().time().replace(microsecond=0),
        etapa=etapa,
        temperatura=temperatura,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    _agendar_backup_apos_registro()

    if registro.conforme:
        flash(
            f"✅ Registro salvo! {etapa}: {temperatura:.1f}°C — dentro do padrão "
            f"(até {registro.limite:.0f}°C).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {etapa}: {temperatura:.1f}°C — limite é "
            f"{registro.limite:.0f}°C. O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("registro.index"))

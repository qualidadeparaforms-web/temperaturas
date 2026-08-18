from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.calibracao_phmetro.models import RegistroCalibracaoPhmetro

formulario_bp = Blueprint("calibracao_phmetro", __name__, url_prefix="/calibracao_phmetro")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-C — Calibrações pHmetro. Confirmação
    simples (Sim/Não) de que a calibração semanal do pHmetro (pH 7,
    pH 4, pH 10) foi feita, sem detalhar cada solução."""
    recentes = (
        db.session.query(RegistroCalibracaoPhmetro.responsavel)
        .distinct()
        .order_by(RegistroCalibracaoPhmetro.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/calibracao_phmetro/formulario.html",
        responsaveis=responsaveis,
        data_hoje=agora_brasilia().date().isoformat(),
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    data_str = request.form.get("data") or ""
    calibracao_str = request.form.get("calibracao_realizada")
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []

    data_registro = None
    if not data_str:
        erros.append("Informe a data.")
    else:
        try:
            data_registro = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            erros.append("Data inválida.")

    if calibracao_str not in ("sim", "nao"):
        erros.append("Selecione Sim ou Não para \"Calibração Realizada\".")

    if not responsavel:
        erros.append("Informe o responsável (Monitor).")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("calibracao_phmetro.index"))

    calibracao_realizada = calibracao_str == "sim"

    db.session.add(
        RegistroCalibracaoPhmetro(
            data=data_registro,
            calibracao_realizada=calibracao_realizada,
            responsavel=responsavel,
        )
    )
    db.session.commit()

    agendar_backup_apos_registro()

    if calibracao_realizada:
        flash("✅ Registro salvo — calibração do pHmetro realizada.", "success")
    else:
        flash(
            "⚠️ Registro salvo indicando que a calibração do pHmetro NÃO foi realizada esta semana.",
            "warning",
        )

    return redirect(url_for("calibracao_phmetro.index"))

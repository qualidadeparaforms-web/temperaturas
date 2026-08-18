from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.limpeza_agulhas_injetora.models import STATUS_VALIDOS, RegistroLimpezaAgulhasInjetora

formulario_bp = Blueprint("limpeza_agulhas_injetora", __name__, url_prefix="/limpeza_agulhas_injetora")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 01-C — Limpeza Interna das Agulhas da
    Máquina Injetora. Dois critérios C/NC (agulhas limpas, sem
    resíduos) e dois responsáveis distintos: o operador que fez a
    limpeza e o controle de qualidade que registrou/validou."""
    operadores_recentes = (
        db.session.query(RegistroLimpezaAgulhasInjetora.operador)
        .distinct()
        .order_by(RegistroLimpezaAgulhasInjetora.criado_em.desc())
        .limit(15)
        .all()
    )
    cq_recentes = (
        db.session.query(RegistroLimpezaAgulhasInjetora.controle_qualidade)
        .distinct()
        .order_by(RegistroLimpezaAgulhasInjetora.criado_em.desc())
        .limit(15)
        .all()
    )
    return render_template(
        "tipos/limpeza_agulhas_injetora/formulario.html",
        data_hoje=agora_brasilia().date().isoformat(),
        operadores=[r[0] for r in operadores_recentes],
        controles_qualidade=[r[0] for r in cq_recentes],
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    data_str = request.form.get("data") or ""
    agulhas_limpas = request.form.get("agulhas_limpas")
    sem_residuos = request.form.get("sem_residuos")
    operador = (request.form.get("operador") or "").strip()
    controle_qualidade = (request.form.get("controle_qualidade") or "").strip()

    erros = []

    data_registro = None
    if not data_str:
        erros.append("Informe a data.")
    else:
        try:
            data_registro = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            erros.append("Data inválida.")

    if agulhas_limpas not in STATUS_VALIDOS:
        erros.append("Selecione C ou NC para \"Agulhas Limpas\".")
    if sem_residuos not in STATUS_VALIDOS:
        erros.append("Selecione C ou NC para \"Sem Resíduos\".")
    if not operador:
        erros.append("Informe o operador (quem fez a limpeza).")
    if not controle_qualidade:
        erros.append("Informe o controle de qualidade (quem está registrando).")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("limpeza_agulhas_injetora.index"))

    registro = RegistroLimpezaAgulhasInjetora(
        data=data_registro,
        agulhas_limpas=agulhas_limpas,
        sem_residuos=sem_residuos,
        operador=operador,
        controle_qualidade=controle_qualidade,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    if registro.conforme:
        flash("✅ Registro salvo — agulhas limpas e sem resíduos.", "success")
    else:
        criterios_nc = []
        if agulhas_limpas == "NC":
            criterios_nc.append("Agulhas Limpas")
        if sem_residuos == "NC":
            criterios_nc.append("Sem Resíduos")
        flash(
            f"⚠️ Registro salvo com não conformidade em: {', '.join(criterios_nc)}.",
            "warning",
        )

    return redirect(url_for("limpeza_agulhas_injetora.index"))

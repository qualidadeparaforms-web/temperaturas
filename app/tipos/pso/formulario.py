from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.pso.models import PSOS, STATUS_VALIDOS, RegistroPso

formulario_bp = Blueprint("pso", __name__, url_prefix="/pso")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 11 — Monitoramento dos PSO's.

    Checklist diário com os 7 PSOs fixos: cada um recebe C (conforme)
    ou NC (não conforme) via um par de botões grandes, e o Monitor
    (responsável) preenche um único campo. Um único POST grava as 7
    linhas do dia de uma vez (ver `registrar`).
    """
    recentes = (
        db.session.query(RegistroPso.responsavel)
        .distinct()
        .order_by(RegistroPso.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template("tipos/pso/formulario.html", psos=PSOS, responsaveis=responsaveis)


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if not responsavel:
        erros.append("Informe o responsável (Monitor).")

    status_por_pso = []
    for indice, pso in enumerate(PSOS):
        status = request.form.get(f"status_{indice}")
        if status not in STATUS_VALIDOS:
            erros.append(f'Selecione C ou NC para "{pso}".')
            continue
        status_por_pso.append((pso, status))

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("pso.index"))

    data_hoje = agora_brasilia().date()
    for pso, status in status_por_pso:
        db.session.add(RegistroPso(data=data_hoje, pso=pso, status=status, responsavel=responsavel))
    db.session.commit()

    agendar_backup_apos_registro()

    total_nc = sum(1 for _, status in status_por_pso if status == "NC")
    if total_nc == 0:
        flash(
            f"✅ Checklist salvo! Todos os {len(status_por_pso)} PSOs conformes.",
            "success",
        )
    else:
        psos_nc = ", ".join(pso for pso, status in status_por_pso if status == "NC")
        flash(
            f"⚠️ Checklist salvo com {total_nc} PSO(s) não conforme(s): {psos_nc}.",
            "warning",
        )

    return redirect(url_for("pso.index"))

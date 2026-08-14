from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.ventilacao.models import SETORES_COM_GRUPO, STATUS_VALIDOS, RegistroVentilacao

formulario_bp = Blueprint("ventilacao", __name__, url_prefix="/ventilacao")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-E — Monitoramento da Ventilação.

    Checklist semanal com os 22 setores fixos (divididos em 2 grupos):
    cada um recebe C (conforme) ou NC (não conforme) via um par de
    botões grandes, cobrindo em conjunto os 4 critérios (condensação,
    odores, gelo, contra-fluxo de ar). O Monitor escolhe a data da
    checagem (não é sempre "hoje", por ser semanal) e preenche o
    responsável. Um único POST grava as 22 linhas de uma vez (ver
    `registrar`).
    """
    recentes = (
        db.session.query(RegistroVentilacao.responsavel)
        .distinct()
        .order_by(RegistroVentilacao.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/ventilacao/formulario.html",
        setores=SETORES_COM_GRUPO,
        responsaveis=responsaveis,
        data_hoje=agora_brasilia().date().isoformat(),
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    responsavel = (request.form.get("responsavel") or "").strip()
    data_str = request.form.get("data") or ""

    erros = []

    data_checagem = None
    if not data_str:
        erros.append("Informe a data da checagem.")
    else:
        try:
            data_checagem = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            erros.append("Data inválida.")

    if not responsavel:
        erros.append("Informe o responsável (Monitor).")

    status_por_setor = []
    for indice, (grupo, setor) in enumerate(SETORES_COM_GRUPO):
        status = request.form.get(f"status_{indice}")
        if status not in STATUS_VALIDOS:
            erros.append(f'Selecione C ou NC para "{setor}".')
            continue
        status_por_setor.append((grupo, setor, status))

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("ventilacao.index"))

    for grupo, setor, status in status_por_setor:
        db.session.add(
            RegistroVentilacao(
                data=data_checagem,
                grupo=grupo,
                setor=setor,
                status=status,
                responsavel=responsavel,
            )
        )
    db.session.commit()

    agendar_backup_apos_registro()

    total_nc = sum(1 for _, _, status in status_por_setor if status == "NC")
    if total_nc == 0:
        flash(
            f"✅ Checklist salvo! Todos os {len(status_por_setor)} setores conformes.",
            "success",
        )
    else:
        setores_nc = ", ".join(setor for _, setor, status in status_por_setor if status == "NC")
        flash(
            f"⚠️ Checklist salvo com {total_nc} setor(es) não conforme(s): {setores_nc}.",
            "warning",
        )

    return redirect(url_for("ventilacao.index"))

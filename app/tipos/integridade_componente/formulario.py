from datetime import datetime as _datetime
from datetime import time as _time
from datetime import timedelta as _timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.integridade_componente.models import (
    EQUIPAMENTOS,
    EQUIPAMENTOS_INFO,
    STATUS_VALIDOS,
    RegistroIntegridadeComponente,
    VerificacaoRT,
    momentos_do_equipamento,
)

formulario_bp = Blueprint("integridade_componente", __name__, url_prefix="/integridade_componente")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 17 — Monitoramento de Integridade de
    Componentes de Máquinas (agulhas/lâminas de 3 equipamentos,
    antigos PAC 17-A/17-C/17-G, unificados neste tipo).
    """
    responsaveis = [
        r[0]
        for r in db.session.query(RegistroIntegridadeComponente.responsavel)
        .distinct()
        .order_by(RegistroIntegridadeComponente.criado_em.desc())
        .limit(15)
        .all()
    ]
    return render_template(
        "tipos/integridade_componente/formulario.html",
        equipamentos=EQUIPAMENTOS,
        equipamentos_info=EQUIPAMENTOS_INFO,
        responsaveis=responsaveis,
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    equipamento = (request.form.get("equipamento") or "").strip()
    momento = (request.form.get("momento") or "").strip()
    horario_raw = (request.form.get("horario") or "").strip()
    status = request.form.get("status")
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if equipamento not in EQUIPAMENTOS:
        erros.append("Selecione um equipamento válido.")
    elif momento not in momentos_do_equipamento(equipamento):
        erros.append("Selecione um momento válido para o equipamento escolhido.")

    horario = None
    if not horario_raw:
        erros.append("Informe o horário da checagem.")
    else:
        try:
            horario = _datetime.strptime(horario_raw, "%H:%M").time()
        except ValueError:
            erros.append("Horário inválido.")

    if status not in STATUS_VALIDOS:
        erros.append("Selecione C ou NC.")

    if not responsavel:
        erros.append("Informe o responsável (Monitor).")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("integridade_componente.index"))

    registro = RegistroIntegridadeComponente(
        data=agora_brasilia().date(),
        equipamento=equipamento,
        momento=momento,
        horario=horario,
        status=status,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    descricao = f"{equipamento} — {registro.componente} ({momento})"
    if registro.conforme:
        flash(f"✅ Registro salvo! {descricao}: íntegro, sem partes quebradas ou faltantes.", "success")
    else:
        flash(
            f"⚠️ NC registrado! {descricao}: risco de contaminação física do produto — "
            f"verifique antes de continuar a produção. O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("integridade_componente.index"))


@formulario_bp.route("/verificacao-rt", methods=["GET"])
def verificacao_rt():
    """Tela rápida — sem formulário longo — pra registrar apenas a
    data/hora e o equipamento conferido. Disponível a partir do menu
    de qualquer tela (ver link na barra de navegação, base.html)."""
    hoje = agora_brasilia().date()
    inicio_do_dia = _datetime.combine(hoje, _time.min)
    fim_do_dia = inicio_do_dia + _timedelta(days=1)
    verificacoes_hoje = (
        VerificacaoRT.query.filter(
            VerificacaoRT.data_hora >= inicio_do_dia, VerificacaoRT.data_hora < fim_do_dia
        )
        .order_by(VerificacaoRT.data_hora.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "tipos/integridade_componente/verificacao_rt.html",
        equipamentos=EQUIPAMENTOS,
        verificacoes_hoje=verificacoes_hoje,
    )


@formulario_bp.route("/verificacao-rt/registrar", methods=["POST"])
def registrar_verificacao_rt():
    equipamento = (request.form.get("equipamento") or "").strip()
    if equipamento not in EQUIPAMENTOS:
        flash("Selecione um equipamento válido.", "danger")
        return redirect(url_for("integridade_componente.verificacao_rt"))

    db.session.add(VerificacaoRT(equipamento=equipamento))
    db.session.commit()

    agendar_backup_apos_registro()

    flash(f"✅ Verificação RT registrada — {equipamento}.", "success")
    return redirect(url_for("integridade_componente.verificacao_rt"))

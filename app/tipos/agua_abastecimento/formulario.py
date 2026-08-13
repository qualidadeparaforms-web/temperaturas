from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.agua_abastecimento.models import PONTOS, RegistroAguaAbastecimento

formulario_bp = Blueprint("agua_abastecimento", __name__, url_prefix="/agua_abastecimento")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 03-A — Água de Abastecimento (Cloro e pH)."""
    recentes = (
        db.session.query(RegistroAguaAbastecimento.responsavel)
        .distinct()
        .order_by(RegistroAguaAbastecimento.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/agua_abastecimento/formulario.html",
        pontos=PONTOS,
        responsaveis=responsaveis,
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    ponto = (request.form.get("ponto") or "").strip()
    ph_raw = (request.form.get("ph") or "").strip()
    cloro_raw = (request.form.get("cloro") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if ponto not in PONTOS:
        erros.append("Selecione um ponto de coleta válido.")

    ph = None
    if not ph_raw:
        erros.append("Informe o pH.")
    else:
        try:
            ph = float(ph_raw.replace(",", "."))
        except ValueError:
            erros.append("pH inválido. Use apenas números.")

    cloro = None
    if not cloro_raw:
        erros.append("Informe o cloro.")
    else:
        try:
            cloro = float(cloro_raw.replace(",", "."))
        except ValueError:
            erros.append("Cloro inválido. Use apenas números.")

    if not responsavel:
        erros.append("Informe o responsável pelo registro.")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("agua_abastecimento.index"))

    registro = RegistroAguaAbastecimento(
        data=agora_brasilia().date(),
        horario=agora_brasilia().time().replace(microsecond=0),
        ponto=ponto,
        ph=ph,
        cloro=cloro,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    if registro.conforme:
        flash(
            f"✅ Registro salvo! {ponto}: pH {ph:.2f} / Cloro {cloro:.2f}ppm — dentro do padrão.",
            "success",
        )
    else:
        flash(
            f"⚠️ {registro.situacao}! {ponto}: pH {ph:.2f} (padrão 6,0–9,0) / "
            f"Cloro {cloro:.2f}ppm (padrão 0,2–5,0ppm). O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("agua_abastecimento.index"))

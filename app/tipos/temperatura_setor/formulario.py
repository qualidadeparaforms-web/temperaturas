from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.temperatura_setor.models import SETORES, RegistroTemperaturaSetor

formulario_bp = Blueprint("temperatura_setor", __name__, url_prefix="/temperatura_setor")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro de temperatura de setor/câmara."""
    recentes = (
        db.session.query(RegistroTemperaturaSetor.responsavel)
        .distinct()
        .order_by(RegistroTemperaturaSetor.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/temperatura_setor/formulario.html", setores=SETORES, responsaveis=responsaveis
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    setor = (request.form.get("setor") or "").strip()
    temperatura_raw = (request.form.get("temperatura") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if setor not in SETORES:
        erros.append("Selecione um setor válido.")

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
        return redirect(url_for("temperatura_setor.index"))

    registro = RegistroTemperaturaSetor(
        data=agora_brasilia().date(),
        horario=agora_brasilia().time().replace(microsecond=0),
        setor=setor,
        temperatura=temperatura,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    if registro.conforme:
        flash(
            f"✅ Registro salvo! {setor}: {temperatura:.1f}°C — dentro do padrão "
            f"(limite {registro.limite:.0f}°C).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {setor}: {temperatura:.1f}°C — limite é "
            f"{registro.limite:.0f}°C. O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("temperatura_setor.index"))

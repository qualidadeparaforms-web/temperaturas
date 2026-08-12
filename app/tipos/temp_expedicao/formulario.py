from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.tipos.temp_expedicao.models import (
    CATEGORIAS,
    LOCAIS,
    LOCAIS_COM_CATEGORIA,
    RegistroTempExpedicao,
)

formulario_bp = Blueprint("temp_expedicao", __name__, url_prefix="/temp_expedicao")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 04-D — Temperatura dos Produtos nas Câmaras de Expedição."""
    responsaveis = [
        r[0]
        for r in db.session.query(RegistroTempExpedicao.responsavel)
        .distinct()
        .order_by(RegistroTempExpedicao.criado_em.desc())
        .limit(15)
        .all()
    ]
    return render_template(
        "tipos/temp_expedicao/formulario.html",
        locais=LOCAIS,
        locais_com_categoria=LOCAIS_COM_CATEGORIA,
        categorias=CATEGORIAS,
        responsaveis=responsaveis,
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    local = (request.form.get("local") or "").strip()
    categoria_raw = (request.form.get("categoria") or "").strip()
    temperatura_raw = (request.form.get("temperatura") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if local not in LOCAIS:
        erros.append("Selecione um local válido.")

    categoria = None
    if local in LOCAIS_COM_CATEGORIA:
        if categoria_raw not in CATEGORIAS:
            erros.append("Selecione uma categoria válida.")
        else:
            categoria = categoria_raw
    # Para o local sem categoria (Matéria Prima), qualquer valor
    # enviado é ignorado — o registro é sempre salvo sem categoria.

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
        return redirect(url_for("temp_expedicao.index"))

    registro = RegistroTempExpedicao(
        data=date.today(),
        horario=datetime.now().time().replace(microsecond=0),
        local=local,
        categoria=categoria,
        temperatura=temperatura,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    descricao = local + (f" ({categoria})" if categoria else "")
    if registro.conforme:
        flash(
            f"✅ Registro salvo! {descricao}: {temperatura:.1f}°C — dentro do padrão "
            f"(até {registro.limite:.0f}°C).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {descricao}: {temperatura:.1f}°C — limite é "
            f"{registro.limite:.0f}°C. O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("temp_expedicao.index"))

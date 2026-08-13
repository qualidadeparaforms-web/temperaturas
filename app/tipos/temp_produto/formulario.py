from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.temp_produto.models import CATEGORIAS, LOCAIS, RegistroTempProduto

formulario_bp = Blueprint("temp_produto", __name__, url_prefix="/temp_produto")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 04-C — Temperatura dos Produtos na Produção."""
    responsaveis = [
        r[0]
        for r in db.session.query(RegistroTempProduto.responsavel)
        .distinct()
        .order_by(RegistroTempProduto.criado_em.desc())
        .limit(15)
        .all()
    ]
    # Produtos recentes, só como sugestão de digitação (datalist) —
    # o campo é texto livre, não uma lista fixa.
    produtos_sugeridos = [
        r[0]
        for r in db.session.query(RegistroTempProduto.produto)
        .distinct()
        .order_by(RegistroTempProduto.criado_em.desc())
        .limit(15)
        .all()
    ]
    return render_template(
        "tipos/temp_produto/formulario.html",
        locais=LOCAIS,
        categorias=CATEGORIAS,
        produtos_sugeridos=produtos_sugeridos,
        responsaveis=responsaveis,
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    local = (request.form.get("local") or "").strip()
    categoria = (request.form.get("categoria") or "").strip()
    produto = (request.form.get("produto") or "").strip()
    temperatura_raw = (request.form.get("temperatura") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()

    erros = []
    if local not in LOCAIS:
        erros.append("Selecione um local válido.")
    if categoria not in CATEGORIAS:
        erros.append("Selecione uma categoria válida.")
    if not produto:
        erros.append("Informe o nome do produto.")

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
        return redirect(url_for("temp_produto.index"))

    registro = RegistroTempProduto(
        data=agora_brasilia().date(),
        horario=agora_brasilia().time().replace(microsecond=0),
        local=local,
        categoria=categoria,
        produto=produto,
        temperatura=temperatura,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    if registro.conforme:
        flash(
            f"✅ Registro salvo! {produto} ({categoria}): {temperatura:.1f}°C — dentro do padrão "
            f"(até {registro.limite:.0f}°C).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {produto} ({categoria}): {temperatura:.1f}°C — limite é "
            f"{registro.limite:.0f}°C. O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("temp_produto.index"))

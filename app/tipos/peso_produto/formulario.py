import json
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.tipos.peso_produto.models import PesagemIndividual, RegistroPesoProduto

formulario_bp = Blueprint("peso_produto", __name__, url_prefix="/peso_produto")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 06-D — Monitoramento de Peso (Produto Embalado).

    As pesagens individuais são acumuladas no navegador (lista viva,
    com resumo em tempo real) e só chegam ao servidor quando o
    usuário aperta "Finalizar registro do produto" — um único POST
    salva o registro do produto e todas as suas pesagens numa
    transação só (ver `registrar`).
    """
    responsaveis = [
        r[0]
        for r in db.session.query(RegistroPesoProduto.responsavel)
        .distinct()
        .order_by(RegistroPesoProduto.criado_em.desc())
        .limit(15)
        .all()
    ]
    produtos_sugeridos = [
        r[0]
        for r in db.session.query(RegistroPesoProduto.produto)
        .distinct()
        .order_by(RegistroPesoProduto.criado_em.desc())
        .limit(15)
        .all()
    ]
    return render_template(
        "tipos/peso_produto/formulario.html",
        responsaveis=responsaveis,
        produtos_sugeridos=produtos_sugeridos,
    )


def _parse_float(valor_raw: str) -> float:
    return float(valor_raw.replace(",", "."))


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    produto = (request.form.get("produto") or "").strip()
    peso_liquido_raw = (request.form.get("peso_liquido_nominal") or "").strip()
    peso_embalagem_raw = (request.form.get("peso_embalagem") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()
    pesagens_raw = (request.form.get("pesagens_json") or "").strip()

    erros = []
    if not produto:
        erros.append("Informe o nome do produto.")

    peso_liquido_nominal = None
    if not peso_liquido_raw:
        erros.append("Informe o peso líquido nominal.")
    else:
        try:
            peso_liquido_nominal = _parse_float(peso_liquido_raw)
        except ValueError:
            erros.append("Peso líquido nominal inválido. Use apenas números.")

    peso_embalagem = None
    if not peso_embalagem_raw:
        erros.append("Informe o peso da embalagem.")
    else:
        try:
            peso_embalagem = _parse_float(peso_embalagem_raw)
        except ValueError:
            erros.append("Peso da embalagem inválido. Use apenas números.")

    if not responsavel:
        erros.append("Informe o responsável pelo registro.")

    pesos_medidos = []
    if not pesagens_raw:
        erros.append("Adicione pelo menos uma pesagem antes de finalizar.")
    else:
        try:
            valores = json.loads(pesagens_raw)
            if not isinstance(valores, list) or not valores:
                raise ValueError("lista de pesagens vazia ou inválida")
            pesos_medidos = [float(v) for v in valores]
        except (ValueError, TypeError):
            erros.append("Pesagens inválidas — adicione pelo menos uma pesagem antes de finalizar.")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("peso_produto.index"))

    registro = RegistroPesoProduto(
        data=date.today(),
        horario=datetime.now().time().replace(microsecond=0),
        produto=produto,
        peso_liquido_nominal=peso_liquido_nominal,
        peso_embalagem=peso_embalagem,
        responsavel=responsavel,
    )
    for peso in pesos_medidos:
        registro.pesagens.append(PesagemIndividual(peso_medido=peso))

    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    if registro.conforme:
        flash(
            f"✅ Registro salvo! {produto}: {registro.total_pesagens} pesagem(ns), "
            f"todas conformes (padrão mínimo: {registro.peso_minimo:g}).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {produto}: {registro.total_nc} de {registro.total_pesagens} "
            f"pesagem(ns) não conforme(s) (padrão mínimo: {registro.peso_minimo:g}). "
            f"O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("peso_produto.index"))

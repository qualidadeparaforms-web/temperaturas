import json
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.tipos.gramatura.models import PesagemIndividualGramatura, RegistroGramatura

formulario_bp = Blueprint("gramatura", __name__, url_prefix="/gramatura")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 06-E — Monitoramento de Gramatura de
    Bifes e Cubos.

    Igual ao PAC 06-D (peso do produto embalado), mas sem embalagem:
    aqui compara-se cada pesagem com uma FAIXA de gramatura
    (gramatura_minima..gramatura_maxima) — qualquer valor fora da
    faixa é NC. As pesagens são acumuladas no navegador e só chegam ao
    servidor num único POST ao finalizar (ver `registrar`).
    """
    responsaveis = [
        r[0]
        for r in db.session.query(RegistroGramatura.responsavel)
        .distinct()
        .order_by(RegistroGramatura.criado_em.desc())
        .limit(15)
        .all()
    ]
    operadores = [
        r[0]
        for r in db.session.query(RegistroGramatura.operador)
        .distinct()
        .order_by(RegistroGramatura.criado_em.desc())
        .limit(15)
        .all()
    ]
    produtos_sugeridos = [
        r[0]
        for r in db.session.query(RegistroGramatura.produto)
        .distinct()
        .order_by(RegistroGramatura.criado_em.desc())
        .limit(15)
        .all()
    ]
    return render_template(
        "tipos/gramatura/formulario.html",
        responsaveis=responsaveis,
        operadores=operadores,
        produtos_sugeridos=produtos_sugeridos,
    )


def _parse_float(valor_raw: str) -> float:
    return float(valor_raw.replace(",", "."))


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
    produto = (request.form.get("produto") or "").strip()
    gramatura_minima_raw = (request.form.get("gramatura_minima") or "").strip()
    gramatura_maxima_raw = (request.form.get("gramatura_maxima") or "").strip()
    operador = (request.form.get("operador") or "").strip()
    responsavel = (request.form.get("responsavel") or "").strip()
    pesagens_raw = (request.form.get("pesagens_json") or "").strip()

    erros = []
    if not produto:
        erros.append("Informe o nome do produto.")

    gramatura_minima = None
    if not gramatura_minima_raw:
        erros.append("Informe a gramatura mínima.")
    else:
        try:
            gramatura_minima = _parse_float(gramatura_minima_raw)
        except ValueError:
            erros.append("Gramatura mínima inválida. Use apenas números.")

    gramatura_maxima = None
    if not gramatura_maxima_raw:
        erros.append("Informe a gramatura máxima.")
    else:
        try:
            gramatura_maxima = _parse_float(gramatura_maxima_raw)
        except ValueError:
            erros.append("Gramatura máxima inválida. Use apenas números.")

    if gramatura_minima is not None and gramatura_maxima is not None and gramatura_minima >= gramatura_maxima:
        erros.append("A gramatura mínima deve ser menor que a gramatura máxima.")

    if not operador:
        erros.append("Informe o operador.")

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
        return redirect(url_for("gramatura.index"))

    registro = RegistroGramatura(
        data=date.today(),
        horario=datetime.now().time().replace(microsecond=0),
        produto=produto,
        gramatura_minima=gramatura_minima,
        gramatura_maxima=gramatura_maxima,
        operador=operador,
        responsavel=responsavel,
    )
    for peso in pesos_medidos:
        registro.pesagens.append(PesagemIndividualGramatura(peso_medido=peso))

    db.session.add(registro)
    db.session.commit()

    agendar_backup_apos_registro()

    faixa = f"{registro.gramatura_minima:g}–{registro.gramatura_maxima:g}"
    if registro.conforme:
        flash(
            f"✅ Registro salvo! {produto}: {registro.total_pesagens} pesagem(ns), "
            f"todas conformes (faixa: {faixa}).",
            "success",
        )
    else:
        flash(
            f"⚠️ Fora do padrão! {produto}: {registro.total_nc} de {registro.total_pesagens} "
            f"pesagem(ns) fora da faixa de gramatura ({faixa}). "
            f"O registro foi salvo mesmo assim.",
            "warning",
        )

    return redirect(url_for("gramatura.index"))

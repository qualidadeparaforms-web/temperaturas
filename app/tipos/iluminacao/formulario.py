from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.iluminacao.models import PONTOS_COM_SETOR, RegistroIluminacao, status_para_leitura

formulario_bp = Blueprint("iluminacao", __name__, url_prefix="/iluminacao")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-D — Monitoramento da Iluminação.

    Checklist mensal com os pontos fixos (organizados por setor):
    cada um mostra o mínimo de lux exigido (informativo, fixo) e um
    campo pra digitar a leitura do luxímetro. O status C/NC aparece
    ao vivo no navegador assim que a leitura é digitada (ver script
    no template) e é recalculado no servidor ao salvar. Não é
    obrigatório preencher todos os pontos de uma vez — só os
    preenchidos são salvos (ver `registrar`).
    """
    return render_template(
        "tipos/iluminacao/formulario.html",
        pontos=PONTOS_COM_SETOR,
        data_hoje=agora_brasilia().date().isoformat(),
    )


@formulario_bp.route("/registrar", methods=["POST"])
def registrar():
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

    leituras = []
    for indice, (setor, local, lux_necessario) in enumerate(PONTOS_COM_SETOR):
        valor_str = (request.form.get(f"lux_obtido_{indice}") or "").strip()
        if not valor_str:
            continue
        try:
            lux_obtido = float(valor_str.replace(",", "."))
        except ValueError:
            erros.append(f'Leitura de lux inválida para "{setor} — {local}".')
            continue
        leituras.append((setor, local, lux_necessario, lux_obtido))

    if not erros and not leituras:
        erros.append("Preencha a leitura de pelo menos um ponto.")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("iluminacao.index"))

    total_nc = 0
    nomes_nc = []
    for setor, local, lux_necessario, lux_obtido in leituras:
        status = status_para_leitura(lux_obtido, lux_necessario)
        if status == "NC":
            total_nc += 1
            nomes_nc.append(f"{setor} — {local}")
        db.session.add(
            RegistroIluminacao(
                data=data_checagem,
                setor=setor,
                local=local,
                lux_necessario=lux_necessario,
                lux_obtido=lux_obtido,
                status=status,
            )
        )
    db.session.commit()

    agendar_backup_apos_registro()

    if total_nc == 0:
        flash(
            f"✅ Checklist salvo! Todos os {len(leituras)} ponto(s) lançado(s) conformes.",
            "success",
        )
    else:
        flash(
            f"⚠️ Checklist salvo com {total_nc} ponto(s) não conforme(s): {', '.join(nomes_nc)}.",
            "warning",
        )

    return redirect(url_for("iluminacao.index"))

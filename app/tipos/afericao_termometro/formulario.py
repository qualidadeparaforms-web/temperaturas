from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.afericao_termometro.models import (
    TERMOMETRO_PADRAO_CODIGO,
    RegistroAfericaoTermometro,
    Termometro,
    status_para_leituras,
)

formulario_bp = Blueprint("afericao_termometro", __name__, url_prefix="/afericao_termometro")

CAMPOS_TEMPERATURA = ("quente_padrao", "quente_equipamento", "fria_padrao", "fria_equipamento")
ROTULOS_CAMPOS = {
    "quente_padrao": "quente do padrão",
    "quente_equipamento": "quente do equipamento",
    "fria_padrao": "fria do padrão",
    "fria_equipamento": "fria do equipamento",
}


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-F — Aferição dos Termômetros.

    Compara cada um dos 4 termômetros/equipamentos cadastrados contra
    o termômetro padrão de referência (TERMOMETRO_PADRAO_CODIGO), nas
    condições quente e fria. O status C/NC é calculado ao vivo no
    navegador conforme os 4 campos de cada equipamento são
    preenchidos (ver script abaixo) e recalculado no servidor ao
    salvar. Diferente do PAC 08-G, aqui as 4 leituras dos 4
    equipamentos são todas obrigatórias — um único POST grava a
    aferição completa de uma vez (ver `registrar`).
    """
    termometros = Termometro.query.order_by(Termometro.id.asc()).all()
    recentes = (
        db.session.query(RegistroAfericaoTermometro.responsavel)
        .distinct()
        .order_by(RegistroAfericaoTermometro.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/afericao_termometro/formulario.html",
        termometros=termometros,
        responsaveis=responsaveis,
        data_hoje=agora_brasilia().date().isoformat(),
        termometro_padrao_codigo=TERMOMETRO_PADRAO_CODIGO,
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
        erros.append("Informe o responsável.")

    termometros = Termometro.query.order_by(Termometro.id.asc()).all()
    leituras = []
    for termometro in termometros:
        valores = {}
        for campo in CAMPOS_TEMPERATURA:
            valor_str = (request.form.get(f"{campo}_{termometro.id}") or "").strip()
            if not valor_str:
                erros.append(f'Informe a temperatura {ROTULOS_CAMPOS[campo]} de "{termometro.rotulo()}".')
                continue
            try:
                valores[campo] = float(valor_str.replace(",", "."))
            except ValueError:
                erros.append(f'Temperatura {ROTULOS_CAMPOS[campo]} inválida para "{termometro.rotulo()}".')
        if len(valores) == len(CAMPOS_TEMPERATURA):
            leituras.append((termometro, valores))

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("afericao_termometro.index"))

    total_nc = 0
    nomes_nc = []
    for termometro, valores in leituras:
        status = status_para_leituras(
            valores["quente_padrao"], valores["quente_equipamento"],
            valores["fria_padrao"], valores["fria_equipamento"],
        )
        if status == "NC":
            total_nc += 1
            nomes_nc.append(termometro.rotulo())
        db.session.add(
            RegistroAfericaoTermometro(
                termometro_id=termometro.id,
                data=data_checagem,
                temp_quente_padrao=valores["quente_padrao"],
                temp_quente_equipamento=valores["quente_equipamento"],
                temp_fria_padrao=valores["fria_padrao"],
                temp_fria_equipamento=valores["fria_equipamento"],
                status=status,
                responsavel=responsavel,
            )
        )
    db.session.commit()

    agendar_backup_apos_registro()

    if total_nc == 0:
        flash(
            f"✅ Aferição salva! Todos os {len(leituras)} termômetros conformes.",
            "success",
        )
    else:
        flash(
            f"⚠️ Aferição salva com {total_nc} termômetro(s) não conforme(s): {', '.join(nomes_nc)}.",
            "warning",
        )

    return redirect(url_for("afericao_termometro.index"))

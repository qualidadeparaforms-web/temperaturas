from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.afericao_termometro.models import (
    TERMOMETRO_PADRAO_CODIGO,
    LeituraTermometroEquipamento,
    RegistroAfericaoTermometro,
    Termometro,
    status_para_leituras,
)

formulario_bp = Blueprint("afericao_termometro", __name__, url_prefix="/afericao_termometro")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-F — Aferição dos Termômetros.

    Fluxo em 4 passos: 1) temperatura quente do padrão (uma única
    leitura pra sessão inteira), 2) temperatura quente de cada um dos
    4 equipamentos, 3) temperatura fria do padrão (de novo, uma única
    leitura), 4) temperatura fria de cada equipamento. O status C/NC
    de cada equipamento é calculado ao vivo no navegador assim que
    suas duas leituras (quente e fria) e as duas leituras do padrão
    estiverem preenchidas (ver script no template) e recalculado no
    servidor ao salvar. As 4 leituras dos 4 equipamentos + as 2 do
    padrão são todas obrigatórias — um único POST grava a sessão
    inteira de uma vez (ver `registrar`).
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


def _ler_temperatura(nome_campo: str, rotulo: str, erros: list) -> float | None:
    valor_str = (request.form.get(nome_campo) or "").strip()
    if not valor_str:
        erros.append(f"Informe a temperatura {rotulo}.")
        return None
    try:
        return float(valor_str.replace(",", "."))
    except ValueError:
        erros.append(f"Temperatura {rotulo} inválida.")
        return None


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

    temp_quente_padrao = _ler_temperatura("quente_padrao", "quente do padrão", erros)
    temp_fria_padrao = _ler_temperatura("fria_padrao", "fria do padrão", erros)

    termometros = Termometro.query.order_by(Termometro.id.asc()).all()
    leituras_equipamento = []
    for termometro in termometros:
        quente = _ler_temperatura(
            f"quente_equipamento_{termometro.id}", f'quente de "{termometro.rotulo()}"', erros
        )
        fria = _ler_temperatura(
            f"fria_equipamento_{termometro.id}", f'fria de "{termometro.rotulo()}"', erros
        )
        if quente is not None and fria is not None:
            leituras_equipamento.append((termometro, quente, fria))

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("afericao_termometro.index"))

    registro = RegistroAfericaoTermometro(
        data=data_checagem,
        temp_quente_padrao=temp_quente_padrao,
        temp_fria_padrao=temp_fria_padrao,
        responsavel=responsavel,
    )
    db.session.add(registro)
    db.session.flush()  # garante registro.id antes de criar as leituras filhas

    total_nc = 0
    nomes_nc = []
    for termometro, quente_equip, fria_equip in leituras_equipamento:
        status = status_para_leituras(temp_quente_padrao, quente_equip, temp_fria_padrao, fria_equip)
        if status == "NC":
            total_nc += 1
            nomes_nc.append(termometro.rotulo())
        db.session.add(
            LeituraTermometroEquipamento(
                registro_id=registro.id,
                termometro_id=termometro.id,
                temp_quente_equipamento=quente_equip,
                temp_fria_equipamento=fria_equip,
                status=status,
            )
        )
    db.session.commit()

    agendar_backup_apos_registro()

    if total_nc == 0:
        flash(
            f"✅ Aferição salva! Todos os {len(leituras_equipamento)} termômetros conformes.",
            "success",
        )
    else:
        flash(
            f"⚠️ Aferição salva com {total_nc} termômetro(s) não conforme(s): {', '.join(nomes_nc)}.",
            "warning",
        )

    return redirect(url_for("afericao_termometro.index"))

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.backup_utils import agendar_backup_apos_registro
from app.extensions import db
from app.timezone_utils import agora_brasilia
from app.tipos.afericao_balanca.models import Balanca, RegistroAfericaoBalanca, status_para_leitura

formulario_bp = Blueprint("afericao_balanca", __name__, url_prefix="/afericao_balanca")


@formulario_bp.route("", methods=["GET"])
def index():
    """Tela de registro do PAC 08-G — Aferição das Balanças.

    Uma leitura por balança cadastrada (massa de teste de 1000g),
    organizada em grupos por setor. O status C/NC é calculado ao vivo
    no navegador conforme a leitura é digitada (ver script abaixo) e
    recalculado no servidor ao salvar — não é obrigatório preencher
    todas as balanças de uma vez: um único POST grava só as que
    tiverem leitura preenchida (ver `registrar`).
    """
    balancas = Balanca.query.order_by(Balanca.id.asc()).all()
    recentes = (
        db.session.query(RegistroAfericaoBalanca.responsavel)
        .distinct()
        .order_by(RegistroAfericaoBalanca.criado_em.desc())
        .limit(15)
        .all()
    )
    responsaveis = [r[0] for r in recentes]
    return render_template(
        "tipos/afericao_balanca/formulario.html",
        balancas=balancas,
        responsaveis=responsaveis,
        data_hoje=agora_brasilia().date().isoformat(),
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
        erros.append("Informe o responsável (Monitor).")

    balancas = Balanca.query.order_by(Balanca.id.asc()).all()
    leituras = []
    for balanca in balancas:
        valor_str = (request.form.get(f"leitura_{balanca.id}") or "").strip()
        if not valor_str:
            continue
        try:
            leitura = float(valor_str.replace(",", "."))
        except ValueError:
            erros.append(f'Leitura inválida para "{balanca.rotulo()}".')
            continue
        leituras.append((balanca, leitura))

    if not erros and not leituras:
        erros.append("Preencha a leitura de pelo menos uma balança.")

    if erros:
        for erro in erros:
            flash(erro, "danger")
        return redirect(url_for("afericao_balanca.index"))

    total_nc = 0
    nomes_nc = []
    for balanca, leitura in leituras:
        status = status_para_leitura(leitura)
        if status == "NC":
            total_nc += 1
            nomes_nc.append(balanca.rotulo())
        db.session.add(
            RegistroAfericaoBalanca(
                balanca_id=balanca.id,
                data=data_checagem,
                leitura=leitura,
                status=status,
                responsavel=responsavel,
            )
        )
    db.session.commit()

    agendar_backup_apos_registro()

    if total_nc == 0:
        flash(
            f"✅ Aferição salva! Todas as {len(leituras)} balança(s) lançada(s) conformes.",
            "success",
        )
    else:
        flash(
            f"⚠️ Aferição salva com {total_nc} balança(s) não conforme(s): {', '.join(nomes_nc)}.",
            "warning",
        )

    return redirect(url_for("afericao_balanca.index"))

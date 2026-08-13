from datetime import datetime, timedelta
from io import BytesIO

from flask import Blueprint, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

from app.timezone_utils import agora_brasilia
from app.tipos import TIPOS_REGISTRO, obter_tipo

dashboard_bp = Blueprint("dashboard", __name__)


def _periodo_para_datas(periodo, data_inicio=None, data_fim=None):
    hoje = agora_brasilia().date()
    if periodo == "dia":
        return hoje, hoje
    if periodo == "semana":
        return hoje - timedelta(days=6), hoje
    if periodo == "mes":
        return hoje - timedelta(days=29), hoje
    if periodo == "personalizado" and data_inicio and data_fim:
        try:
            return (
                datetime.strptime(data_inicio, "%Y-%m-%d").date(),
                datetime.strptime(data_fim, "%Y-%m-%d").date(),
            )
        except ValueError:
            pass
    return hoje - timedelta(days=6), hoje


@dashboard_bp.route("/dashboard")
def dashboard():
    """Painel principal: cada tipo de registro tem seu próprio painel
    completo (gráfico, cartões, filtros específicos). Esta rota só
    decide para onde mandar o usuário:

    - Um `tipo` específico pedido na URL (?tipo=<slug>) → painel
      daquele tipo.
    - Só existe um tipo cadastrado → vai direto pra ele (hoje é o caso:
      só "Temperatura de Processo" existe, então /dashboard se
      comporta exatamente como antes desta reestruturação).
    - Dois ou mais tipos, sem um `tipo` específico pedido → visão
      combinada (cartões de contagem + tabela unificada de todos os
      tipos).
    """
    tipo_pedido = request.args.get("tipo")

    if tipo_pedido and tipo_pedido != "todos":
        tipo = obter_tipo(tipo_pedido)
        if tipo:
            outros_params = {k: v for k, v in request.args.items() if k != "tipo"}
            return redirect(url_for(f"{tipo.slug}_dashboard.index", **outros_params))

    if tipo_pedido != "todos" and len(TIPOS_REGISTRO) == 1:
        return redirect(url_for(f"{TIPOS_REGISTRO[0].slug}_dashboard.index"))

    return _visao_combinada()


def _visao_combinada():
    periodo = request.args.get("periodo", "semana")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    inicio, fim = _periodo_para_datas(periodo, data_inicio, data_fim)

    resumos = [
        {"tipo": tipo, "total": tipo.contar(inicio, fim)} for tipo in TIPOS_REGISTRO
    ]

    linhas = []
    for tipo in TIPOS_REGISTRO:
        linhas.extend(tipo.linhas_combinadas(inicio, fim))
    linhas.sort(key=lambda linha: linha["ordenacao"], reverse=True)

    return render_template(
        "dashboard_combinado.html",
        tipos=TIPOS_REGISTRO,
        resumos=resumos,
        linhas=linhas,
        periodo=periodo,
        inicio=inicio,
        fim=fim,
    )


@dashboard_bp.route("/exportar")
def exportar():
    """Exportação combinada: um `tipo` específico gera a planilha
    daquele tipo (mesmo resultado de /dashboard/<tipo>/exportar);
    "todos" (ou nenhum tipo pedido, havendo mais de um cadastrado)
    gera um único arquivo com uma aba por tipo.
    """
    tipo_pedido = request.args.get("tipo", "todos")
    periodo = request.args.get("periodo", "semana")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    inicio, fim = _periodo_para_datas(periodo, data_inicio, data_fim)

    if tipo_pedido != "todos":
        tipo = obter_tipo(tipo_pedido)
        if tipo:
            return redirect(url_for(f"{tipo.slug}_dashboard.exportar", **request.args))

    wb = Workbook()
    del wb["Sheet"]
    for tipo in TIPOS_REGISTRO:
        tipo.adicionar_planilha(wb, inicio, fim, {})

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nome_arquivo = f"registros_{inicio.strftime('%Y%m%d')}_{fim.strftime('%Y%m%d')}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

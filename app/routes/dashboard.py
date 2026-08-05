from datetime import date, datetime, timedelta
from io import BytesIO

from flask import Blueprint, jsonify, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from app.models import ETAPAS, RegistroTemperatura

dashboard_bp = Blueprint("dashboard", __name__)

PERIODOS_VALIDOS = {"dia", "semana", "mes", "personalizado"}


def periodo_para_datas(periodo: str, data_inicio: str | None = None, data_fim: str | None = None):
    """Converte o filtro de período em um intervalo (inicio, fim), inclusive."""
    hoje = date.today()

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

    # Padrão: última semana.
    return hoje - timedelta(days=6), hoje


def buscar_registros(periodo: str, etapa: str, data_inicio: str | None = None, data_fim: str | None = None):
    inicio, fim = periodo_para_datas(periodo, data_inicio, data_fim)
    query = RegistroTemperatura.query.filter(
        RegistroTemperatura.data >= inicio, RegistroTemperatura.data <= fim
    )
    if etapa and etapa != "todas":
        query = query.filter(RegistroTemperatura.etapa == etapa)

    registros = query.order_by(
        RegistroTemperatura.data.asc(), RegistroTemperatura.horario.asc()
    ).all()
    return registros, inicio, fim


def _parametros_filtro():
    return {
        "periodo": request.args.get("periodo", "semana"),
        "etapa": request.args.get("etapa", "todas"),
        "data_inicio": request.args.get("data_inicio"),
        "data_fim": request.args.get("data_fim"),
    }


@dashboard_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", etapas=ETAPAS)


@dashboard_bp.route("/api/registros")
def api_registros():
    filtros = _parametros_filtro()
    registros, inicio, fim = buscar_registros(**filtros)

    total = len(registros)
    fora_padrao = sum(1 for r in registros if not r.conforme)
    conformes = total - fora_padrao

    return jsonify(
        {
            "registros": [r.to_dict() for r in registros],
            "resumo": {
                "total": total,
                "conformes": conformes,
                "fora_padrao": fora_padrao,
                "percentual_conforme": round(conformes / total * 100, 1) if total else 100.0,
            },
            "periodo": {
                "inicio": inicio.strftime("%d/%m/%Y"),
                "fim": fim.strftime("%d/%m/%Y"),
            },
        }
    )


@dashboard_bp.route("/exportar")
def exportar():
    filtros = _parametros_filtro()
    registros, inicio, fim = buscar_registros(**filtros)

    wb = Workbook()
    ws = wb.active
    ws.title = "Registros de Temperatura"

    colunas = ["Dia", "Horário", "Etapa", "Temperatura", "Responsável", "Conforme"]
    ws.append(colunas)

    cabecalho_preenchimento = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    cabecalho_fonte = Font(color="FFFFFF", bold=True)
    for indice in range(1, len(colunas) + 1):
        celula = ws.cell(row=1, column=indice)
        celula.fill = cabecalho_preenchimento
        celula.font = cabecalho_fonte
        celula.alignment = Alignment(horizontal="center")

    preenchimento_fora_padrao = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    fonte_fora_padrao = Font(color="C00000", bold=True)

    for registro in registros:
        ws.append(
            [
                registro.data.strftime("%d/%m/%Y"),
                registro.horario.strftime("%H:%M"),
                registro.etapa,
                registro.temperatura,
                registro.responsavel,
                "Sim" if registro.conforme else "Não",
            ]
        )
        if not registro.conforme:
            linha = ws.max_row
            for indice in range(1, len(colunas) + 1):
                celula = ws.cell(row=linha, column=indice)
                celula.fill = preenchimento_fora_padrao
                celula.font = fonte_fora_padrao

    larguras = [12, 10, 14, 14, 24, 12]
    for indice, largura in enumerate(larguras, start=1):
        ws.column_dimensions[chr(64 + indice)].width = largura

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nome_arquivo = (
        f"registros_temperatura_{inicio.strftime('%Y%m%d')}_{fim.strftime('%Y%m%d')}.xlsx"
    )
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.gramatura.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.gramatura.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="gramatura",
    nome="PAC 06-E - Monitoramento de Gramatura de Bifes e Cubos",
    icone="📏",
    tabela="registros_gramatura",
    colunas_backup=[
        "id",
        "data",
        "horario",
        "produto",
        "gramatura_nominal",
        "operador",
        "responsavel",
    ],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.temp_produto.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.temp_produto.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="temp_produto",
    nome="PAC 04-C - Temperatura dos Produtos na Produção",
    icone="🥩",
    tabela="registros_temp_produto",
    colunas_backup=[
        "id",
        "data",
        "horario",
        "local",
        "categoria",
        "produto",
        "temperatura",
        "responsavel",
    ],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

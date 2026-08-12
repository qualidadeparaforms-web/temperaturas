from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.peso_produto.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.peso_produto.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="peso_produto",
    nome="PAC 06-D - Monitoramento de Peso (Produto Embalado)",
    icone="⚖️",
    tabela="registros_peso_produto",
    colunas_backup=[
        "id",
        "data",
        "horario",
        "produto",
        "peso_liquido_nominal",
        "peso_embalagem",
        "responsavel",
    ],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

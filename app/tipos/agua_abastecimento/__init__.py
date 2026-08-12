from app.tipos.agua_abastecimento.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.agua_abastecimento.formulario import formulario_bp
from app.tipos.base import TipoRegistro, registrar_tipo

TIPO = TipoRegistro(
    slug="agua_abastecimento",
    nome="PAC 03-A - Água de Abastecimento (Cloro e pH)",
    icone="💧",
    tabela="registros_agua_abastecimento",
    colunas_backup=["id", "data", "horario", "ponto", "ph", "cloro", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

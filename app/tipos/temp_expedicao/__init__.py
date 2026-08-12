from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.temp_expedicao.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.temp_expedicao.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="temp_expedicao",
    nome="PAC 04-D - Temperatura dos Produtos nas Câmaras de Expedição",
    icone="📦",
    tabela="registros_temp_expedicao",
    colunas_backup=["id", "data", "horario", "local", "categoria", "temperatura", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

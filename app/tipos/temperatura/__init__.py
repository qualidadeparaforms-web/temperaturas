from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.temperatura.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.temperatura.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="temperatura",
    nome="Temperatura de Processo",
    icone="🌡️",
    tabela="registros_temperatura",
    colunas_backup=["id", "data", "horario", "etapa", "temperatura", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

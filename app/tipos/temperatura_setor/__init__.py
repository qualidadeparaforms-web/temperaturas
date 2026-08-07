from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.temperatura_setor.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.temperatura_setor.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="temperatura_setor",
    nome="Temperatura de Setor/Câmara",
    icone="🧊",
    tabela="registros_temperatura_setor",
    colunas_backup=["id", "data", "horario", "setor", "temperatura", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

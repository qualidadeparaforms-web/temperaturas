from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.calibracao_phmetro.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.calibracao_phmetro.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="calibracao_phmetro",
    nome="PAC 08-C - Calibrações pHmetro",
    icone="🧪",
    tabela="registros_calibracao_phmetro",
    colunas_backup=["id", "data", "calibracao_realizada", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
    categoria="semanal",
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

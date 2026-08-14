from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.ventilacao.dashboard import adicionar_planilha, contar, dashboard_bp, linhas_combinadas
from app.tipos.ventilacao.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="ventilacao",
    nome="PAC 08-E - Monitoramento da Ventilação",
    icone="🌬️",
    tabela="registros_ventilacao",
    colunas_backup=["id", "data", "grupo", "setor", "status", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
    categoria="semanal",
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

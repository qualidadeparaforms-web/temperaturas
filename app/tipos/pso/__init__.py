from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.pso.dashboard import adicionar_planilha, contar, dashboard_bp, linhas_combinadas
from app.tipos.pso.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="pso",
    nome="PAC 11 - Monitoramento dos PSO's",
    icone="🧼",
    tabela="registros_pso",
    colunas_backup=["id", "data", "pso", "status", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

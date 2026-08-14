from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.iluminacao.dashboard import adicionar_planilha, contar, dashboard_bp, linhas_combinadas
from app.tipos.iluminacao.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="iluminacao",
    nome="PAC 08-D - Monitoramento da Iluminação",
    icone="💡",
    tabela="registros_iluminacao",
    colunas_backup=["id", "data", "setor", "local", "lux_necessario", "lux_obtido", "status"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
    categoria="mensal",
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

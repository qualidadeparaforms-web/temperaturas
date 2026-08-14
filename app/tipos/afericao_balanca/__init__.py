from app.tipos.afericao_balanca.dashboard import adicionar_planilha, contar, dashboard_bp, linhas_combinadas
from app.tipos.afericao_balanca.formulario import formulario_bp
from app.tipos.afericao_balanca.models import seed_balancas_se_vazio
from app.tipos.base import TipoRegistro, registrar_tipo

TIPO = TipoRegistro(
    slug="afericao_balanca",
    nome="PAC 08-G - Aferição das Balanças",
    icone="⚙️",
    tabela="registros_afericao_balanca",
    colunas_backup=["id", "balanca_id", "data", "leitura", "status", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
    categoria="semanal",
    seed=seed_balancas_se_vazio,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

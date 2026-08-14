from app.tipos.afericao_termometro.dashboard import adicionar_planilha, contar, dashboard_bp, linhas_combinadas
from app.tipos.afericao_termometro.formulario import formulario_bp
from app.tipos.afericao_termometro.models import seed_termometros_se_vazio
from app.tipos.base import TipoRegistro, registrar_tipo

TIPO = TipoRegistro(
    slug="afericao_termometro",
    nome="PAC 08-F - Aferição dos Termômetros",
    icone="🎯",
    tabela="registros_afericao_termometro",
    colunas_backup=[
        "id", "termometro_id", "data",
        "temp_quente_padrao", "temp_quente_equipamento",
        "temp_fria_padrao", "temp_fria_equipamento",
        "status", "responsavel",
    ],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
    categoria="semanal",
    seed=seed_termometros_se_vazio,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

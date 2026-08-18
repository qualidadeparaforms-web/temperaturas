from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.limpeza_agulhas_injetora.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.limpeza_agulhas_injetora.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="limpeza_agulhas_injetora",
    nome="PAC 01-C - Limpeza Interna das Agulhas da Máquina Injetora",
    icone="🧽",
    tabela="registros_limpeza_agulhas_injetora",
    colunas_backup=["id", "data", "agulhas_limpas", "sem_residuos", "operador", "controle_qualidade"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

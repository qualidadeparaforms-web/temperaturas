from app.tipos.base import TipoRegistro, registrar_tipo
from app.tipos.integridade_componente.dashboard import (
    adicionar_planilha,
    contar,
    dashboard_bp,
    linhas_combinadas,
)
from app.tipos.integridade_componente.formulario import formulario_bp

TIPO = TipoRegistro(
    slug="integridade_componente",
    nome="PAC 17 - Monitoramento de Integridade de Componentes de Máquinas",
    icone="🪡",
    tabela="registros_integridade_componente",
    colunas_backup=["id", "data", "equipamento", "momento", "horario", "status", "responsavel"],
    contar=contar,
    linhas_combinadas=linhas_combinadas,
    adicionar_planilha=adicionar_planilha,
)

registrar_tipo(TIPO, formulario_bp, dashboard_bp)

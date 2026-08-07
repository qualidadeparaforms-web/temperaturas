"""
Registro central dos "tipos de registro" (Temperatura de Processo,
e outros que forem adicionados no futuro).

Cada tipo de registro é um pacote em app/tipos/<slug>/ que, ao ser
importado, monta um TipoRegistro e chama registrar_tipo(). Veja
app/tipos/temperatura/__init__.py como referência, e o README.md
("Como adicionar um novo tipo de registro") para o passo a passo.
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable


@dataclass
class TipoRegistro:
    slug: str
    """Identificador curto usado em URLs, filtros e nomes de blueprint
    (ex.: "temperatura"). Precisa ser único, minúsculo, sem espaços."""

    nome: str
    """Nome de exibição (ex.: "Temperatura de Processo")."""

    icone: str
    """Emoji exibido no botão da tela inicial e nos cartões do painel."""

    tabela: str
    """Nome da tabela SQL correspondente — usado pelo backup.py para
    gerar o CSV deste tipo sem depender do contexto da aplicação Flask."""

    colunas_backup: list
    """Colunas (na ordem) a exportar no CSV de backup deste tipo."""

    contar: Callable[[date, date], int]
    """(inicio, fim) -> quantidade de registros no período. Usado nos
    cartões de resumo da visão combinada do painel."""

    linhas_combinadas: Callable[[date, date], list]
    """(inicio, fim) -> lista de dicts padronizados para a tabela da
    visão combinada do painel:
    {"tipo": nome, "icone": icone, "data": "dd/mm/aaaa", "horario": "HH:MM",
     "resumo": texto curto, "conforme": True/False/None, "ordenacao": datetime}
    """

    adicionar_planilha: Callable
    """(workbook, inicio, fim, filtros_extra) -> None. Acrescenta ao
    workbook (openpyxl) uma aba com os dados deste tipo no período,
    já formatada (cabeçalho, destaque de não conformidade etc.)."""


TIPOS_REGISTRO: list[TipoRegistro] = []
_BLUEPRINTS: list = []


def registrar_tipo(tipo: TipoRegistro, *blueprints) -> None:
    """Chamado por cada pacote de tipo ao ser importado."""
    TIPOS_REGISTRO.append(tipo)
    _BLUEPRINTS.extend(blueprints)


def obter_tipo(slug: str) -> TipoRegistro | None:
    return next((t for t in TIPOS_REGISTRO if t.slug == slug), None)


def blueprints_registrados() -> list:
    return list(_BLUEPRINTS)

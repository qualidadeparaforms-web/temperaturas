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

# Categorias de frequência — usadas pra agrupar os tipos na tela
# "Categoria de Registro" (Diárias/Semanais/Mensais), o passo entre a
# splash e a grade de tipos. Hoje todo tipo existente é diário; um
# tipo semanal/mensal novo só precisa passar categoria="semanal" (ou
# "mensal") no TipoRegistro do seu __init__.py — nenhuma outra
# mudança estrutural é necessária, ele aparece sozinho na tela certa
# (ver app/routes/home.py).
CATEGORIAS_VALIDAS = ("diaria", "semanal", "mensal")


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

    categoria: str = "diaria"
    """Frequência do tipo — "diaria", "semanal" ou "mensal" (ver
    CATEGORIAS_VALIDAS). Decide em qual das três telas de "Categoria de
    Registro" o tipo aparece. Todo tipo já existente é diário, por
    isso o padrão — tipos novos de outra frequência passam
    categoria="semanal"/"mensal" explicitamente."""

    def __post_init__(self) -> None:
        if self.categoria not in CATEGORIAS_VALIDAS:
            raise ValueError(
                f"categoria inválida para o tipo '{self.slug}': {self.categoria!r} "
                f"(use uma de {CATEGORIAS_VALIDAS})"
            )


TIPOS_REGISTRO: list[TipoRegistro] = []
_BLUEPRINTS: list = []


def registrar_tipo(tipo: TipoRegistro, *blueprints) -> None:
    """Chamado por cada pacote de tipo ao ser importado."""
    TIPOS_REGISTRO.append(tipo)
    _BLUEPRINTS.extend(blueprints)


def obter_tipo(slug: str) -> TipoRegistro | None:
    return next((t for t in TIPOS_REGISTRO if t.slug == slug), None)


def tipos_por_categoria(categoria: str) -> list[TipoRegistro]:
    """Tipos registrados de uma frequência ("diaria"/"semanal"/
    "mensal"), na ordem em que foram importados — usado pela tela de
    "Categoria de Registro" (app/routes/home.py)."""
    return [t for t in TIPOS_REGISTRO if t.categoria == categoria]


def blueprints_registrados() -> list:
    return list(_BLUEPRINTS)

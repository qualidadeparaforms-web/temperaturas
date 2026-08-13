from flask import Blueprint, render_template

from app.tipos import tipos_por_categoria

home_bp = Blueprint("home", __name__)

# Info de exibição de cada categoria de frequência (ver
# app/tipos/base.py, CATEGORIAS_VALIDAS/TipoRegistro.categoria).
# "adjetivo" é usado na mensagem "Nenhum registro <adjetivo> cadastrado
# ainda" das categorias ainda sem tipo algum.
CATEGORIAS_INFO = {
    "diaria": {"nome": "Diárias", "adjetivo": "diário", "icone": "📆"},
    "semanal": {"nome": "Semanais", "adjetivo": "semanal", "icone": "🗓️"},
    "mensal": {"nome": "Mensais", "adjetivo": "mensal", "icone": "📅"},
}


@home_bp.route("/")
def splash():
    """Tela de splash/inicialização — a primeira coisa que aparece ao
    acessar a URL raiz do sistema. Puramente estática: depois de
    alguns segundos, redireciona sozinha (via JS, com <meta
    http-equiv="refresh"> como reforço sem JS) para a tela de
    categoria de registro (`index`, em /inicio). Não mexe em nenhuma
    lógica de formulário/banco — só a porta de entrada.
    """
    return render_template("splash.html")


@home_bp.route("/inicio")
def index():
    """Tela de "Categoria de Registro" — Diárias / Semanais / Mensais.
    Primeira escolha depois da splash; cada botão leva à grade de
    tipos daquela frequência (ver `_tela_categoria`)."""
    return render_template("home_categorias.html", categorias=CATEGORIAS_INFO)


@home_bp.route("/diarias")
def diarias():
    """Grade de tipos diários — a tela que já existia antes desta
    reorganização (todos os 9 tipos de hoje são diários)."""
    return _tela_categoria("diaria")


@home_bp.route("/semanais")
def semanais():
    """Grade de tipos semanais — vazia por enquanto. Um tipo novo
    passando categoria="semanal" no seu TipoRegistro aparece aqui
    sozinho, sem precisar mexer nesta rota nem no template."""
    return _tela_categoria("semanal")


@home_bp.route("/mensais")
def mensais():
    """Grade de tipos mensais — mesma ideia de `semanais`, pra
    categoria="mensal"."""
    return _tela_categoria("mensal")


def _tela_categoria(categoria: str):
    info = CATEGORIAS_INFO[categoria]
    tipos = tipos_por_categoria(categoria)
    return render_template(
        "home_tipos.html",
        tipos=tipos,
        categoria_nome=info["nome"],
        categoria_adjetivo=info["adjetivo"],
    )

from flask import Blueprint, render_template

from app.tipos import TIPOS_REGISTRO

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def splash():
    """Tela de splash/inicialização — a primeira coisa que aparece ao
    acessar a URL raiz do sistema. Puramente estática: depois de
    alguns segundos, redireciona sozinha (via JS, com <meta
    http-equiv="refresh"> como reforço sem JS) para a tela de seleção
    de tipo (`index`, agora em /inicio). Não mexe em nenhuma lógica de
    formulário/banco — só a porta de entrada.
    """
    return render_template("splash.html")


@home_bp.route("/inicio")
def index():
    """Tela inicial: grade de botões, um para cada tipo de registro."""
    return render_template("home.html", tipos=TIPOS_REGISTRO)

from flask import Blueprint, render_template

from app.tipos import TIPOS_REGISTRO

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    """Tela inicial: grade de botões, um para cada tipo de registro."""
    return render_template("home.html", tipos=TIPOS_REGISTRO)

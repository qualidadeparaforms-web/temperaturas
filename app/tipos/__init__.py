from app.tipos.base import (  # noqa: F401
    TIPOS_REGISTRO,
    TipoRegistro,
    blueprints_registrados,
    obter_tipo,
    registrar_tipo,
    tipos_por_categoria,
)

# Cada tipo de registro se cadastra sozinho ao ser importado aqui
# (chama registrar_tipo() no seu __init__.py). Para adicionar um novo
# tipo, crie o pacote app/tipos/<slug>/ e importe-o abaixo — veja o
# README.md ("Como adicionar um novo tipo de registro").
from app.tipos import temperatura  # noqa: E402,F401
from app.tipos import temperatura_setor  # noqa: E402,F401
from app.tipos import agua_abastecimento  # noqa: E402,F401
from app.tipos import temp_produto  # noqa: E402,F401
from app.tipos import temp_expedicao  # noqa: E402,F401
from app.tipos import peso_produto  # noqa: E402,F401
from app.tipos import gramatura  # noqa: E402,F401
from app.tipos import pso  # noqa: E402,F401
from app.tipos import integridade_componente  # noqa: E402,F401

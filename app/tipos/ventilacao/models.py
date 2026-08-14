from datetime import datetime

from app.extensions import db

# Lista fixa dos 22 setores avaliados, divididos em 2 grupos — a
# mesma divisão da planilha em papel original. A ordem de cada lista
# é a ordem de exibição na tela de registro.
SETORES_POR_GRUPO = {
    "Setor Produção": [
        "Selagem",
        "Túnel de congelamento 3",
        "Embalagem primária",
        "Setor de carne moída",
        "Sala de lavação de caixas",
        "Depósito de caixas limpas",
        "Sala de esterilização de facas",
        "Câmara de matéria-prima (carcaças)",
        "Sala de cortes",
        "Túnel de congelamento 4",
        "Setor de temperados",
        "Barreira Sanitária Principal",
        "Depósito de condimentos (almoxarifado)",
        "Depósito de embalagens primárias (almoxarifado)",
    ],
    "Setor Embalagem Secundária e Expedição": [
        "Barreira Sanitária Expedição",
        "Câmara de congelados 1",
        "Câmara de congelados 2",
        "Abertura de caixas de papelão",
        "Expedição",
        "Câmara de resfriados",
        "Depósito de embalagens secundárias",
        "Embalagem Secundária",
    ],
}

GRUPOS = list(SETORES_POR_GRUPO.keys())

# Achatada em pares (grupo, setor), na ordem de exibição — usada pra
# gerar os campos do formulário (um índice global por setor) e pra
# percorrer a lista inteira sem se importar com o agrupamento.
SETORES_COM_GRUPO = [
    (grupo, setor) for grupo, setores in SETORES_POR_GRUPO.items() for setor in setores
]
SETORES = [setor for _, setor in SETORES_COM_GRUPO]
GRUPO_POR_SETOR = {setor: grupo for grupo, setor in SETORES_COM_GRUPO}

STATUS_VALIDOS = ("C", "NC")


class RegistroVentilacao(db.Model):
    """Um registro por setor por checagem semanal — uma checagem
    completa gera 22 linhas (uma por setor), todas com a mesma data e
    responsável. Cada setor recebe um único status geral (C ou NC),
    cobrindo em conjunto os 4 critérios do PAC 08-E (condensação,
    odores, gelo, contra-fluxo de ar) — o formulário não distingue
    qual critério falhou, só se o setor está conforme como um todo.

    Diferente da maioria dos outros tipos, `data` não tem valor
    automático: é semanal, então o usuário escolhe a data da checagem
    (pode não ser hoje)."""

    __tablename__ = "registros_ventilacao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    grupo = db.Column(db.String(80), nullable=False)
    setor = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(2), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def conforme(self) -> bool:
        return self.status == "C"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "grupo": self.grupo,
            "setor": self.setor,
            "status": self.status,
            "responsavel": self.responsavel,
            "conforme": self.conforme,
        }

from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

# Lista fixa dos PSOs monitorados, na ordem de exibição na tela de
# registro. A numeração pula do PSO 6 pro PSO 8 de propósito — não
# existe "PSO 7" no procedimento original.
PSOS = [
    "PSO 1 - Troca de Facas e Chairas",
    "PSO 2 - Toalete das Peças",
    "PSO 3 - Separação, Identificação e Uso dos Produtos",
    "PSO 4 - Acúmulo de Produtos",
    "PSO 5 - Cobertura e Identificação dos Produtos",
    "PSO 6 - Utilização de Caixas Plásticas",
    "PSO 8 - Corte de Carcaças na Câmara",
]

STATUS_VALIDOS = ("C", "NC")


class RegistroPso(db.Model):
    """Um registro por PSO por dia — um checklist completo gera 7
    linhas (uma por PSO), todas com a mesma data e responsável."""

    __tablename__ = "registros_pso"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    pso = db.Column(db.String(80), nullable=False, index=True)
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
            "pso": self.pso,
            "status": self.status,
            "responsavel": self.responsavel,
            "conforme": self.conforme,
        }

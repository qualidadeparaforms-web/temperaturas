from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

# Faixas de conformidade — fixas no código.
PH_MIN = 6.0
PH_MAX = 9.0
CLORO_MIN = 0.2
CLORO_MAX = 5.0

# Pontos de coleta — lista fixa, selecionada por botões na tela de
# registro (mesmo padrão de ETAPAS/SETORES dos outros tipos). Na
# prática é monitorado 1 ponto por dia, em rodízio entre estes.
PONTOS = [
    "Sala de Cortes",
    "Lavação de Caixas",
    "Lavação de Utensílios",
    "Setor Carne Moída",
    "Setor de Selagem",
    "Barreira Sanitária Expedição",
    "Barreira Sanitária Sala de Carcaças",
    "Abertura de Carnes",
    "Setor de Industrializados",
]


class RegistroAguaAbastecimento(db.Model):
    __tablename__ = "registros_agua_abastecimento"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    horario = db.Column(
        db.Time, nullable=False, default=lambda: agora_brasilia().time().replace(microsecond=0)
    )
    ponto = db.Column(db.String(120), nullable=False)
    ph = db.Column(db.Float, nullable=False)
    cloro = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def ph_conforme(self) -> bool:
        return PH_MIN <= self.ph <= PH_MAX

    @property
    def cloro_conforme(self) -> bool:
        return CLORO_MIN <= self.cloro <= CLORO_MAX

    @property
    def conforme(self) -> bool:
        return self.ph_conforme and self.cloro_conforme

    @property
    def situacao(self) -> str:
        """Descrição do desvio (qual dos dois valores está fora),
        usada na tela de registro, no painel e na exportação."""
        problemas = []
        if not self.ph_conforme:
            problemas.append("pH")
        if not self.cloro_conforme:
            problemas.append("Cloro")
        if not problemas:
            return "Conforme"
        return " e ".join(problemas) + " fora do padrão"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "ponto": self.ponto,
            "ph": self.ph,
            "cloro": self.cloro,
            "responsavel": self.responsavel,
            "ph_conforme": self.ph_conforme,
            "cloro_conforme": self.cloro_conforme,
            "conforme": self.conforme,
            "situacao": self.situacao,
        }

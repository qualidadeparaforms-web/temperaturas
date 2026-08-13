from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

# Etapas do processo, na ordem em que devem aparecer na tela de registro.
ETAPAS = ["Aparas", "Bifes", "Moídas", "Temperados", "Embalagem", "Selagem"]

# Faixas de temperatura consideradas conformes (limite máximo, inclusive).
LIMITES_TEMPERATURA = {
    "Moídas": 4.0,
}
LIMITE_PADRAO = 7.0  # Aparas, Bifes, Temperados, Embalagem, Selagem


def limite_para_etapa(etapa: str) -> float:
    """Retorna a temperatura máxima (°C) considerada conforme para a etapa."""
    return LIMITES_TEMPERATURA.get(etapa, LIMITE_PADRAO)


def is_conforme(etapa: str, temperatura: float) -> bool:
    """Um registro é conforme quando a temperatura é <= limite da etapa."""
    return temperatura <= limite_para_etapa(etapa)


class RegistroTemperatura(db.Model):
    __tablename__ = "registros_temperatura"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    horario = db.Column(
        db.Time, nullable=False, default=lambda: agora_brasilia().time().replace(microsecond=0)
    )
    etapa = db.Column(db.String(20), nullable=False, index=True)
    temperatura = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def limite(self) -> float:
        return limite_para_etapa(self.etapa)

    @property
    def conforme(self) -> bool:
        return is_conforme(self.etapa, self.temperatura)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "etapa": self.etapa,
            "temperatura": self.temperatura,
            "responsavel": self.responsavel,
            "limite": self.limite,
            "conforme": self.conforme,
        }

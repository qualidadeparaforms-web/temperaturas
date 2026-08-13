from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

# Setores/câmaras monitorados e seus limites máximos de temperatura
# (°C) — fixos no código, não editáveis pelo usuário na tela. A ordem
# aqui é a mesma ordem de exibição na tela de registro.
LIMITES_SETOR = {
    "Câmara 1 - Estoque de congelados": -18.0,
    "Câmara 2 - Estoque de congelados": -18.0,
    "Setor de expedição": 16.0,
    "Câmara 3 - Estoque de resfriados": 4.0,
    "Túnel de congelamento 3": -25.0,
    "Setor de selagem": 16.0,
    "Túnel de congelamento 2 - Giro freezer": -25.0,
    "Setor de embalagem primária": 16.0,
    "Setor de industrializados": 10.0,
    "Câmara de industrializados": 4.0,
    "Câmara de retalhos 2": 4.0,
    "Setor de carne moída": 10.0,
    "Câmara de retalhos 1": 4.0,
    "Câmara de carcaças": 4.0,
    "Setor de cortes": 16.0,
    "Túnel de congelamento 4 - Serra": -25.0,
    "Setor de temperados": 16.0,
}
SETORES = list(LIMITES_SETOR.keys())


def limite_para_setor(setor: str) -> float:
    """Limite máximo (°C) considerado conforme para o setor."""
    return LIMITES_SETOR[setor]


def is_conforme(setor: str, temperatura: float) -> bool:
    """Um registro é conforme quando a temperatura é <= limite do setor."""
    return temperatura <= limite_para_setor(setor)


class RegistroTemperaturaSetor(db.Model):
    __tablename__ = "registros_temperatura_setor"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    horario = db.Column(
        db.Time, nullable=False, default=lambda: agora_brasilia().time().replace(microsecond=0)
    )
    setor = db.Column(db.String(60), nullable=False, index=True)
    temperatura = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def limite(self) -> float:
        return limite_para_setor(self.setor)

    @property
    def conforme(self) -> bool:
        return is_conforme(self.setor, self.temperatura)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "setor": self.setor,
            "temperatura": self.temperatura,
            "responsavel": self.responsavel,
            "limite": self.limite,
            "conforme": self.conforme,
        }

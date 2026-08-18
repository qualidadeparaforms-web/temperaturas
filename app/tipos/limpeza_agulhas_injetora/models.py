from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

STATUS_VALIDOS = ("C", "NC")


class RegistroLimpezaAgulhasInjetora(db.Model):
    """PAC 01-C — checklist diário com 2 critérios independentes
    (agulhas limpas, sem resíduos), cada um C ou NC, e dois
    responsáveis distintos: `operador` (quem fez a limpeza) e
    `controle_qualidade` (quem registrou/validou). Sem `horario` —
    igual ao PAC 11 (PSO), é um checklist do dia, não uma medição
    pontual."""

    __tablename__ = "registros_limpeza_agulhas_injetora"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    agulhas_limpas = db.Column(db.String(2), nullable=False)
    sem_residuos = db.Column(db.String(2), nullable=False)
    operador = db.Column(db.String(100), nullable=False)
    controle_qualidade = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def conforme(self) -> bool:
        """Conforme só se os dois critérios estiverem C — qualquer um
        em NC já torna o registro inteiro não conforme."""
        return self.agulhas_limpas == "C" and self.sem_residuos == "C"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "agulhas_limpas": self.agulhas_limpas,
            "sem_residuos": self.sem_residuos,
            "operador": self.operador,
            "controle_qualidade": self.controle_qualidade,
            "conforme": self.conforme,
        }

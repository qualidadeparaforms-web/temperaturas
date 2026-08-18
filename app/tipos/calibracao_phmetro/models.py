from datetime import datetime

from app.extensions import db


class RegistroCalibracaoPhmetro(db.Model):
    """PAC 08-C — confirmação simples: a calibração semanal do
    pHmetro (soluções pH 7, pH 4 e pH 10) foi feita ou não naquele
    dia, sem detalhar cada solução individualmente."""

    __tablename__ = "registros_calibracao_phmetro"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    calibracao_realizada = db.Column(db.Boolean, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def conforme(self) -> bool:
        """"Não" indica que a calibração da semana não foi feita —
        tratado como não conforme, destacado em vermelho no painel."""
        return self.calibracao_realizada

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "calibracao_realizada": self.calibracao_realizada,
            "calibracao_realizada_texto": "Sim" if self.calibracao_realizada else "Não",
            "responsavel": self.responsavel,
            "conforme": self.conforme,
        }

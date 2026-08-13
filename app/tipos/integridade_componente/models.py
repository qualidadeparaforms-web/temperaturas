from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia

# Equipamentos monitorados (antigos PAC 17-A, 17-C e 17-G, unificados
# neste único tipo), cada um com o nome do componente avaliado e os
# momentos de checagem que se aplicam a ele — fixos no código.
EQUIPAMENTOS_INFO = {
    "Agulhas Tenderizadora": {
        "componente": "Agulhas",
        "momentos": ["Início", "Final"],
    },
    "Máquina de Cubos e Iscas": {
        "componente": "Lâminas de Corte",
        "momentos": ["Início", "Troca de Lâminas", "Final"],
    },
    "Agulhas Injetora": {
        "componente": "Agulhas",
        "momentos": ["Início", "Final"],
    },
}
EQUIPAMENTOS = list(EQUIPAMENTOS_INFO.keys())

STATUS_VALIDOS = ("C", "NC")


def componente_do_equipamento(equipamento: str) -> str:
    return EQUIPAMENTOS_INFO[equipamento]["componente"]


def momentos_do_equipamento(equipamento: str) -> list:
    return EQUIPAMENTOS_INFO[equipamento]["momentos"]


class RegistroIntegridadeComponente(db.Model):
    """Um registro por checagem (equipamento + momento). O horário é
    digitado pelo usuário — diferente dos demais tipos, a checagem
    pode ser registrada depois do momento real (ex.: anotada no papel
    e digitada mais tarde)."""

    __tablename__ = "registros_integridade_componente"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    equipamento = db.Column(db.String(40), nullable=False, index=True)
    momento = db.Column(db.String(30), nullable=False)
    horario = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(2), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def componente(self) -> str:
        return componente_do_equipamento(self.equipamento)

    @property
    def conforme(self) -> bool:
        return self.status == "C"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "equipamento": self.equipamento,
            "componente": self.componente,
            "momento": self.momento,
            "status": self.status,
            "responsavel": self.responsavel,
            "conforme": self.conforme,
        }


class VerificacaoRT(db.Model):
    """Conferência rápida e independente, feita pelo próprio RT
    (Raunir) ao longo do dia — só marca "passei aqui e conferi",
    sem status de conformidade nem formulário longo."""

    __tablename__ = "verificacoes_rt"

    id = db.Column(db.Integer, primary_key=True)
    equipamento = db.Column(db.String(40), nullable=False, index=True)
    data_hora = db.Column(db.DateTime, nullable=False, default=agora_brasilia)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "equipamento": self.equipamento,
            "data": self.data_hora.strftime("%d/%m/%Y"),
            "horario": self.data_hora.strftime("%H:%M"),
        }

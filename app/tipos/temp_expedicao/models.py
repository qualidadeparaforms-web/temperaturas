from datetime import date, datetime

from app.extensions import db

# Locais monitorados — lista fixa.
LOCAIS = [
    "Câmara de Congelado 1",
    "Câmara de Congelado 2",
    "Câmara de Resfriados",
    "Matéria Prima - Quebra de Gelo",
]

# Só estes locais têm o conceito de categoria; "Matéria Prima -
# Quebra de Gelo" tem um único limite, sem distinção de categoria.
LOCAIS_COM_CATEGORIA = [
    "Câmara de Congelado 1",
    "Câmara de Congelado 2",
    "Câmara de Resfriados",
]
LOCAL_SEM_CATEGORIA = "Matéria Prima - Quebra de Gelo"

CATEGORIAS = ["Corte", "Carne Moída"]

# Limite máximo de temperatura (°C) por combinação (local, categoria)
# — fixo no código. O local sem categoria usa chave (local, None).
LIMITES = {
    ("Câmara de Congelado 1", "Corte"): -12.0,
    ("Câmara de Congelado 1", "Carne Moída"): -18.0,
    ("Câmara de Congelado 2", "Corte"): -12.0,
    ("Câmara de Congelado 2", "Carne Moída"): -18.0,
    ("Câmara de Resfriados", "Corte"): 7.0,
    ("Câmara de Resfriados", "Carne Moída"): 4.0,
    (LOCAL_SEM_CATEGORIA, None): -8.0,
}


def limite_para(local: str, categoria: str | None) -> float:
    chave = (local, categoria if local in LOCAIS_COM_CATEGORIA else None)
    return LIMITES[chave]


def is_conforme(local: str, categoria: str | None, temperatura: float) -> bool:
    return temperatura <= limite_para(local, categoria)


class RegistroTempExpedicao(db.Model):
    __tablename__ = "registros_temp_expedicao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=date.today)
    horario = db.Column(
        db.Time, nullable=False, default=lambda: datetime.now().time().replace(microsecond=0)
    )
    local = db.Column(db.String(60), nullable=False)
    # Nulo para o único local sem esse conceito (Matéria Prima).
    categoria = db.Column(db.String(30), nullable=True)
    temperatura = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def limite(self) -> float:
        return limite_para(self.local, self.categoria)

    @property
    def conforme(self) -> bool:
        return is_conforme(self.local, self.categoria, self.temperatura)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "local": self.local,
            "categoria": self.categoria or "",
            "temperatura": self.temperatura,
            "responsavel": self.responsavel,
            "limite": self.limite,
            "conforme": self.conforme,
        }

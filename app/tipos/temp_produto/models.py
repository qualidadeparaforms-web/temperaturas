from datetime import date, datetime

from app.extensions import db

# Local de coleta — lista fixa.
LOCAIS = ["Produto em Processo", "Produto na Câmara de Retalhos"]

# Categoria do produto e seu limite máximo de temperatura (°C),
# fixos no código.
LIMITES_CATEGORIA = {
    "Corte": 7.0,
    "Carne Moída": 4.0,
}
CATEGORIAS = list(LIMITES_CATEGORIA.keys())


def limite_para_categoria(categoria: str) -> float:
    return LIMITES_CATEGORIA[categoria]


def is_conforme(categoria: str, temperatura: float) -> bool:
    """Um registro é conforme quando a temperatura é <= limite da categoria."""
    return temperatura <= limite_para_categoria(categoria)


class RegistroTempProduto(db.Model):
    __tablename__ = "registros_temp_produto"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=date.today)
    horario = db.Column(
        db.Time, nullable=False, default=lambda: datetime.now().time().replace(microsecond=0)
    )
    local = db.Column(db.String(60), nullable=False)
    categoria = db.Column(db.String(30), nullable=False, index=True)
    produto = db.Column(db.String(80), nullable=False)
    temperatura = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def limite(self) -> float:
        return limite_para_categoria(self.categoria)

    @property
    def conforme(self) -> bool:
        return is_conforme(self.categoria, self.temperatura)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "local": self.local,
            "categoria": self.categoria,
            "produto": self.produto,
            "temperatura": self.temperatura,
            "responsavel": self.responsavel,
            "limite": self.limite,
            "conforme": self.conforme,
        }

from datetime import date, datetime

from app.extensions import db


class RegistroPesoProduto(db.Model):
    """Um registro por produto avaliado no dia — reúne várias
    pesagens individuais (ver PesagemIndividual)."""

    __tablename__ = "registros_peso_produto"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=date.today)
    horario = db.Column(
        db.Time, nullable=False, default=lambda: datetime.now().time().replace(microsecond=0)
    )
    produto = db.Column(db.String(80), nullable=False)
    peso_liquido_nominal = db.Column(db.Float, nullable=False)
    peso_embalagem = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    pesagens = db.relationship(
        "PesagemIndividual",
        backref="registro",
        cascade="all, delete-orphan",
        order_by="PesagemIndividual.id",
    )

    @property
    def peso_minimo(self) -> float:
        """Padrão mínimo de peso: líquido nominal + embalagem."""
        return self.peso_liquido_nominal + self.peso_embalagem

    @property
    def total_pesagens(self) -> int:
        return len(self.pesagens)

    @property
    def total_nc(self) -> int:
        return sum(1 for p in self.pesagens if not p.conforme)

    @property
    def percentual_conforme(self) -> float:
        total = self.total_pesagens
        if total == 0:
            return 100.0
        return round((total - self.total_nc) / total * 100, 1)

    @property
    def conforme(self) -> bool:
        """O produto/dia é considerado conforme quando nenhuma pesagem
        individual deu NC."""
        return self.total_nc == 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "horario": self.horario.strftime("%H:%M"),
            "produto": self.produto,
            "peso_liquido_nominal": self.peso_liquido_nominal,
            "peso_embalagem": self.peso_embalagem,
            "peso_minimo": self.peso_minimo,
            "responsavel": self.responsavel,
            "total_pesagens": self.total_pesagens,
            "total_nc": self.total_nc,
            "percentual_conforme": self.percentual_conforme,
            "conforme": self.conforme,
        }


class PesagemIndividual(db.Model):
    __tablename__ = "pesagens_individuais"

    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(
        db.Integer, db.ForeignKey("registros_peso_produto.id"), nullable=False, index=True
    )
    peso_medido = db.Column(db.Float, nullable=False)

    @property
    def conforme(self) -> bool:
        """NC (não conforme) quando o peso medido é menor que o padrão
        mínimo (líquido nominal + embalagem) do registro."""
        return self.peso_medido >= self.registro.peso_minimo

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "peso_medido": self.peso_medido,
            "conforme": self.conforme,
        }

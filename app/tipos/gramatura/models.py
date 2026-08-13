from datetime import datetime

from app.extensions import db
from app.timezone_utils import agora_brasilia


class RegistroGramatura(db.Model):
    """Um registro por produto avaliado no dia — reúne várias
    pesagens individuais (ver PesagemIndividualGramatura)."""

    __tablename__ = "registros_gramatura"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=lambda: agora_brasilia().date())
    horario = db.Column(
        db.Time, nullable=False, default=lambda: agora_brasilia().time().replace(microsecond=0)
    )
    produto = db.Column(db.String(80), nullable=False)
    gramatura_minima = db.Column(db.Float, nullable=False)
    gramatura_maxima = db.Column(db.Float, nullable=False)
    operador = db.Column(db.String(100), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    pesagens = db.relationship(
        "PesagemIndividualGramatura",
        backref="registro",
        cascade="all, delete-orphan",
        order_by="PesagemIndividualGramatura.id",
    )

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
            "gramatura_minima": self.gramatura_minima,
            "gramatura_maxima": self.gramatura_maxima,
            "operador": self.operador,
            "responsavel": self.responsavel,
            "total_pesagens": self.total_pesagens,
            "total_nc": self.total_nc,
            "percentual_conforme": self.percentual_conforme,
            "conforme": self.conforme,
        }


class PesagemIndividualGramatura(db.Model):
    __tablename__ = "pesagens_individuais_gramatura"

    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(
        db.Integer, db.ForeignKey("registros_gramatura.id"), nullable=False, index=True
    )
    peso_medido = db.Column(db.Float, nullable=False)

    @property
    def conforme(self) -> bool:
        """NC (não conforme) quando o peso medido cai fora da faixa
        [gramatura_minima, gramatura_maxima] do registro — qualquer
        valor abaixo do mínimo ou acima do máximo é NC.

        Registros legados (criados antes da faixa mín/máx existir e
        migrados automaticamente sem dado histórico pra preencher —
        ver _migrar_colunas_faltantes em app/__init__.py) ficam com
        gramatura_minima/gramatura_maxima nulos. Tratados como NC por
        segurança: sem um padrão de referência, não dá pra confirmar
        conformidade."""
        if self.registro.gramatura_minima is None or self.registro.gramatura_maxima is None:
            return False
        return self.registro.gramatura_minima <= self.peso_medido <= self.registro.gramatura_maxima

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "peso_medido": self.peso_medido,
            "conforme": self.conforme,
        }

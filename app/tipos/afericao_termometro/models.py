from datetime import datetime

from app.extensions import db

# Termômetro padrão de referência usado em toda aferição — não é um
# equipamento cadastrado (não tem linha própria em "termometros"),
# só um código fixo mostrado na tela pra contexto.
TERMOMETRO_PADRAO_CODIGO = "AK240607938"

# Variação aceitável entre padrão e equipamento, em °C — fixa, igual
# para todos os equipamentos e para as duas leituras (quente e fria).
DIFERENCA_MAXIMA_C = 1.0


def status_para_leituras(
    temp_quente_padrao: float,
    temp_quente_equipamento: float,
    temp_fria_padrao: float,
    temp_fria_equipamento: float,
) -> str:
    """C só se AMBAS as diferenças (quente e fria) ficarem dentro da
    variação aceitável; NC se qualquer uma das duas ultrapassar."""
    diferenca_quente = abs(temp_quente_padrao - temp_quente_equipamento)
    diferenca_fria = abs(temp_fria_padrao - temp_fria_equipamento)
    if diferenca_quente <= DIFERENCA_MAXIMA_C and diferenca_fria <= DIFERENCA_MAXIMA_C:
        return "C"
    return "NC"


# Cadastro fixo dos 4 termômetros/equipamentos da fábrica — populado
# automaticamente no boot por seed_termometros_se_vazio() (só insere
# se a tabela "termometros" estiver vazia; idempotente).
TERMOMETROS_SEED = [
    {"codigo": "AK240608010", "descricao": "Reserva"},
    {"codigo": "AK240612434", "descricao": "Máquina IQF (Embalagem Primária)"},
    {"codigo": "AK180100128", "descricao": "Expedição"},
    {"codigo": "AK200515295", "descricao": "Produção"},
]


class Termometro(db.Model):
    """Cadastro mestre dos termômetros/equipamentos da fábrica (não
    inclui o termômetro padrão de referência — ver
    TERMOMETRO_PADRAO_CODIGO). Não é preenchido pelo usuário na tela
    de registro, só uma vez no boot a partir de TERMOMETROS_SEED (ver
    seed_termometros_se_vazio, chamada automaticamente via
    TipoRegistro.seed)."""

    __tablename__ = "termometros"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    descricao = db.Column(db.String(120), nullable=False)

    def rotulo(self) -> str:
        return f"{self.codigo} - {self.descricao}"

    def to_dict(self) -> dict:
        return {"id": self.id, "codigo": self.codigo, "descricao": self.descricao, "rotulo": self.rotulo()}


def seed_termometros_se_vazio() -> None:
    """Garante que a tabela `termometros` tenha o cadastro fixo. Roda
    a cada boot (ver TipoRegistro.seed em app/tipos/base.py), mas só
    insere se a tabela estiver vazia — idempotente: não duplica em
    boots seguintes, nem sobrescreve edições manuais feitas depois."""
    if Termometro.query.first() is not None:
        return
    for dados in TERMOMETROS_SEED:
        db.session.add(Termometro(**dados))
    db.session.commit()


class RegistroAfericaoTermometro(db.Model):
    """Uma SESSÃO de aferição — a leitura do termômetro padrão
    (quente e fria) é tomada uma única vez por sessão e vale pra
    todos os equipamentos comparados nela (ver `leituras`, em
    LeituraTermometroEquipamento). Antes desta reformulação, o padrão
    era lido de novo pra cada equipamento; esta é a estrutura correta
    pro fluxo real de uso: 1 leitura de padrão quente, N leituras de
    equipamento quente, 1 leitura de padrão fria, N leituras de
    equipamento fria."""

    __tablename__ = "registros_afericao_termometro"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    temp_quente_padrao = db.Column(db.Float, nullable=False)
    temp_fria_padrao = db.Column(db.Float, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    leituras = db.relationship(
        "LeituraTermometroEquipamento",
        backref="registro",
        cascade="all, delete-orphan",
        order_by="LeituraTermometroEquipamento.id",
    )

    @property
    def total_equipamentos(self) -> int:
        return len(self.leituras)

    @property
    def total_nc(self) -> int:
        return sum(1 for leitura in self.leituras if not leitura.conforme)

    @property
    def conforme(self) -> bool:
        """A sessão inteira é conforme quando nenhum equipamento deu NC."""
        return self.total_nc == 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "temp_quente_padrao": self.temp_quente_padrao,
            "temp_fria_padrao": self.temp_fria_padrao,
            "responsavel": self.responsavel,
            "total_equipamentos": self.total_equipamentos,
            "total_nc": self.total_nc,
            "conforme": self.conforme,
        }


class LeituraTermometroEquipamento(db.Model):
    """Uma linha por equipamento aferido dentro de uma sessão
    (RegistroAfericaoTermometro) — as leituras do padrão (quente e
    fria) vêm da sessão via `self.registro`, não são repetidas aqui.
    O status é sempre calculado a partir das 4 temperaturas (2 do
    equipamento + 2 herdadas da sessão via `registro`), nunca
    escolhido pelo usuário."""

    __tablename__ = "leituras_termometro_equipamento"

    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(
        db.Integer, db.ForeignKey("registros_afericao_termometro.id"), nullable=False, index=True
    )
    termometro_id = db.Column(db.Integer, db.ForeignKey("termometros.id"), nullable=False, index=True)
    temp_quente_equipamento = db.Column(db.Float, nullable=False)
    temp_fria_equipamento = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(2), nullable=False)

    termometro = db.relationship("Termometro")

    @property
    def conforme(self) -> bool:
        return self.status == "C"

    @property
    def diferenca_quente(self) -> float:
        return abs(self.registro.temp_quente_padrao - self.temp_quente_equipamento)

    @property
    def diferenca_fria(self) -> float:
        return abs(self.registro.temp_fria_padrao - self.temp_fria_equipamento)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.registro.data.strftime("%d/%m/%Y"),
            "data_iso": self.registro.data.isoformat(),
            "responsavel": self.registro.responsavel,
            "termometro_id": self.termometro_id,
            "termometro": self.termometro.rotulo() if self.termometro else "?",
            "codigo": self.termometro.codigo if self.termometro else "",
            "temp_quente_padrao": self.registro.temp_quente_padrao,
            "temp_quente_equipamento": self.temp_quente_equipamento,
            "temp_fria_padrao": self.registro.temp_fria_padrao,
            "temp_fria_equipamento": self.temp_fria_equipamento,
            "diferenca_quente": round(self.diferenca_quente, 2),
            "diferenca_fria": round(self.diferenca_fria, 2),
            "status": self.status,
            "conforme": self.conforme,
        }

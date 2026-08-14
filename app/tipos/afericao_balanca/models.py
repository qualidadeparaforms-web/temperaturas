from datetime import datetime

from app.extensions import db

# Massa de teste e faixa aceitável — fixos, iguais para todas as
# balanças cadastradas (não há configuração por balança).
MASSA_TESTE_G = 1000.0
FAIXA_MINIMA_G = 999.0
FAIXA_MAXIMA_G = 1001.0


def status_para_leitura(leitura: float) -> str:
    return "C" if FAIXA_MINIMA_G <= leitura <= FAIXA_MAXIMA_G else "NC"


# Cadastro fixo das 20 balanças da fábrica, a partir da planilha
# original — populado automaticamente no boot por
# seed_balancas_se_vazio() (só insere se a tabela "balancas" estiver
# vazia, então é seguro rodar sempre; não sobrescreve edições
# manuais feitas depois).
#
# Agrupadas por setor (mesmo padrão visual do PAC 08-E — ver
# formulario.html), preservando a ordem original all-planilha dentro
# de cada setor; "-" em numero_balanca vira None (a coluna aceita
# vazio, como pedido).
BALANCAS_SEED = [
    {"setor": "EMB. PRIMÁRIA", "equipamento": "1", "numero_balanca": "11300029",
     "numero_serie": "11155082", "marca": "Toledo", "carga_maxima": "10 kg"},
    {"setor": "EMB. PRIMÁRIA", "equipamento": "2", "numero_balanca": "11300030",
     "numero_serie": "11155083", "marca": "Toledo", "carga_maxima": "10 kg"},
    {"setor": "EMB. PRIMÁRIA", "equipamento": "4", "numero_balanca": "11300032",
     "numero_serie": "11155085", "marca": "Toledo", "carga_maxima": "10 kg"},
    {"setor": "EMB. PRIMÁRIA", "equipamento": "21", "numero_balanca": None,
     "numero_serie": "13219719", "marca": "Toledo/Prix", "carga_maxima": "5 kg"},
    {"setor": "EMB. PRIMÁRIA", "equipamento": "28", "numero_balanca": None,
     "numero_serie": "14780/2025", "marca": "Pró", "carga_maxima": "5 kg"},
    {"setor": "SUNBEEF/TERMOFORMADORA", "equipamento": "3", "numero_balanca": "11300031",
     "numero_serie": "11155084", "marca": "Toledo", "carga_maxima": "10 kg"},
    {"setor": "SALA DE TEMPERADOS", "equipamento": "7", "numero_balanca": "11271285",
     "numero_serie": "11155088", "marca": "Toledo", "carga_maxima": "100 kg"},
    {"setor": "EMB. SECUNDÁRIA", "equipamento": "8", "numero_balanca": "11271286",
     "numero_serie": "11155089", "marca": "Toledo", "carga_maxima": "100 kg"},
    {"setor": "EXPEDIÇÃO", "equipamento": "9", "numero_balanca": "10012739",
     "numero_serie": "10835256", "marca": "Toledo", "carga_maxima": "100 kg"},
    {"setor": "SALA DE CORTES", "equipamento": "10", "numero_balanca": "13027041",
     "numero_serie": "10835257", "marca": "Toledo", "carga_maxima": "100 kg"},
    {"setor": "SETOR SERRA FITA", "equipamento": "12", "numero_balanca": None,
     "numero_serie": "13359643", "marca": "Toledo/Prix", "carga_maxima": "32 kg"},
    {"setor": "SETOR DE CUBOS", "equipamento": "13", "numero_balanca": None,
     "numero_serie": "13925508", "marca": "Toledo/Prix", "carga_maxima": "10 kg"},
    {"setor": "SETOR DE CUBOS", "equipamento": "30", "numero_balanca": "16049650",
     "numero_serie": "15443/2025", "marca": "Pró", "carga_maxima": "10 kg"},
    {"setor": "SETOR DE BIFES", "equipamento": "19", "numero_balanca": None,
     "numero_serie": "12049022", "marca": "Toledo/Prix", "carga_maxima": "5 kg"},
    {"setor": "SETOR DE BIFES", "equipamento": "25", "numero_balanca": None,
     "numero_serie": "13847/2024", "marca": "Pró", "carga_maxima": "5 kg"},
    {"setor": "SETOR DE BIFES", "equipamento": "26", "numero_balanca": None,
     "numero_serie": "13846/2024", "marca": "Pró", "carga_maxima": "5 kg"},
    {"setor": "SETOR DE BIFES", "equipamento": "27", "numero_balanca": "15431063",
     "numero_serie": "14147/2024", "marca": "Pró", "carga_maxima": "5 kg"},
    {"setor": "SETOR DE BIFES", "equipamento": "29", "numero_balanca": "15733037",
     "numero_serie": "14779/2025", "marca": "Pró", "carga_maxima": "5 kg"},
    {"setor": "SETOR INDUSTRIALIZADOS", "equipamento": "23", "numero_balanca": None,
     "numero_serie": "13165536", "marca": "Toledo", "carga_maxima": "50 kg"},
    {"setor": "SETOR MOÍDAS", "equipamento": "24", "numero_balanca": None,
     "numero_serie": "13205383", "marca": "Toledo", "carga_maxima": "50 kg"},
]


class Balanca(db.Model):
    """Cadastro mestre das balanças da fábrica. Não é preenchido pelo
    usuário na tela de registro — populado uma vez no boot a partir de
    BALANCAS_SEED (ver seed_balancas_se_vazio, chamada automaticamente
    por app/__init__.py via TipoRegistro.seed)."""

    __tablename__ = "balancas"

    id = db.Column(db.Integer, primary_key=True)
    setor = db.Column(db.String(80), nullable=False, index=True)
    equipamento = db.Column(db.String(20), nullable=False)
    numero_balanca = db.Column(db.String(40), nullable=True)
    numero_serie = db.Column(db.String(40), nullable=False)
    marca = db.Column(db.String(40), nullable=False)
    carga_maxima = db.Column(db.String(20), nullable=False)

    def rotulo(self) -> str:
        """Texto de identificação curto — setor + nº do equipamento,
        já suficiente pra distinguir as 20 balanças (não repete nenhum
        número de equipamento). Usado na tela de registro, no painel
        e na matriz de exportação."""
        return f"{self.setor} — Equip. {self.equipamento}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "setor": self.setor,
            "equipamento": self.equipamento,
            "numero_balanca": self.numero_balanca,
            "numero_serie": self.numero_serie,
            "marca": self.marca,
            "carga_maxima": self.carga_maxima,
            "rotulo": self.rotulo(),
        }


def seed_balancas_se_vazio() -> None:
    """Garante que a tabela `balancas` tenha o cadastro fixo. Roda a
    cada boot (ver TipoRegistro.seed em app/tipos/base.py), mas só
    insere se a tabela estiver vazia — idempotente: não duplica em
    boots seguintes, nem sobrescreve edições manuais feitas depois."""
    if Balanca.query.first() is not None:
        return
    for dados in BALANCAS_SEED:
        db.session.add(Balanca(**dados))
    db.session.commit()


class RegistroAfericaoBalanca(db.Model):
    """Uma leitura de aferição por balança por checagem semanal. Só
    balanças com leitura preenchida naquele envio geram linha — ao
    contrário do PAC 08-E, aqui não é obrigatório preencher todas de
    uma vez (a fábrica pode aferir um subconjunto numa semana)."""

    __tablename__ = "registros_afericao_balanca"

    id = db.Column(db.Integer, primary_key=True)
    balanca_id = db.Column(db.Integer, db.ForeignKey("balancas.id"), nullable=False, index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    leitura = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(2), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    balanca = db.relationship("Balanca")

    @property
    def conforme(self) -> bool:
        return self.status == "C"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "balanca_id": self.balanca_id,
            "balanca": self.balanca.rotulo() if self.balanca else "?",
            "setor": self.balanca.setor if self.balanca else "",
            "leitura": self.leitura,
            "status": self.status,
            "responsavel": self.responsavel,
            "conforme": self.conforme,
        }

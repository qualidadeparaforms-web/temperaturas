from datetime import datetime

from app.extensions import db

# Lista fixa dos pontos de medição de luminosidade, agrupados por
# setor (mesma organização da planilha original) — cada ponto tem seu
# próprio mínimo de lux exigido, fixo. "Barreira sanitária" aparece em
# 2 setores diferentes (Sala de cortes e Expedição) com exigências
# distintas — por isso a identidade de um ponto é sempre o par
# (setor, local), nunca o local sozinho.
PONTOS_POR_SETOR = {
    "Sala de cortes": [
        ("Barreira sanitária", 220),
        ("Aparas", 540),
        ("Equipamentos", 540),
    ],
    "Lavação de utensílios": [
        ("Sala de caixas limpas", 110),
        ("Esterilização de facas", 540),
    ],
    "Setor de carne moída": [
        ("Moedor", 540),
    ],
    "Setor de temperados": [
        ("Tamblers", 540),
    ],
    "Setor de Industrializados": [
        ("Moedor", 540),
        ("Embutideira", 540),
    ],
    "Embalagem primária": [
        ("Empacotadora", 220),
        ("Dosadora", 220),
        ("Túnel Congelamento 3", 110),
    ],
    "Selagem": [
        ("Seladora", 220),
        ("Sala de etiquetas", 110),
        ("Depósito de embalagens primária", 110),
    ],
    "Expedição": [
        ("Depósito de embalagens secundárias", 110),
        ("Corredor central", 110),
        ("Câmara de congelados 1", 110),
        ("Câmara de congelados 2", 110),
        ("Câmara de resfriados", 110),
        ("Barreira sanitária", 220),
    ],
}

# Achatada em triplas (setor, local, lux_necessario), na ordem de
# exibição — usada pra gerar os campos do formulário (um índice
# global por ponto, já que "local" sozinho pode repetir entre
# setores) e pra percorrer a lista inteira sem se importar com o
# agrupamento.
PONTOS_COM_SETOR = [
    (setor, local, lux_necessario)
    for setor, pontos in PONTOS_POR_SETOR.items()
    for local, lux_necessario in pontos
]


def status_para_leitura(lux_obtido: float, lux_necessario: float) -> str:
    return "C" if lux_obtido >= lux_necessario else "NC"


class RegistroIluminacao(db.Model):
    """Um registro por ponto medido por checagem mensal — um checklist
    completo pode gerar até 21 linhas (uma por ponto), mas só os
    pontos com leitura preenchida naquele envio são salvos (igual ao
    PAC 08-G, diferente do PAC 08-E, que exige o checklist inteiro).

    Diferente de todos os outros tipos, este não tem campo de
    `responsavel` — não faz parte do modelo de dados pedido para este
    checklist."""

    __tablename__ = "registros_iluminacao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    setor = db.Column(db.String(80), nullable=False, index=True)
    local = db.Column(db.String(100), nullable=False)
    lux_necessario = db.Column(db.Integer, nullable=False)
    lux_obtido = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(2), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def conforme(self) -> bool:
        return self.status == "C"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data": self.data.strftime("%d/%m/%Y"),
            "data_iso": self.data.isoformat(),
            "setor": self.setor,
            "local": self.local,
            "ponto": f"{self.setor} — {self.local}",
            "lux_necessario": self.lux_necessario,
            "lux_obtido": self.lux_obtido,
            "status": self.status,
            "conforme": self.conforme,
        }

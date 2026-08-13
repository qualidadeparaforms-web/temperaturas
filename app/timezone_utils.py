"""Utilitário compartilhado por todos os tipos de registro.

O servidor (Render) roda com o relógio em UTC. Sem ajuste, `data` e
`horario` eram gravados com o horário "cru" do servidor — 3h
adiantados em relação a Brasília (ex.: 7h da manhã em Brasília virava
10h nos registros). O Brasil não usa mais horário de verão desde
2019, então um deslocamento fixo de -3h é seguro para "agora" (não
precisa de tabela de fuso horário/tzdata).
"""

from datetime import datetime, timedelta

FUSO_BRASILIA = timedelta(hours=-3)


def agora_brasilia() -> datetime:
    """Data e hora atuais no horário de Brasília, como datetime
    "naive" (sem tzinfo) — mesma convenção usada nas colunas
    Date/Time/DateTime do banco em todos os tipos de registro."""
    return datetime.utcnow() + FUSO_BRASILIA

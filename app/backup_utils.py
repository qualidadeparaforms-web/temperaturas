"""Utilitário compartilhado por todos os tipos de registro."""

import os
import threading


def agendar_backup_apos_registro() -> None:
    """Dispara um backup em segundo plano logo após salvar um registro,
    de qualquer tipo.

    Importante em hospedagens de plano gratuito (ex.: Render Free): o
    disco local é apagado toda vez que o serviço "dorme" por
    inatividade (~15 min sem acesso), não só em redeploys. Fazer o
    backup na hora, em vez de esperar um ciclo periódico, é o que
    garante que o registro sobreviva a esse "sono". Só roda quando
    BACKUP_S3_BUCKET está configurado — sem isso, um backup só local
    não sobrevive ao mesmo apagão.

    Chame esta função logo após o commit de qualquer tipo de registro
    (o backup é do banco inteiro, não só do tipo que acabou de salvar).
    """
    if not os.environ.get("BACKUP_S3_BUCKET"):
        return

    def _rodar():
        try:
            from backup import executar_backup

            executar_backup()
        except Exception as exc:  # nunca deve derrubar a resposta ao usuário
            print(f"Falha ao fazer backup após o registro: {exc}")

    threading.Thread(target=_rodar, daemon=True, name="backup-pos-registro").start()

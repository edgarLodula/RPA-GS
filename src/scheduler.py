import logging
import time

import schedule

from src.pipeline import executar_pipeline

logger = logging.getLogger("scheduler")


def main():
    # Roda uma vez ao iniciar (em try/except para não derrubar o scheduler
    # em caso de falha transiente na primeira execução, ex: API NASA indisponível)
    try:
        executar_pipeline()
    except Exception as e:
        logger.exception("Pipeline falhou na inicialização: %s — scheduler continua.", e)
    schedule.every(6).hours.do(executar_pipeline)
    logger.info("Agendador ativo: pipeline a cada 6 horas.")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
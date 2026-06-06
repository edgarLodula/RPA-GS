import logging
from datetime import date, timedelta

from src import collector, database, analizer, config
from src.monitor import medir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOGS_DIR / "robo.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("pipeline")


@medir
def executar_pipeline() -> dict:
    """Roda o fluxo completo: coleta -> armazena -> analisa -> APOD."""
    logger.info("=== INÍCIO DO PIPELINE ===")
    try:
        database.criar_tabela()
        dados = collector.coletar_asteroides(dias=1)
        registros = database.parse_feed(dados)
        database.inserir_asteroides(registros)
        relatorio = analizer.analisar_e_relatar()

        data_limite = (date.today() - timedelta(days=60)).isoformat()
        removidos = database.remover_antigos(data_limite)
        logger.info("%d registros antigos removidos (anteriores a %s).", removidos, data_limite)

        # Coleta e análise da APOD — falha aqui é warning, nunca erro do pipeline
        try:
            from src.vision import coletar_e_analisar
            coletar_e_analisar()
        except Exception as e:
            logger.warning("Módulo de visão não executado: %s", e)

        logger.info("=== PIPELINE CONCLUÍDO COM SUCESSO ===")
        return relatorio
    except Exception as erro:
        logger.exception("Pipeline interrompido por erro: %s", erro)
        raise


if __name__ == "__main__":
    executar_pipeline()

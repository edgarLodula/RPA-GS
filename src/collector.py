import logging
import json
import time
from datetime import date, timedelta

import requests

from src import config

logger = logging.getLogger(__name__)


def _salvar_bruto(dados):
    nome = f"neo_{date.today().isoformat()}.json"
    caminho = config.DATA_DIR / nome
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=2, ensure_ascii=False)


def coletar_asteroides(dias: int = 1, tentativas: int = 3) -> dict:
    fim = date.today()
    inicio = fim - timedelta(days=dias)
    params = {
        "start_date": inicio.isoformat(),
        "end_date": fim.isoformat(),
        "api_key": config.nasa_api,
    }
    for tentativa in range(1, tentativas + 1):
        try:
            logger.info("Tentativa %d", tentativa)
            resposta = requests.get(config.NASA_FEED_URL, params=params, timeout=20)
            resposta.raise_for_status()
            dados = resposta.json()
            _salvar_bruto(dados)
            logger.info("Coleta concluída!")
            return dados
        except requests.exceptions.RequestException as e:
            logger.warning("Falha na coleta: %s", e)
            if tentativa < tentativas:
                time.sleep(2 * tentativa)
    raise RuntimeError("Todas as tentativas de coleta falharam.")

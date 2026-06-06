import functools
import logging
import time

import psutil

from src.config import BASE_DIR

logger = logging.getLogger(__name__)


def medir(funcao):
    """Decorator que mede CPU, memória e tempo de uma função do pipeline."""
    @functools.wraps(funcao)
    def envelope(*args, **kwargs):
        processo = psutil.Process()
        inicio = time.time()
        cpu_antes = processo.cpu_percent()

        resultado = funcao(*args, **kwargs)

        duracao = time.time() - inicio
        memoria_mb = processo.memory_info().rss / (1024 * 1024)
        logger.info(
            "[MONITOR] %s | tempo=%.2fs | mem=%.1fMB | cpu=%.1f%%",
            funcao.__name__, duracao, memoria_mb, cpu_antes,
        )
        return resultado
    return envelope


def status_sistema() -> dict:
    """Snapshot dos recursos da máquina — usado pelo endpoint /saude."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memoria_percent": psutil.virtual_memory().percent,
        "disco_percent": psutil.disk_usage(str(BASE_DIR)).percent,
    }
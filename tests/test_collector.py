from unittest.mock import MagicMock, patch

import pytest
import requests as req

from src import config, collector


NASA_MOCK = {
    "near_earth_objects": {
        "2026-06-05": [{
            "id": "t-1", "name": "Mock Asteroid",
            "estimated_diameter": {"meters": {"estimated_diameter_min": 10, "estimated_diameter_max": 20}},
            "is_potentially_hazardous_asteroid": False,
            "close_approach_data": [{
                "close_approach_date": "2026-06-05",
                "relative_velocity": {"kilometers_per_hour": "50000"},
                "miss_distance": {"kilometers": "1000000"},
            }],
        }]
    }
}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redireciona config.DATA_DIR para tmp_path para não gerar arquivos reais."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return tmp_path


def _resposta_ok():
    """Helper: cria mock de resposta HTTP 200 com NASA_MOCK."""
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = NASA_MOCK
    return resp


def test_coleta_sucesso_salva_json(data_dir):
    """Coleta bem-sucedida deve retornar JSON e salvar arquivo neo_*.json."""
    with patch("src.collector.requests.get", return_value=_resposta_ok()):
        resultado = collector.coletar_asteroides(dias=1)

    assert resultado == NASA_MOCK
    json_files = list(data_dir.glob("neo_*.json"))
    assert len(json_files) == 1


def test_retry_em_falha_temporaria(data_dir):
    """Duas falhas seguidas de sucesso devem retornar o resultado sem lançar exceção."""
    side_effects = [
        req.exceptions.RequestException("timeout"),
        req.exceptions.RequestException("timeout"),
        _resposta_ok(),
    ]
    with patch("src.collector.requests.get", side_effect=side_effects), \
         patch("src.collector.time.sleep") as mock_sleep:
        resultado = collector.coletar_asteroides(dias=1, tentativas=3)

    assert resultado == NASA_MOCK
    # sleep chamado 2x: após tentativa 1 e após tentativa 2 (não após a última)
    assert mock_sleep.call_count == 2


def test_falha_em_todas_tentativas_levanta_runtime_error(data_dir):
    """Quando todas as tentativas falham, deve levantar RuntimeError."""
    with patch("src.collector.requests.get",
               side_effect=req.exceptions.RequestException("sem rede")), \
         patch("src.collector.time.sleep"):
        with pytest.raises(RuntimeError, match="Todas as tentativas"):
            collector.coletar_asteroides(dias=1, tentativas=3)

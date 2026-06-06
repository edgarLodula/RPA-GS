import openpyxl
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src import config, database

# TestClient criado uma vez por módulo; startup event (criar_tabela) é idempotente
client = TestClient(app)

ASTEROIDES_MOCK = [
    {
        "id": "t-1", "nome": "Mock-1", "data_aprox": "2026-06-01",
        "diametro_min_m": 100.0, "diametro_max_m": 200.0,
        "velocidade_kmh": 50_000.0, "distancia_km": 1_000_000.0,
        "perigoso": 0, "score_risco": 30.0, "anomaly_score": None,
    },
    {
        "id": "t-2", "nome": "Mock-2", "data_aprox": "2026-06-01",
        "diametro_min_m": 200.0, "diametro_max_m": 400.0,
        "velocidade_kmh": 80_000.0, "distancia_km": 500_000.0,
        "perigoso": 1, "score_risco": 60.0, "anomaly_score": -0.1,
    },
    {
        "id": "t-3", "nome": "Mock-3", "data_aprox": "2026-06-01",
        "diametro_min_m": 500.0, "diametro_max_m": 900.0,
        "velocidade_kmh": 100_000.0, "distancia_km": 300_000.0,
        "perigoso": 1, "score_risco": 90.0, "anomaly_score": -0.3,
    },
]


def test_saude_retorna_tres_metricas():
    """/saude deve responder 200 com cpu_percent, memoria_percent e disco_percent."""
    resp = client.get("/saude")
    assert resp.status_code == 200
    dados = resp.json()
    assert "cpu_percent" in dados
    assert "memoria_percent" in dados
    assert "disco_percent" in dados
    assert isinstance(dados["cpu_percent"], (int, float))


def test_asteroides_404_quando_vazio(monkeypatch):
    """/asteroides deve retornar 404 quando o banco não tem registros."""
    monkeypatch.setattr(database, "listar_asteroides", lambda: [])
    resp = client.get("/asteroides")
    assert resp.status_code == 404


def test_perigosos_filtra_por_score(monkeypatch):
    """/perigosos?score_minimo=50 deve retornar só asteroides com score >= 50."""
    monkeypatch.setattr(database, "listar_asteroides", lambda: ASTEROIDES_MOCK)
    resp = client.get("/perigosos?score_minimo=50")
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()]
    assert "t-2" in ids   # score 60 ≥ 50
    assert "t-3" in ids   # score 90 ≥ 50
    assert "t-1" not in ids  # score 30 < 50


def test_relatorio_xlsx_retorna_arquivo(tmp_path, monkeypatch):
    """/relatorio.xlsx deve retornar 200 e content-type XLSX quando arquivo existe."""
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
    xlsx = tmp_path / "relatorio_2026-06-05.xlsx"
    wb = openpyxl.Workbook()
    wb.save(xlsx)

    resp = client.get("/relatorio.xlsx")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")


def test_relatorio_xlsx_404_sem_arquivo(tmp_path, monkeypatch):
    """/relatorio.xlsx deve retornar 404 quando nenhum XLSX existe."""
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path)
    resp = client.get("/relatorio.xlsx")
    assert resp.status_code == 404

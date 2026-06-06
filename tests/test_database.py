import pytest

from src import config, database


# Registros reutilizados em múltiplos testes
MOCK_A = {
    "id": "t-1", "nome": "Mock 1", "data_aprox": "2026-06-01",
    "diametro_min_m": 100.0, "diametro_max_m": 200.0,
    "velocidade_kmh": 50_000.0, "distancia_km": 1_000_000.0,
    "perigoso": 0, "score_risco": None,
}
MOCK_B = {
    "id": "t-2", "nome": "Mock 2", "data_aprox": "2026-06-02",
    "diametro_min_m": 50.0, "diametro_max_m": 100.0,
    "velocidade_kmh": 40_000.0, "distancia_km": 500_000.0,  # menor distância
    "perigoso": 1, "score_risco": None,
}
MOCK_ANTIGO = {
    "id": "t-3", "nome": "Antigo", "data_aprox": "2025-01-01",
    "diametro_min_m": 10.0, "diametro_max_m": 20.0,
    "velocidade_kmh": 30_000.0, "distancia_km": 2_000_000.0,
    "perigoso": 0, "score_risco": None,
}


@pytest.fixture
def db_temp(tmp_path, monkeypatch):
    """Aponta config.DB_PATH para banco isolado por teste e inicializa a tabela."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    database.criar_tabela()


def test_criar_tabela_idempotente(db_temp):
    """Chamar criar_tabela() duas vezes não deve falhar nem criar colunas duplicadas."""
    database.criar_tabela()  # segunda chamada
    with database.conectar() as con:
        colunas = [r[1] for r in con.execute("PRAGMA table_info(asteroides)").fetchall()]
    assert "id" in colunas
    assert "score_risco" in colunas
    assert "anomaly_score" in colunas


def test_parse_feed_ignora_sem_close_approach():
    """Asteroide sem close_approach_data deve ser pulado silenciosamente."""
    feed = {
        "near_earth_objects": {
            "2026-06-01": [
                {   # sem close_approach_data — deve ser ignorado
                    "id": "bad-1", "name": "Sem dados",
                    "estimated_diameter": {"meters": {"estimated_diameter_min": 10, "estimated_diameter_max": 20}},
                    "is_potentially_hazardous_asteroid": False,
                    "close_approach_data": [],
                },
                {   # com dados válidos — deve ser incluído
                    "id": "ok-1", "name": "Com dados",
                    "estimated_diameter": {"meters": {"estimated_diameter_min": 50, "estimated_diameter_max": 100}},
                    "is_potentially_hazardous_asteroid": False,
                    "close_approach_data": [{
                        "close_approach_date": "2026-06-01",
                        "relative_velocity": {"kilometers_per_hour": "50000"},
                        "miss_distance": {"kilometers": "1000000"},
                    }],
                },
            ]
        }
    }
    registros = database.parse_feed(feed)
    assert len(registros) == 1
    assert registros[0]["id"] == "ok-1"


def test_insert_e_list_ordenado_por_distancia(db_temp):
    """Listar deve retornar registros ordenados por distancia_km crescente."""
    database.inserir_asteroides([MOCK_A, MOCK_B, MOCK_ANTIGO])
    resultado = database.listar_asteroides()
    assert len(resultado) == 3
    distancias = [r["distancia_km"] for r in resultado]
    assert distancias == sorted(distancias)
    assert resultado[0]["id"] == "t-2"  # 500_000 km


def test_upsert_atualiza_distancia_preserva_score(db_temp):
    """Segundo insert com mesmo id atualiza distancia_km mas preserva score_risco."""
    database.inserir_asteroides([MOCK_A])
    database.atualizar_score("t-1", 42.0)

    novo = {**MOCK_A, "distancia_km": 999_999.0, "data_aprox": "2026-12-31"}
    database.inserir_asteroides([novo])

    resultado = database.listar_asteroides()
    assert len(resultado) == 1
    r = resultado[0]
    assert r["distancia_km"] == pytest.approx(999_999.0)
    assert r["data_aprox"] == "2026-12-31"
    assert r["score_risco"] == pytest.approx(42.0)  # deve ter sido preservado


def test_remover_antigos_deleta_apenas_velhos(db_temp):
    """remover_antigos deve deletar apenas registros com data_aprox < data_limite."""
    database.inserir_asteroides([MOCK_A, MOCK_B, MOCK_ANTIGO])
    removidos = database.remover_antigos("2026-01-01")
    assert removidos == 1
    restantes = [r["id"] for r in database.listar_asteroides()]
    assert "t-3" not in restantes
    assert "t-1" in restantes
    assert "t-2" in restantes

import random

from src.analizer import calcular_score, detectar_anomalias, _detectar_anomalias_legado

ASTEROIDE_BASE = {
    "diametro_max_m": 500.0,
    "velocidade_kmh": 50_000.0,
    "distancia_km": 1_000_000.0,
    "perigoso": 0,
}


def test_score_entre_0_e_100():
    score = calcular_score(ASTEROIDE_BASE)
    assert 0 <= score <= 100


def test_perigoso_tem_score_maior():
    seguro = calcular_score({**ASTEROIDE_BASE, "perigoso": 0})
    perigoso = calcular_score({**ASTEROIDE_BASE, "perigoso": 1})
    assert perigoso > seguro


def test_anomalias_vazia_se_scores_iguais():
    asteroides = [
        {"score_risco": 50.0},
        {"score_risco": 50.0},
        {"score_risco": 50.0},
    ]
    assert detectar_anomalias(asteroides) == []


def test_anomalias_fallback_menos_de_10():
    """Com menos de 10 asteroides, usa o caminho legado e retorna lista."""
    asteroides = [
        {**ASTEROIDE_BASE, "score_risco": float(i * 10)}
        for i in range(9)
    ]
    resultado = detectar_anomalias(asteroides)
    assert isinstance(resultado, list)


def test_anomalias_isolation_forest_detecta_outliers():
    """IsolationForest identifica outliers óbvios numa amostra sintética."""
    rng = random.Random(42)

    # 20 asteroides "normais" com valores moderados
    normais = [
        {
            "diametro_max_m": 100.0 + rng.uniform(-10, 10),
            "velocidade_kmh": 50_000.0 + rng.uniform(-5_000, 5_000),
            "distancia_km": 3_000_000.0 + rng.uniform(-200_000, 200_000),
            "score_risco": 50.0 + rng.uniform(-5, 5),
        }
        for _ in range(20)
    ]

    # 2 outliers absurdamente extremos
    outliers = [
        {
            "diametro_max_m": 9_999.0,
            "velocidade_kmh": 999_999.0,
            "distancia_km": 10.0,
            "score_risco": 100.0,
        },
        {
            "diametro_max_m": 9_998.0,
            "velocidade_kmh": 998_000.0,
            "distancia_km": 15.0,
            "score_risco": 99.9,
        },
    ]

    todos = normais + outliers
    anomalias = detectar_anomalias(todos)

    assert len(anomalias) > 0, "Deve detectar ao menos uma anomalia"
    # Pelo menos um dos dois outliers explícitos deve estar nas anomalias
    ids_anomalos = {id(a) for a in anomalias}
    assert any(id(o) in ids_anomalos for o in outliers), (
        "Pelo menos um outlier extremo deve ser identificado"
    )

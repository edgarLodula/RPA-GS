import json
import logging
from datetime import date

from src import config, database

logger = logging.getLogger(__name__)


def calcular_score(ast: dict) -> float:
    fator_tamanho = min(ast["diametro_max_m"] / 1000, 1.0)
    fator_velocidade = min(ast["velocidade_kmh"] / 150_000, 1.0)  # ~máx real nos dados NASA
    fator_proximidade = 1 - min(ast["distancia_km"] / 7_500_000, 1.0)

    score = (
        fator_tamanho * 0.4
        + fator_velocidade * 0.2
        + fator_proximidade * 0.4
    ) * 100

    if ast["perigoso"]:
        score = min(score + 15, 100)
    return round(score, 2)


def _detectar_anomalias_legado(asteroides: list[dict]) -> list[dict]:
    """Detecção estatística simples (média + 1σ). Usada como fallback para < 10 amostras."""
    scores = [a["score_risco"] for a in asteroides if a["score_risco"] is not None]
    if not scores:
        return []
    media = sum(scores) / len(scores)
    desvio = (sum((s - media) ** 2 for s in scores) / len(scores)) ** 0.5
    limite = media + desvio
    return [a for a in asteroides if a["score_risco"] and a["score_risco"] > limite]


def detectar_anomalias(asteroides: list[dict]) -> list[dict]:
    """Detecção multidimensional com IsolationForest (scikit-learn).

    Features: diametro_max_m, velocidade_kmh, distancia_km, score_risco.
    Fallback para _detectar_anomalias_legado() quando há menos de 10 amostras,
    pois o IsolationForest não generaliza bem com poucos dados.
    Adiciona campo anomaly_score em cada asteroide processado
    (quanto menor o valor, mais anômalo o objeto).
    """
    if len(asteroides) < 10:
        return _detectar_anomalias_legado(asteroides)

    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        logger.warning("scikit-learn/numpy não instalado — usando detecção legado.")
        return _detectar_anomalias_legado(asteroides)

    FEATURES = ("diametro_max_m", "velocidade_kmh", "distancia_km", "score_risco")

    # Filtra apenas asteroides com todas as features disponíveis
    features: list[list[float]] = []
    indices_validos: list[int] = []
    for i, a in enumerate(asteroides):
        if all(a.get(f) is not None for f in FEATURES):
            features.append([float(a[f]) for f in FEATURES])
            indices_validos.append(i)

    if len(features) < 10:
        return _detectar_anomalias_legado(asteroides)

    X = np.array(features, dtype=float)
    # StandardScaler essencial: as ordens de grandeza das features são muito diferentes
    X_scaled = StandardScaler().fit_transform(X)

    modelo = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
    predicoes = modelo.fit_predict(X_scaled)
    scores_anomalia = modelo.decision_function(X_scaled)  # negativo = mais anômalo

    for pos, idx in enumerate(indices_validos):
        asteroides[idx]["anomaly_score"] = round(float(scores_anomalia[pos]), 4)

    return [asteroides[idx] for pos, idx in enumerate(indices_validos) if predicoes[pos] == -1]


def _gerar_xlsx(asteroides: list[dict], relatorio: dict) -> None:
    """Gera relatório XLSX multi-aba. Erros são logados como warning (pipeline não para)."""
    try:
        import pandas as pd
        from openpyxl.styles import Font

        caminho = config.REPORTS_DIR / f"relatorio_{date.today().isoformat()}.xlsx"

        COLUNAS_PTBR = {
            "id": "ID",
            "nome": "Nome",
            "data_aprox": "Data Aprox.",
            "diametro_min_m": "Diâmetro Mín. (m)",
            "diametro_max_m": "Diâmetro Máx. (m)",
            "velocidade_kmh": "Velocidade (km/h)",
            "distancia_km": "Distância (km)",
            "perigoso": "Perigoso",
            "score_risco": "Score de Risco",
            "anomaly_score": "Score de Anomalia",
        }

        df_todos = pd.DataFrame(asteroides).rename(columns=COLUNAS_PTBR)
        df_top5 = pd.DataFrame(relatorio.get("top_5_risco", [])).rename(columns=COLUNAS_PTBR)
        df_metricas = pd.DataFrame([
            {"Métrica": "Gerado em",                "Valor": relatorio.get("gerado_em", "")},
            {"Métrica": "Total de Asteroides",      "Valor": relatorio.get("total_asteroides", 0)},
            {"Métrica": "Potencialmente Perigosos", "Valor": relatorio.get("potencialmente_perigosos", 0)},
            {"Métrica": "Anomalias Detectadas",     "Valor": relatorio.get("anomalias_detectadas", 0)},
        ])

        with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
            for df, aba in [
                (df_todos,    "Asteroides"),
                (df_top5,     "Top 5 Risco"),
                (df_metricas, "Métricas"),
            ]:
                df.to_excel(writer, sheet_name=aba, index=False)
                ws = writer.sheets[aba]
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                ws.freeze_panes = "A2"

        logger.info("Relatório XLSX salvo em %s", caminho)
    except Exception as e:
        logger.warning("Falha ao gerar XLSX (pipeline continua): %s", e)


def analisar_e_relatar() -> dict:
    """Calcula scores, grava no banco e gera relatório consolidado (JSON + XLSX)."""
    asteroides = database.listar_asteroides()

    for ast in asteroides:
        score = calcular_score(ast)
        ast["score_risco"] = score
        database.atualizar_score(ast["id"], score)

    anomalias = detectar_anomalias(asteroides)

    relatorio = {
        "gerado_em": date.today().isoformat(),
        "total_asteroides": len(asteroides),
        "potencialmente_perigosos": sum(a["perigoso"] for a in asteroides),
        "anomalias_detectadas": len(anomalias),
        "anomalias": anomalias,
        "top_5_risco": sorted(
            asteroides, key=lambda a: a["score_risco"] or 0, reverse=True
        )[:5],
    }

    caminho = config.REPORTS_DIR / f"relatorio_{date.today().isoformat()}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    logger.info("Relatório consolidado salvo em %s", caminho)

    # Persiste anomaly_score no banco para cada asteroide que recebeu o campo
    for ast in asteroides:
        score_anomalia = ast.get("anomaly_score")
        if score_anomalia is not None:
            try:
                database.atualizar_anomaly_score(ast["id"], score_anomalia)
            except Exception as e:
                logger.warning("anomaly_score não persistido para %s: %s", ast["id"], e)

    _gerar_xlsx(asteroides, relatorio)
    return relatorio

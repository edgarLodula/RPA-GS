import logging
import sqlite3
from contextlib import contextmanager

from src import config

logger = logging.getLogger(__name__)


@contextmanager
def conectar():
    conexao = sqlite3.connect(config.DB_PATH)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    except sqlite3.Error as e:
        conexao.rollback()
        logger.error("Erro de banco: %s", e)
        raise
    finally:
        conexao.close()


def _migrar_anomaly_score() -> None:
    """Adiciona anomaly_score em bancos já existentes.

    SQLite não suporta ADD COLUMN IF NOT EXISTS, então trata a OperationalError
    que ocorre quando a coluna já existe — banco novo ou banco legado, sem crash.
    """
    try:
        with conectar() as con:
            con.execute("ALTER TABLE asteroides ADD COLUMN anomaly_score REAL")
        logger.info("Coluna 'anomaly_score' adicionada à tabela.")
    except sqlite3.OperationalError:
        pass  # Coluna já existe; nenhuma ação necessária


def criar_tabela():
    with conectar() as con:
        con.execute('''
        CREATE TABLE IF NOT EXISTS asteroides (
            id              TEXT PRIMARY KEY,
            nome            TEXT NOT NULL,
            data_aprox      TEXT,
            diametro_min_m  REAL,
            diametro_max_m  REAL,
            velocidade_kmh  REAL,
            distancia_km    REAL,
            perigoso        INTEGER,
            score_risco     REAL,
            anomaly_score   REAL
        )
        ''')
    _migrar_anomaly_score()
    logger.info("Tabela 'asteroides' pronta.")


def parse_feed(dados: dict) -> list[dict]:
    registros = []
    pulados = 0
    for lista_do_dia in dados.get("near_earth_objects", {}).values():
        for ast in lista_do_dia:
            if not ast.get("close_approach_data"):
                pulados += 1
                continue
            diam = ast["estimated_diameter"]["meters"]
            aprox = ast["close_approach_data"][0]
            registros.append({
                "id": ast["id"],
                "nome": ast["name"],
                "data_aprox": aprox["close_approach_date"],
                "diametro_min_m": diam["estimated_diameter_min"],
                "diametro_max_m": diam["estimated_diameter_max"],
                "velocidade_kmh": float(aprox["relative_velocity"]["kilometers_per_hour"]),
                "distancia_km": float(aprox["miss_distance"]["kilometers"]),
                "perigoso": int(ast["is_potentially_hazardous_asteroid"]),
                "score_risco": None,
            })
    if pulados:
        logger.warning("%d asteroides pulados por falta de close_approach_data.", pulados)
    return registros


def inserir_asteroides(registros: list[dict]) -> int:
    with conectar() as con:
        con.executemany('''
        INSERT INTO asteroides
            (id, nome, data_aprox, diametro_min_m, diametro_max_m,
             velocidade_kmh, distancia_km, perigoso, score_risco)
        VALUES
            (:id, :nome, :data_aprox, :diametro_min_m, :diametro_max_m,
             :velocidade_kmh, :distancia_km, :perigoso, :score_risco)
        ON CONFLICT(id) DO UPDATE SET
            data_aprox   = excluded.data_aprox,
            distancia_km = excluded.distancia_km
        ''', registros)
    logger.info("%d asteroides registrados", len(registros))
    return len(registros)


def listar_asteroides() -> list[dict]:
    with conectar() as con:
        linhas = con.execute("SELECT * FROM asteroides ORDER BY distancia_km").fetchall()
    return [dict(l) for l in linhas]


def atualizar_score(asteroide_id: str, score: float):
    with conectar() as con:
        con.execute(
            "UPDATE asteroides SET score_risco = ? WHERE id = ?",
            (score, asteroide_id)
        )


def atualizar_anomaly_score(asteroide_id: str, score: float):
    with conectar() as con:
        con.execute(
            "UPDATE asteroides SET anomaly_score = ? WHERE id = ?",
            (score, asteroide_id)
        )


def remover_antigos(data_limite: str) -> int:
    with conectar() as con:
        cursor = con.execute(
            "DELETE FROM asteroides WHERE data_aprox < ?", (data_limite,)
        )
    return cursor.rowcount

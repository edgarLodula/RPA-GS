from pydantic import BaseModel


class Asteroide(BaseModel):
    id: str
    nome: str
    data_aprox: str | None
    diametro_min_m: float
    diametro_max_m: float
    velocidade_kmh: float
    distancia_km: float
    perigoso: int
    score_risco: float | None
    anomaly_score: float | None = None


class StatusSaude(BaseModel):
    cpu_percent: float
    memoria_percent: float
    disco_percent: float


class APODAnalise(BaseModel):
    data: str
    titulo: str
    media_type: str
    largura: int | None = None
    altura: int | None = None
    brilho_medio: float | None = None
    cor_dominante_hex: str | None = None
    tamanho_kb: float | None = None
    caminho_imagem: str | None = None

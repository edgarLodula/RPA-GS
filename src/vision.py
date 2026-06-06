"""
Módulo de visão computacional: coleta e analisa a Astronomy Picture of the Day (APOD) da NASA.

Integrado ao pipeline como etapa opcional — falhas geram warning e não interrompem
o fluxo principal de asteroides.
"""
import csv
import json
import logging
import time
from collections import Counter
from datetime import date
from pathlib import Path

import requests

from src import config

logger = logging.getLogger(__name__)

APOD_URL = "https://api.nasa.gov/planetary/apod"
IMAGES_DIR = config.BASE_DIR / "data" / "images"
APOD_CSV = config.REPORTS_DIR / "apod_analytics.csv"

_CSV_COLUNAS = [
    "data", "titulo", "media_type",
    "largura", "altura", "brilho_medio",
    "cor_dominante_hex", "tamanho_kb", "caminho_imagem",
]


def _garantir_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def coletar_apod(tentativas: int = 3) -> dict:
    """Busca metadados e imagem da APOD. Retry + backoff exponencial (igual ao collector.py)."""
    _garantir_dirs()
    params = {"api_key": config.nasa_api, "date": date.today().isoformat()}

    ultimo_erro: Exception | None = None
    dados: dict = {}
    for t in range(1, tentativas + 1):
        try:
            resp = requests.get(APOD_URL, params=params, timeout=20)
            resp.raise_for_status()
            dados = resp.json()
            break
        except requests.RequestException as e:
            ultimo_erro = e
            if t < tentativas:
                logger.warning("APOD: tentativa %d falhou (%s), aguardando...", t, e)
                time.sleep(2 * t)
    else:
        raise RuntimeError(f"APOD: todas as tentativas falharam. Último: {ultimo_erro}")

    # Persiste os metadados JSON localmente
    meta_path = IMAGES_DIR / f"apod_{date.today().isoformat()}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    # Baixa a imagem quando media_type == "image"
    caminho_img: Path | None = None
    if dados.get("media_type") == "image":
        url_img = dados.get("hdurl") or dados.get("url", "")
        ext = url_img.rsplit(".", 1)[-1].split("?")[0] if "." in url_img else "jpg"
        caminho_img = IMAGES_DIR / f"apod_{date.today().isoformat()}.{ext}"
        try:
            r = requests.get(url_img, timeout=30)
            r.raise_for_status()
            with open(caminho_img, "wb") as f:
                f.write(r.content)
            logger.info("APOD imagem salva: %s", caminho_img.name)
        except requests.RequestException as e:
            logger.warning("APOD: falha ao baixar imagem (%s)", e)
            caminho_img = None
    else:
        logger.info("APOD: media_type=%s — download ignorado.", dados.get("media_type"))

    dados["_caminho_imagem"] = str(caminho_img) if caminho_img else None
    return dados


def analisar_imagem(caminho: str | Path) -> dict:
    """Analisa imagem com Pillow: dimensões, brilho médio e cor dominante."""
    from PIL import Image

    img_path = Path(caminho)
    if not img_path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

    with Image.open(img_path) as img:
        largura, altura = img.size

        # Brilho médio: escala de cinza → média dos pixels (0–255)
        pixels = list(img.convert("L").getdata())
        brilho = sum(pixels) / len(pixels) if pixels else 0.0

        # Cor dominante: reduz a paleta de 8 cores e pega a mais frequente
        quantizada = img.convert("RGB").quantize(colors=8)
        paleta = quantizada.getpalette()  # lista plana [R,G,B, R,G,B, ...]
        idx_dom = Counter(quantizada.getdata()).most_common(1)[0][0]
        r, g, b = paleta[idx_dom * 3: idx_dom * 3 + 3]
        cor_hex = f"#{r:02X}{g:02X}{b:02X}"

        tamanho_kb = round(img_path.stat().st_size / 1024, 2)

    return {
        "largura": largura,
        "altura": altura,
        "brilho_medio": round(brilho, 2),
        "cor_dominante_hex": cor_hex,
        "tamanho_kb": tamanho_kb,
    }


def coletar_e_analisar() -> dict:
    """Orquestra coleta + análise da APOD e faz append no CSV diário.

    Não lança exceções — falhas retornam dict vazio e são logadas como warning.
    """
    _garantir_dirs()
    try:
        dados_apod = coletar_apod()

        # Caminho absoluto usado internamente para leitura de arquivo;
        # o CSV armazena o path relativo à raiz do projeto para portabilidade
        # (evita paths Docker /app/... que são inválidos fora do container).
        caminho_abs: str | None = dados_apod.get("_caminho_imagem")
        caminho_relativo: str | None = None
        if caminho_abs:
            try:
                caminho_relativo = str(Path(caminho_abs).relative_to(config.BASE_DIR))
            except ValueError:
                caminho_relativo = caminho_abs  # fallback se já for relativo

        analise: dict = {
            "data": date.today().isoformat(),
            "titulo": dados_apod.get("title", ""),
            "media_type": dados_apod.get("media_type", ""),
            "largura": None,
            "altura": None,
            "brilho_medio": None,
            "cor_dominante_hex": None,
            "tamanho_kb": None,
            "caminho_imagem": caminho_relativo,
        }

        if caminho_abs:
            analise.update(analisar_imagem(caminho_abs))

        ja_existe = APOD_CSV.exists()
        with open(APOD_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_COLUNAS)
            if not ja_existe:
                writer.writeheader()
            writer.writerow(analise)

        logger.info("APOD análise concluída: %s", analise.get("titulo", ""))
        return analise
    except Exception as e:
        logger.warning("APOD: falha na coleta/análise (%s) — pipeline continua.", e)
        return {}

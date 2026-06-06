import csv
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.models import APODAnalise, Asteroide, StatusSaude
from src import config, database, monitor
from src.config import BASE_DIR

app = FastAPI(
    title="GS 2026 — Monitoramento de Missões Espaciais",
    description="API que serve dados de asteroides processados pelo robô RPA.",
    version="1.0.0",
)

# Permite requisições cross-origin (necessário durante desenvolvimento).
# Em produção, substituir ["*"] pelo domínio real do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Garante que a tabela existe antes da primeira requisição."""
    database.criar_tabela()


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse(url="/ui/")


@app.get("/asteroides", response_model=list[Asteroide])
def get_asteroides():
    """READ — todos os asteroides do banco, ordenados por distância."""
    dados = database.listar_asteroides()
    if not dados:
        raise HTTPException(404, "Nenhum dado. Rode o pipeline primeiro.")
    return dados


@app.get("/perigosos", response_model=list[Asteroide])
def get_perigosos(score_minimo: float = 50.0):
    """Filtra só os asteroides acima de um score mínimo de risco."""
    return [a for a in database.listar_asteroides()
            if (a["score_risco"] or 0) >= score_minimo]


@app.get("/relatorio")
def get_relatorio():
    """Devolve o relatório consolidado mais recente gerado pelo pipeline."""
    arquivos = sorted(config.REPORTS_DIR.glob("relatorio_*.json"), reverse=True)
    if not arquivos:
        raise HTTPException(404, "Nenhum relatório encontrado. Rode o pipeline primeiro.")
    with open(arquivos[0], encoding="utf-8") as f:
        return json.load(f)


@app.get("/relatorio.xlsx")
def get_relatorio_xlsx():
    """Baixa o relatório XLSX mais recente gerado pelo pipeline."""
    arquivos = sorted(config.REPORTS_DIR.glob("relatorio_*.xlsx"), reverse=True)
    if not arquivos:
        raise HTTPException(404, "Nenhum XLSX encontrado. Rode o pipeline primeiro.")
    return FileResponse(
        path=str(arquivos[0]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=arquivos[0].name,
    )


@app.get("/saude", response_model=StatusSaude)
def get_saude():
    """Métricas de observabilidade da máquina do robô."""
    return monitor.status_sistema()


@app.get("/apod", response_model=APODAnalise)
def get_apod():
    """Retorna a análise da APOD (Astronomy Picture of the Day) mais recente."""
    images_dir = BASE_DIR / "data" / "images"
    arquivos = sorted(images_dir.glob("apod_*.json"), reverse=True)
    if not arquivos:
        raise HTTPException(404, "Nenhuma análise APOD encontrada. Rode o pipeline primeiro.")
    with open(arquivos[0], encoding="utf-8") as f:
        dados = json.load(f)

    # Extrai campos da análise persistida no CSV, se disponível
    analise: dict = {
        "data": dados.get("date", ""),
        "titulo": dados.get("title", ""),
        "media_type": dados.get("media_type", ""),
    }

    apod_csv = config.REPORTS_DIR / "apod_analytics.csv"
    if apod_csv.exists():
        with open(apod_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            ultima = rows[-1]
            for campo in ("largura", "altura", "brilho_medio", "tamanho_kb"):
                v = ultima.get(campo)
                analise[campo] = float(v) if v else None
            for campo in ("cor_dominante_hex", "caminho_imagem"):
                analise[campo] = ultima.get(campo) or None

    return analise


@app.get("/apod/imagem")
def get_apod_imagem():
    """Serve a imagem APOD mais recente baixada."""
    images_dir = BASE_DIR / "data" / "images"
    extensoes = ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp")
    candidatos = []
    for ext in extensoes:
        candidatos.extend(images_dir.glob(f"apod_{ext}"))
    if not candidatos:
        raise HTTPException(404, "Nenhuma imagem APOD encontrada.")
    imagem = sorted(candidatos, reverse=True)[0]
    return FileResponse(path=str(imagem))


# Serve o frontend estático em /ui/.
# html=True faz /ui/ retornar index.html automaticamente.
# Montado por último para não interceptar as rotas da API acima.
app.mount("/ui", StaticFiles(directory=str(BASE_DIR / "frontend"), html=True), name="frontend")

"""
Gera o ZIP limpo de entrega do GS 2026.

Lê os padrões do .gitignore e aplica exclusões adicionais de artefatos
gerados em runtime. Saída: gs_entrega_AAAA-MM-DD.zip na raiz do projeto.

Uso:
    python scripts/build_entrega.py
"""
import fnmatch
import zipfile
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Artefatos de runtime que nunca devem constar no ZIP de entrega
EXCLUIR_EXTRA = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".venv",
    ".git",
    "*.db",
    "*.log",
    "data/neo_*.json",
    "data/reports/*.json",
    "data/images",
    "data/arquivo_bruto",
    "*.egg-info",
    "dist",
    "build",
]


def _ler_gitignore(base: Path) -> list[str]:
    gi = base / ".gitignore"
    if not gi.exists():
        return []
    padroes = []
    for linha in gi.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            padroes.append(linha.rstrip("/"))
    return padroes


def _deve_ignorar(relativo: str, padroes: list[str]) -> bool:
    """Retorna True se *relativo* bate em qualquer padrão de exclusão."""
    rel_posix = relativo.replace("\\", "/")
    partes = rel_posix.split("/")
    for padrao in padroes:
        # Corresponde ao caminho completo
        if fnmatch.fnmatch(rel_posix, padrao):
            return True
        # Corresponde a qualquer segmento do caminho (ex: __pycache__)
        if fnmatch.fnmatch(partes[0], padrao):
            return True
        for parte in partes:
            if fnmatch.fnmatch(parte, padrao):
                return True
        # Padrão com barra corresponde ao prefixo do caminho (ex: data/neo_*.json)
        if "/" in padrao and fnmatch.fnmatch(rel_posix, padrao):
            return True
    return False


def main() -> None:
    padroes = _ler_gitignore(BASE_DIR) + EXCLUIR_EXTRA
    saida = BASE_DIR / f"gs_entrega_{date.today().isoformat()}.zip"

    incluidos: list[str] = []
    pulados: list[str] = []

    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in sorted(BASE_DIR.rglob("*")):
            if not arquivo.is_file():
                continue
            relativo = str(arquivo.relative_to(BASE_DIR))
            # Nunca incluir o próprio ZIP ou outros ZIPs na raiz
            if arquivo.suffix == ".zip":
                pulados.append(relativo)
                continue
            if _deve_ignorar(relativo, padroes):
                pulados.append(relativo)
                print(f"  PULADO : {relativo}")
            else:
                zf.write(arquivo, relativo)
                incluidos.append(relativo)
                print(f"  OK     : {relativo}")

    print()
    print(f"ZIP gerado : {saida.name}")
    print(f"Incluídos  : {len(incluidos)} arquivos")
    print(f"Pulados    : {len(pulados)} arquivos")


if __name__ == "__main__":
    main()

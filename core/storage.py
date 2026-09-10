"""Leitura e escrita do historico em `hist/*.txt`."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from core import paths
from core.models import TestResult

# Aceita apenas nomes no padrao AAAA-MM-DD HH-MM-SS.txt para evitar path traversal.
_NOME_VALIDO = re.compile(r"^[\w\-. ()]+\.txt$", re.UNICODE)


def save(resultado: TestResult) -> Path:
    """Grava um teste em um arquivo proprio. A pasta hist/ nasce aqui."""
    destino = paths.ensure_hist_dir()
    caminho = destino / resultado.build_filename()

    # Colisao de segundo (dois testes no mesmo segundo): sufixo incremental.
    contador = 2
    while caminho.exists():
        base = resultado.build_filename()[:-4]
        caminho = destino / f"{base} ({contador}).txt"
        contador += 1

    caminho.write_text(resultado.to_txt(), encoding="utf-8")
    resultado.filename = caminho.name
    return caminho


def load_history() -> list[TestResult]:
    """Le todos os .txt da pasta, do mais recente para o mais antigo (RF-11)."""
    pasta = paths.hist_dir()
    if not pasta.is_dir():
        return []

    resultados: list[TestResult] = []
    for arquivo in pasta.glob("*.txt"):
        try:
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # arquivo travado por outro processo nao derruba a tela

        registro = TestResult.from_txt(texto, arquivo.name)
        if registro.download <= 0 and registro.upload <= 0 and registro.ping is None:
            continue  # arquivo sem nenhum dado aproveitavel (RF-18)
        resultados.append(registro)

    resultados.sort(key=lambda r: r.timestamp, reverse=True)
    return resultados


def delete(filename: str) -> bool:
    """Remove um registro do historico (RF-15)."""
    if not filename or not _NOME_VALIDO.match(filename):
        return False
    alvo = paths.hist_dir() / filename
    try:
        if alvo.parent != paths.hist_dir() or not alvo.is_file():
            return False
        alvo.unlink()
        return True
    except OSError:
        return False


def summary(resultados: list[TestResult]) -> dict:
    """Medias exibidas no topo da tela de historico (RF-13)."""
    validos = [r for r in resultados if r.download > 0 or r.upload > 0]
    if not validos:
        return {"count": 0, "avg_download": 0.0, "avg_upload": 0.0, "best_download": 0.0}
    return {
        "count": len(validos),
        "avg_download": round(sum(r.download for r in validos) / len(validos), 2),
        "avg_upload": round(sum(r.upload for r in validos) / len(validos), 2),
        "best_download": round(max(r.download for r in validos), 2),
    }


def open_folder() -> bool:
    """Abre a pasta hist/ no Explorer (RF-14)."""
    pasta = paths.ensure_hist_dir()
    try:
        if sys.platform == "win32":
            os.startfile(str(pasta))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pasta)])
        else:
            subprocess.Popen(["xdg-open", str(pasta)])
        return True
    except OSError:
        return False

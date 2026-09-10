"""Resolucao de diretorios.

Regra do PRD (secao 5.1): a pasta `hist/` fica ao lado do executavel. Se esse
diretorio nao aceitar escrita (ex.: instalado em Program Files), cai para
%APPDATA%\\mowanettest\\hist.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

APP_NAME = "mowanettest"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Diretorio do executavel (ou raiz do projeto, em desenvolvimento)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Diretorio dos arquivos empacotados (ui/, assets/)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent.parent


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def _is_writable(diretorio: Path) -> bool:
    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        sonda = diretorio / f".w{uuid.uuid4().hex[:8]}"
        sonda.write_text("", encoding="utf-8")
        sonda.unlink()
        return True
    except OSError:
        return False


def hist_dir() -> Path:
    """Caminho da pasta de historico. NAO cria a pasta."""
    ao_lado = app_dir() / "hist"
    if ao_lado.exists():
        return ao_lado

    alternativo = appdata_dir() / "hist"
    if alternativo.exists():
        return alternativo

    return ao_lado if _is_writable(app_dir()) else alternativo


def ensure_hist_dir() -> Path:
    """Cria a pasta de historico. Chamado apenas ao concluir um teste (RF-08)."""
    destino = hist_dir()
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError:
        destino = appdata_dir() / "hist"
        destino.mkdir(parents=True, exist_ok=True)
    return destino

"""Modelo de dados de um teste de velocidade.

O formato de arquivo definido no PRD e' `chave: valor`, uma por linha,
UTF-8, legivel por humanos e trivial de parsear.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

APP_VERSION = "1.0.0"

# Ordem em que as chaves sao escritas no arquivo.
_FIELD_ORDER = (
    "data",
    "hora",
    "download",
    "upload",
    "ping",
    "jitter",
    "ip",
    "provedor",
    "servidor",
    "duracao",
    "versao",
)

_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


def _to_float(raw: Optional[str]) -> Optional[float]:
    """Extrai o primeiro numero de um valor como '248.73 Mbps'."""
    if raw is None:
        return None
    match = _NUMBER.search(raw)
    if not match:
        return None
    try:
        return float(match.group().replace(",", "."))
    except ValueError:
        return None


@dataclass
class TestResult:
    """Resultado de um teste concluido."""

    timestamp: datetime
    download: float = 0.0        # Mbps
    upload: float = 0.0          # Mbps
    ping: Optional[float] = None       # ms
    jitter: Optional[float] = None     # ms
    ip: Optional[str] = None
    provider: Optional[str] = None
    server: Optional[str] = None
    duration: Optional[float] = None   # segundos
    version: str = APP_VERSION
    filename: str = field(default="", compare=False)

    # ------------------------------------------------------------------ escrita

    def build_filename(self) -> str:
        """`AAAA-MM-DD HH-MM-SS.txt` — hifens porque ':' e' invalido no Windows."""
        return self.timestamp.strftime("%Y-%m-%d %H-%M-%S") + ".txt"

    def to_txt(self) -> str:
        values = {
            "data": self.timestamp.strftime("%Y-%m-%d"),
            "hora": self.timestamp.strftime("%H:%M:%S"),
            "download": f"{self.download:.2f} Mbps",
            "upload": f"{self.upload:.2f} Mbps",
            "ping": f"{self.ping:.1f} ms" if self.ping is not None else None,
            "jitter": f"{self.jitter:.1f} ms" if self.jitter is not None else None,
            "ip": self.ip,
            "provedor": self.provider,
            "servidor": self.server,
            "duracao": f"{self.duration:.1f} s" if self.duration is not None else None,
            "versao": self.version,
        }
        linhas = [f"{k}: {values[k]}" for k in _FIELD_ORDER if values.get(k)]
        return "\n".join(linhas) + "\n"

    # ------------------------------------------------------------------ leitura

    @classmethod
    def from_txt(cls, texto: str, filename: str = "") -> "TestResult":
        """Le um arquivo de historico.

        Tolerante: chaves ausentes viram None e linhas desconhecidas sao
        ignoradas (RF-18). Se o conteudo nao tiver data/hora valida, o nome do
        arquivo e' usado como fonte.
        """
        dados: dict[str, str] = {}
        for linha in texto.splitlines():
            if ":" not in linha:
                continue
            chave, _, valor = linha.partition(":")
            chave = chave.strip().lower()
            valor = valor.strip()
            if chave and valor:
                dados.setdefault(chave, valor)

        timestamp = cls._parse_timestamp(dados, filename)

        return cls(
            timestamp=timestamp,
            download=_to_float(dados.get("download")) or 0.0,
            upload=_to_float(dados.get("upload")) or 0.0,
            ping=_to_float(dados.get("ping")),
            jitter=_to_float(dados.get("jitter")),
            ip=dados.get("ip"),
            provider=dados.get("provedor"),
            server=dados.get("servidor"),
            duration=_to_float(dados.get("duracao")),
            version=dados.get("versao", ""),
            filename=filename,
        )

    @staticmethod
    def _parse_timestamp(dados: dict[str, str], filename: str) -> datetime:
        """O conteudo prevalece sobre o nome do arquivo (secao 5.3 do PRD)."""
        data, hora = dados.get("data"), dados.get("hora")
        if data:
            for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(f"{data} {hora}".strip(), formato)
                except ValueError:
                    continue
        base = filename[:-4] if filename.lower().endswith(".txt") else filename
        try:
            return datetime.strptime(base.strip(), "%Y-%m-%d %H-%M-%S")
        except ValueError:
            return datetime.fromtimestamp(0)

    # ------------------------------------------------------------------- ponte JS

    def to_dict(self) -> dict:
        return {
            "filename": self.filename or self.build_filename(),
            "iso": self.timestamp.isoformat(),
            "date": self.timestamp.strftime("%d/%m/%Y"),
            "time": self.timestamp.strftime("%H:%M"),
            "download": round(self.download, 2),
            "upload": round(self.upload, 2),
            "ping": round(self.ping, 1) if self.ping is not None else None,
            "jitter": round(self.jitter, 1) if self.jitter is not None else None,
            "ip": self.ip,
            "provider": self.provider,
            "server": self.server,
            "duration": round(self.duration, 1) if self.duration is not None else None,
        }

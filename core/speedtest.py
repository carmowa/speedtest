"""Motor de medicao de velocidade.

Implementacao propria sobre os endpoints publicos da Cloudflare, conforme a
secao 3.2 do PRD: sem dependencia de bibliotecas sem manutencao e sem binario
de terceiros com EULA.

  GET  https://speed.cloudflare.com/__down?bytes=N   -> download
  POST https://speed.cloudflare.com/__up             -> upload
  GET  https://speed.cloudflare.com/meta             -> IP, provedor e datacenter

A medicao descarta a janela inicial (slow start do TCP) e calcula a taxa em
regime estavel, com varias conexoes em paralelo para saturar o link.
"""

from __future__ import annotations

import os
import socket
import ssl
import threading
import time
from datetime import datetime
from typing import Callable, Optional

import requests

from core.models import APP_VERSION, TestResult

HOST = "speed.cloudflare.com"
URL_DOWN = f"https://{HOST}/__down"
URL_UP = f"https://{HOST}/__up"
URL_META = f"https://{HOST}/meta"

URL_TRACE = f"https://{HOST}/cdn-cgi/trace"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

# Parametros de medicao (secao 6, RNF-10: teste entre 20 e 40 s)
PING_SAMPLES = 10
DOWNLOAD_SECONDS = 10.0
UPLOAD_SECONDS = 10.0
WARMUP_SECONDS = 2.0
DOWNLOAD_THREADS = 6
UPLOAD_THREADS = 4
DOWNLOAD_CHUNK_BYTES = 25_000_000
UPLOAD_CHUNK_BYTES = 10_000_000
BLOCK = 65_536
SAMPLE_INTERVAL = 0.2

_DATACENTERS = {
    "GRU": "Sao Paulo", "GIG": "Rio de Janeiro", "CWB": "Curitiba",
    "POA": "Porto Alegre", "BSB": "Brasilia", "FOR": "Fortaleza",
    "REC": "Recife", "SSA": "Salvador", "CNF": "Belo Horizonte",
    "MIA": "Miami", "IAD": "Washington", "LAX": "Los Angeles",
    "EZE": "Buenos Aires", "SCL": "Santiago", "BOG": "Bogota",
}


class TestCancelled(Exception):
    """O usuario interrompeu o teste (RF-07)."""


class NetworkError(Exception):
    """Falha de conexao com mensagem pronta para a interface (RF-09)."""


class SpeedTest:
    """Executa um teste completo: ping -> download -> upload."""

    def __init__(
        self,
        on_progress: Optional[Callable[[dict], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        self._on_progress = on_progress or (lambda _: None)
        self._cancel = cancel_event or threading.Event()
        self._bytes = 0
        self._lock = threading.Lock()
        self._http_status: Optional[int] = None

    # ------------------------------------------------------------------ publico

    def run(self) -> TestResult:
        inicio = time.monotonic()

        meta = self._fetch_meta()
        ping, jitter = self._measure_latency()
        self._emit("latency", 1.0, ping=ping, jitter=jitter)

        download = self._transfer("download", DOWNLOAD_SECONDS, DOWNLOAD_THREADS)
        upload = self._transfer("upload", UPLOAD_SECONDS, UPLOAD_THREADS)

        resultado = TestResult(
            timestamp=datetime.now(),
            download=download,
            upload=upload,
            ping=ping,
            jitter=jitter,
            ip=meta.get("ip"),
            provider=meta.get("provider"),
            server=meta.get("server"),
            duration=time.monotonic() - inicio,
            version=APP_VERSION,
        )
        self._emit("done", 1.0)
        return resultado

    def cancel(self) -> None:
        self._cancel.set()

    # ------------------------------------------------------------------- etapas

    def _fetch_meta(self) -> dict:
        """IP, provedor e datacenter. Informativo: nunca aborta o teste."""
        self._emit("meta", 0.0)
        info = self._meta_json() or self._meta_trace() or {}
        self._emit("meta", 1.0, **info)
        return info

    def _meta_json(self) -> Optional[dict]:
        try:
            resposta = requests.get(URL_META, headers=HEADERS, timeout=8)
            resposta.raise_for_status()
            dados = resposta.json()
        except (requests.RequestException, ValueError):
            return None
        return {
            "ip": dados.get("clientIp") or dados.get("ip"),
            "provider": dados.get("asOrganization"),
            "server": self._nome_servidor(dados.get("colo"), dados.get("city")),
        }

    def _meta_trace(self) -> Optional[dict]:
        """Alternativa quando o /meta esta bloqueado: cdn-cgi/trace."""
        try:
            resposta = requests.get(URL_TRACE, headers=HEADERS, timeout=8)
            resposta.raise_for_status()
        except requests.RequestException:
            return None
        campos = dict(
            linha.split("=", 1)
            for linha in resposta.text.splitlines()
            if "=" in linha
        )
        return {
            "ip": campos.get("ip"),
            "server": self._nome_servidor(campos.get("colo"), None),
        }

    @staticmethod
    def _nome_servidor(colo: Optional[str], city: Optional[str]) -> str:
        colo = (colo or "").upper()
        if not colo:
            return "Cloudflare"
        cidade = _DATACENTERS.get(colo, city or "")
        return f"Cloudflare - {colo}" + (f" ({cidade})" if cidade else "")

    def _measure_latency(self) -> tuple[Optional[float], Optional[float]]:
        """Handshake TCP cronometrado — nao exige privilegio de administrador."""
        amostras: list[float] = []
        contexto = ssl.create_default_context()

        for indice in range(PING_SAMPLES):
            self._check_cancel()
            comeco = time.perf_counter()
            try:
                with socket.create_connection((HOST, 443), timeout=5) as bruto:
                    with contexto.wrap_socket(bruto, server_hostname=HOST):
                        amostras.append((time.perf_counter() - comeco) * 1000)
            except OSError:
                continue
            self._emit("latency", (indice + 1) / PING_SAMPLES,
                       ping=round(min(amostras), 1) if amostras else None)
            time.sleep(0.05)

        if not amostras:
            raise NetworkError(
                "Sem resposta do servidor de medicao. Verifique sua conexao "
                "ou se um firewall esta bloqueando o aplicativo."
            )

        # O handshake TLS custa mais de um RTT; a menor amostra e' a mais limpa.
        ping = min(amostras)
        jitter = (
            sum(abs(b - a) for a, b in zip(amostras, amostras[1:])) / (len(amostras) - 1)
            if len(amostras) > 1 else 0.0
        )
        return round(ping, 1), round(jitter, 1)

    def _transfer(self, direcao: str, duracao: float, workers: int) -> float:
        """Satura o link por `duracao` segundos e devolve a taxa em Mbps."""
        with self._lock:
            self._bytes = 0
        self._http_status = None

        inicio = time.monotonic()
        fim = inicio + duracao + WARMUP_SECONDS
        alvo = self._download_worker if direcao == "download" else self._upload_worker

        threads = [
            threading.Thread(target=alvo, args=(fim,), daemon=True, name=f"{direcao}-{i}")
            for i in range(workers)
        ]
        for thread in threads:
            thread.start()

        base_bytes = 0
        base_tempo = inicio
        aquecendo = True
        anterior_bytes, anterior_tempo = 0, inicio
        erro_fatal: Optional[BaseException] = None

        while time.monotonic() < fim:
            time.sleep(SAMPLE_INTERVAL)
            agora = time.monotonic()
            with self._lock:
                atual = self._bytes

            if aquecendo and agora - inicio >= WARMUP_SECONDS:
                base_bytes, base_tempo, aquecendo = atual, agora, False

            intervalo = max(agora - anterior_tempo, 1e-6)
            instantaneo = (atual - anterior_bytes) * 8 / intervalo / 1_000_000
            anterior_bytes, anterior_tempo = atual, agora

            self._emit(
                direcao,
                min((agora - inicio) / (duracao + WARMUP_SECONDS), 1.0),
                speed=round(instantaneo, 2),
                warmup=aquecendo,
            )

            if self._cancel.is_set():
                erro_fatal = TestCancelled()
                break

        for thread in threads:
            thread.join(timeout=3)

        if erro_fatal:
            raise erro_fatal

        with self._lock:
            total = self._bytes
        decorrido = max(time.monotonic() - base_tempo, 1e-6)
        transferido = max(total - base_bytes, 0)

        if transferido == 0:
            if self._http_status:
                raise NetworkError(
                    f"O servidor recusou o teste de {direcao} "
                    f"(HTTP {self._http_status}). O dominio speed.cloudflare.com "
                    "parece bloqueado nesta rede."
                )
            raise NetworkError(
                f"Nao foi possivel medir o {direcao}. A conexao caiu durante o teste."
            )

        mbps = transferido * 8 / decorrido / 1_000_000
        self._emit(direcao, 1.0, speed=round(mbps, 2), final=True)
        return round(mbps, 2)

    # ------------------------------------------------------------------ workers

    def _download_worker(self, fim: float) -> None:
        sessao = requests.Session()
        sessao.headers.update(HEADERS)
        try:
            while time.monotonic() < fim and not self._cancel.is_set():
                try:
                    with sessao.get(
                        URL_DOWN,
                        params={"bytes": DOWNLOAD_CHUNK_BYTES},
                        stream=True,
                        timeout=15,
                    ) as resposta:
                        if resposta.status_code >= 400:
                            self._http_status = resposta.status_code
                            return
                        for bloco in resposta.iter_content(BLOCK):
                            self._count(len(bloco))
                            if time.monotonic() >= fim or self._cancel.is_set():
                                break
                except requests.RequestException:
                    time.sleep(0.2)  # perda pontual nao invalida o teste
        finally:
            sessao.close()

    def _upload_worker(self, fim: float) -> None:
        sessao = requests.Session()
        sessao.headers.update(HEADERS)
        bloco = os.urandom(BLOCK)
        cabecalhos = {"Content-Type": "application/octet-stream"}
        try:
            while time.monotonic() < fim and not self._cancel.is_set():
                try:
                    resposta = sessao.post(
                        URL_UP,
                        data=self._payload(bloco, fim),
                        headers=cabecalhos,
                        timeout=15,
                    )
                    if resposta.status_code >= 400:
                        self._http_status = resposta.status_code
                        return
                except requests.RequestException:
                    time.sleep(0.2)
        finally:
            sessao.close()

    def _payload(self, bloco: bytes, fim: float):
        enviado = 0
        while enviado < UPLOAD_CHUNK_BYTES:
            if time.monotonic() >= fim or self._cancel.is_set():
                return
            yield bloco
            enviado += len(bloco)
            self._count(len(bloco))

    # ------------------------------------------------------------------ apoio

    def _count(self, quantidade: int) -> None:
        with self._lock:
            self._bytes += quantidade

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise TestCancelled()

    def _emit(self, etapa: str, progresso: float, **extra) -> None:
        payload = {"stage": etapa, "progress": round(progresso, 3)}
        payload.update({k: v for k, v in extra.items() if v is not None})
        try:
            self._on_progress(payload)
        except Exception:  # a UI nunca derruba a medicao
            pass

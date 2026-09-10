"""API exposta ao JavaScript pelo pywebview.

Cada metodo publico desta classe vira `pywebview.api.<metodo>()` no front-end.
O pywebview ja atende cada chamada em uma thread propria, entao a medicao pode
bloquear aqui sem congelar a janela (RNF-09). O progresso e' empurrado no
sentido contrario via `window.evaluate_js`.
"""

from __future__ import annotations

import json
import threading

from core import storage
from core.models import APP_VERSION
from core.paths import hist_dir
from core.speedtest import NetworkError, SpeedTest, TestCancelled


class Api:
    def __init__(self) -> None:
        self._window = None
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._running = False

    def attach(self, window) -> None:
        self._window = window

    # ------------------------------------------------------------------- teste

    def run_test(self) -> dict:
        """Roda o teste completo e grava o resultado em hist/ (RF-02, RF-08)."""
        with self._lock:
            if self._running:
                return {"ok": False, "error": "Ja existe um teste em andamento."}
            self._running = True
            self._cancel = threading.Event()

        try:
            teste = SpeedTest(on_progress=self._push_progress, cancel_event=self._cancel)
            resultado = teste.run()
            caminho = storage.save(resultado)
            payload = resultado.to_dict()
            payload["path"] = str(caminho)
            return {"ok": True, "result": payload}
        except TestCancelled:
            return {"ok": False, "cancelled": True}
        except NetworkError as erro:
            return {"ok": False, "error": str(erro)}
        except OSError as erro:
            return {
                "ok": False,
                "error": f"O teste terminou, mas o historico nao pode ser gravado: {erro}",
            }
        except Exception as erro:  # rede instavel, DNS, proxy corporativo...
            return {"ok": False, "error": f"Falha inesperada durante o teste: {erro}"}
        finally:
            with self._lock:
                self._running = False

    def cancel_test(self) -> dict:
        self._cancel.set()
        return {"ok": True}

    # --------------------------------------------------------------- historico

    def get_history(self) -> dict:
        registros = storage.load_history()
        return {
            "ok": True,
            "items": [r.to_dict() for r in registros],
            "summary": storage.summary(registros),
            "folder": str(hist_dir()),
        }

    def delete_test(self, filename: str) -> dict:
        return {"ok": storage.delete(filename)}

    def open_hist_folder(self) -> dict:
        return {"ok": storage.open_folder()}

    # -------------------------------------------------------------------- app

    def get_info(self) -> dict:
        return {"version": APP_VERSION, "folder": str(hist_dir())}

    def close(self) -> dict:
        self._cancel.set()
        if self._window:
            self._window.destroy()
        return {"ok": True}

    # ------------------------------------------------------------------ apoio

    def _push_progress(self, payload: dict) -> None:
        if not self._window:
            return
        try:
            self._window.evaluate_js(
                f"window.onTestProgress && window.onTestProgress({json.dumps(payload)})"
            )
        except Exception:
            pass  # janela fechada no meio do teste

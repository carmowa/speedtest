"""mowanettest — teste de velocidade de internet para Windows.

Ponto de entrada: cria a janela pywebview e conecta a API Python ao front-end.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import webview  # noqa: E402

from api.bridge import Api  # noqa: E402
from core.models import APP_VERSION  # noqa: E402
from core.paths import resource_dir  # noqa: E402

WINDOW_TITLE = "mowanettest"
WIDTH, HEIGHT = 900, 620
MIN_WIDTH, MIN_HEIGHT = 780, 560
BACKGROUND = "#0F1115"  # evita o flash branco na abertura


def _index_path() -> str:
    caminho = resource_dir() / "ui" / "index.html"
    if not caminho.exists():
        raise SystemExit(f"Interface nao encontrada em {caminho}")
    return str(caminho)


def main() -> None:
    api = Api()

    janela = webview.create_window(
        title=WINDOW_TITLE,
        url=_index_path(),
        js_api=api,
        width=WIDTH,
        height=HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color=BACKGROUND,
        resizable=True,
        text_select=False,
    )
    api.attach(janela)

    try:
        webview.start(debug="--debug" in sys.argv)
    except Exception as erro:
        # Causa mais comum no Windows 10: runtime Edge WebView2 ausente.
        print(
            f"mowanettest {APP_VERSION} nao pode abrir a janela.\n"
            f"Detalhe: {erro}\n\n"
            "Se voce esta no Windows, instale o runtime Edge WebView2 "
            "(Microsoft Edge WebView2 Runtime) e tente novamente.",
            file=sys.stderr,
        )
        raise


if __name__ == "__main__":
    main()

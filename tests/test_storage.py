"""Testes do parser e da persistencia. Rode com: pytest"""

from datetime import datetime
from pathlib import Path

import pytest

from core import paths, storage
from core.models import TestResult


@pytest.fixture
def hist(tmp_path, monkeypatch):
    """Aponta a pasta hist/ para um diretorio temporario."""
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path / "hist"


def amostra(**kwargs) -> TestResult:
    base = dict(
        timestamp=datetime(2026, 9, 10, 15, 57, 34),
        download=248.73, upload=96.41, ping=12.4, jitter=2.1,
        ip="189.1.2.3", provider="Exemplo Telecom",
        server="Cloudflare - GRU", duration=24.8,
    )
    base.update(kwargs)
    return TestResult(**base)


def test_nome_do_arquivo_segue_o_padrao():
    assert amostra().build_filename() == "2026-09-10 15-57-34.txt"


def test_pasta_hist_nasce_no_primeiro_teste(hist):
    assert not hist.exists()
    storage.save(amostra())
    assert hist.is_dir()
    assert (hist / "2026-09-10 15-57-34.txt").is_file()


def test_ida_e_volta_preserva_os_valores(hist):
    caminho = Path(storage.save(amostra()))
    lido = TestResult.from_txt(caminho.read_text(encoding="utf-8"), caminho.name)
    assert lido.download == 248.73
    assert lido.upload == 96.41
    assert lido.ping == 12.4
    assert lido.provider == "Exemplo Telecom"
    assert lido.timestamp == datetime(2026, 9, 10, 15, 57, 34)


def test_dois_testes_no_mesmo_segundo_nao_se_sobrescrevem(hist):
    primeiro = storage.save(amostra())
    segundo = storage.save(amostra(download=10.0))
    assert primeiro != segundo
    assert len(list(hist.glob("*.txt"))) == 2


def test_data_vem_do_nome_quando_falta_no_conteudo(hist):
    hist.mkdir(parents=True)
    (hist / "2026-09-05 20-05-56.txt").write_text(
        "download: 198.02 Mbps\nupload: 74.10 Mbps\n", encoding="utf-8"
    )
    item = storage.load_history()[0]
    assert item.timestamp == datetime(2026, 9, 5, 20, 5, 56)


def test_virgula_decimal_e_linha_estranha_nao_quebram(hist):
    hist.mkdir(parents=True)
    (hist / "2026-09-02 12-01-04.txt").write_text(
        "data: 2026-09-02\nhora: 12:01:04\ndownload: 251,44 Mbps\nlixo aleatorio\n",
        encoding="utf-8",
    )
    assert storage.load_history()[0].download == 251.44


def test_arquivo_sem_dados_e_ignorado(hist):
    storage.save(amostra())
    (hist / "corrompido.txt").write_text("nada util aqui", encoding="utf-8")
    assert len(storage.load_history()) == 1


def test_ordem_do_mais_recente_para_o_mais_antigo(hist):
    storage.save(amostra(timestamp=datetime(2026, 9, 2, 12, 1, 4)))
    storage.save(amostra(timestamp=datetime(2026, 9, 10, 15, 57, 34)))
    storage.save(amostra(timestamp=datetime(2026, 9, 5, 20, 5, 56)))
    datas = [r.timestamp.day for r in storage.load_history()]
    assert datas == [10, 5, 2]


def test_medias_do_resumo(hist):
    storage.save(amostra(download=100.0, upload=50.0))
    storage.save(amostra(timestamp=datetime(2026, 9, 11, 8, 0, 0),
                         download=200.0, upload=70.0))
    resumo = storage.summary(storage.load_history())
    assert resumo == {"count": 2, "avg_download": 150.0,
                      "avg_upload": 60.0, "best_download": 200.0}


@pytest.mark.parametrize("nome", ["../evil.txt", "..\\evil.txt", "sub/dir.txt", "", "x.exe"])
def test_exclusao_rejeita_caminho_perigoso(hist, nome):
    storage.save(amostra())
    assert storage.delete(nome) is False
    assert len(storage.load_history()) == 1


def test_exclusao_remove_o_arquivo(hist):
    caminho = storage.save(amostra())
    assert storage.delete(caminho.name) is True
    assert storage.load_history() == []

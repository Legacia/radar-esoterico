import pytest

import radar.banco as banco


@pytest.fixture
def db(tmp_path, monkeypatch):
    caminho = tmp_path / "teste.db"
    monkeypatch.setattr(banco, "CAMINHO_PADRAO", caminho)
    banco.inicializar(caminho)
    return caminho


@pytest.fixture
def conta(db):
    from radar.usuarios import criar_usuario
    return criar_usuario("Pessoa fictícia", "teste@example.invalid", "senha-ficticia-123", db)

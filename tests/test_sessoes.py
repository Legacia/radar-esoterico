import pytest

from radar.sessoes import criar_sessao, usuario_da_sessao


def test_sessao_dura_oito_horas(monkeypatch):
    import radar.sessoes as sessoes
    monkeypatch.setattr(sessoes.time, "monotonic", lambda: 100)
    sessao = criar_sessao({"id": 1, "nome": "Fictício"})
    monkeypatch.setattr(sessoes.time, "monotonic", lambda: 100 + 8 * 3600 - 1)
    assert usuario_da_sessao(sessao)["id"] == 1
    monkeypatch.setattr(sessoes.time, "monotonic", lambda: 100 + 8 * 3600)
    assert usuario_da_sessao(sessao) is None


@pytest.mark.parametrize("sessao", [None, {}, {"inicio": "invalido"}, {"inicio": 0, "usuario": {}}])
def test_sessao_invalida(sessao):
    assert usuario_da_sessao(sessao) is None

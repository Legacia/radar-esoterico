from fastapi.testclient import TestClient
import pytest

from radar.api import criar_app
from radar.usuarios import autenticar

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


def test_lista_contas_sem_hash_da_senha(cliente):
    contas = cliente.get("/api/contas").json()["contas"]
    assert contas == [{"id": 1, "nome": "Pessoa fictícia", "email": EMAIL}]


def test_quem_entrou_cria_outra_conta_que_consegue_entrar(cliente, db):
    resposta = cliente.post("/api/contas", json={"nome": "Outra pessoa", "email": " Outra@Example.invalid ", "senha": "outra-senha-123"})
    assert resposta.status_code == 200
    assert autenticar("outra@example.invalid", "outra-senha-123", db)["nome"] == "Outra pessoa"
    assert [c["email"] for c in cliente.get("/api/contas").json()["contas"]] == ["outra@example.invalid", EMAIL]


@pytest.mark.parametrize("dados, mensagem", [
    ({"nome": "", "email": "x@example.invalid", "senha": "senha-ficticia-1"}, "Informe o nome."),
    ({"nome": "X", "email": "sem-arroba", "senha": "senha-ficticia-1"}, "Informe um e-mail válido."),
    ({"nome": "X", "email": "x@example.invalid", "senha": "curta"}, "pelo menos 8 caracteres"),
    ({"nome": "X", "email": EMAIL.upper(), "senha": "senha-ficticia-1"}, "Já existe uma conta com esse e-mail."),
])
def test_conta_invalida_explica_em_portugues(cliente, dados, mensagem):
    resposta = cliente.post("/api/contas", json=dados)
    assert resposta.status_code == 400 and mensagem in resposta.json()["detail"]


def test_sem_sessao_nao_cria_conta(db, conta):
    with TestClient(criar_app()) as anonimo:
        resposta = anonimo.post("/api/contas", json={"nome": "Intrusa", "email": "i@example.invalid", "senha": "senha-ficticia-1"})
    assert resposta.status_code == 401
    assert autenticar("i@example.invalid", "senha-ficticia-1", db) is None


def test_trocar_senha_de_outra_conta_encerra_as_sessoes_dela(cliente, db):
    outra = cliente.post("/api/contas", json={"nome": "Outra", "email": "o@example.invalid", "senha": "senha-antiga-1"}).json()["id"]
    with TestClient(cliente.app) as dela:
        dela.post("/api/entrar", json={"email": "o@example.invalid", "senha": "senha-antiga-1"})
        assert dela.get("/api/eu").status_code == 200
        assert cliente.put(f"/api/contas/{outra}/senha", json={"senha": "senha-nova-123"}).status_code == 200
        assert dela.get("/api/eu").status_code == 401
    assert autenticar("o@example.invalid", "senha-antiga-1", db) is None
    assert autenticar("o@example.invalid", "senha-nova-123", db)["id"] == outra
    assert cliente.get("/api/eu").status_code == 200


def test_trocar_a_propria_senha_mantem_esta_sessao(cliente, db):
    assert cliente.put("/api/contas/1/senha", json={"senha": "senha-nova-123"}).status_code == 200
    assert cliente.get("/api/eu").status_code == 200
    assert autenticar(EMAIL, "senha-nova-123", db)["id"] == 1


def test_trocar_senha_invalida_ou_conta_inexistente(cliente):
    assert "pelo menos 8" in cliente.put("/api/contas/1/senha", json={"senha": "curta"}).json()["detail"]
    resposta = cliente.put("/api/contas/99/senha", json={"senha": "senha-nova-123"})
    assert resposta.status_code == 400 and resposta.json()["detail"] == "Conta não encontrada."

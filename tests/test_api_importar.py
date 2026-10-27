from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import radar.api.importar as rota
from radar.api import criar_app
from radar.produtos import salvar_produto

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"
EXEMPLO = Path(__file__).resolve().parents[1] / "exemplos" / "anuncios_ficticios.csv"
CABECALHO = "marketplace;titulo;url;preco;data;produto;sinal\n"


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        c.post("/api/entrar", json={"email": EMAIL, "senha": SENHA})
        yield c


def enviar(cliente, conteudo):
    return cliente.post("/api/importar", content=conteudo, headers={"Content-Type": "text/csv"})


def test_importa_exemplo_e_reimportar_nao_duplica(cliente):
    conteudo = EXEMPLO.read_bytes()
    primeira = enviar(cliente, conteudo).json()
    assert primeira["importadas"] > 0 and primeira["erros"] == []
    segunda = enviar(cliente, conteudo).json()
    assert segunda["importadas"] == 0 and segunda["repetidas"] == primeira["importadas"]


def test_linhas_ruins_viram_relatorio_e_as_boas_entram(cliente, db):
    salvar_produto("Kit fictício", "", "Candidato", caminho=db)
    amanha = (date.today() + timedelta(days=1)).isoformat()
    conteudo = (CABECALHO
        + "Loja;Kit fictício;https://example.invalid/1;59,90;2026-10-20;kit fictício;em alta\n"
        + "Loja;Ruim;ftp://example.invalid/2;10,00;2026-10-20;;\n"
        + f"Loja;Futuro;https://example.invalid/3;10,00;{amanha};;\n"
        + "Loja;Data BR;https://example.invalid/4;10,00;20/10/2026;;\n"
        + "Loja;Sem produto;https://example.invalid/5;10,00;2026-10-20;Inexistente;\n")
    r = enviar(cliente, conteudo.encode()).json()
    assert r["importadas"] == 1
    assert [e["linha"] for e in r["erros"]] == [3, 4, 5, 6]
    assert "http ou https" in r["erros"][0]["erro"]
    assert "data futura" in r["erros"][1]["erro"]
    assert "AAAA-MM-DD" in r["erros"][2]["erro"]
    assert "Produto não encontrado" in r["erros"][3]["erro"]
    anuncio = cliente.get("/api/pesquisa/anuncios").json()["anuncios"][0]
    assert anuncio["produto"] == "Kit fictício"


@pytest.mark.parametrize("conteudo, mensagem", [
    (b"", "Escolha um arquivo CSV."),
    (b"nome;preco\nx;1\n", "Cabeçalho obrigatório"),
    ("marketplace;titulo;url;preco;data\nLoja;Ç;https://e.invalid;1;2026-10-20\n".encode("latin-1"), "UTF-8"),
])
def test_arquivo_invalido_explica(cliente, conteudo, mensagem):
    r = enviar(cliente, conteudo)
    assert r.status_code == 400 and mensagem in r.json()["detail"]


def test_arquivo_grande_demais(cliente, monkeypatch):
    monkeypatch.setattr(rota, "LIMITE_BYTES", 10)
    r = enviar(cliente, CABECALHO.encode())
    assert r.status_code == 400 and "limite é 5 MB" in r.json()["detail"]

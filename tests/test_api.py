from decimal import Decimal

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest

import radar.sessoes as sessoes
from radar.api import criar_app
from radar.api.sessao import COOKIE
from radar.painel import salvar_tarefa

EMAIL, SENHA = "teste@example.invalid", "senha-ficticia-123"


@pytest.fixture
def cliente(db, conta):
    with TestClient(criar_app()) as c:
        yield c


def entrar(cliente, email=EMAIL, senha=SENHA):
    return cliente.post("/api/entrar", json={"email": email, "senha": senha})


def rotas_da_api(app):
    # As rotas vivem só nos dois roteadores de radar.api; o app não pode ter rota solta fora deles.
    import radar.api as api
    from starlette.routing import Mount
    assert len([r for r in app.routes if not isinstance(r, Mount)]) == 2
    return [(m, r.path) for roteador in (api.publico, api.protegido)
            for r in roteador.routes if isinstance(r, APIRoute) for m in r.methods]


def test_toda_rota_exige_sessao_exceto_entrar(cliente):
    rotas = rotas_da_api(cliente.app)
    import radar.api as api
    publicas = [(m, r.path) for r in api.publico.routes for m in r.methods]
    assert publicas == [("POST", "/api/entrar")], "Só entrar pode ficar sem sessão."
    for metodo, caminho in rotas:
        if caminho == "/api/entrar":
            continue
        resposta = cliente.request(metodo, caminho, json={})
        assert resposta.status_code == 401, (metodo, caminho)
        assert resposta.json() == {"detail": "Entre novamente para continuar."}


def test_entrar_grava_cookie_protegido_e_libera_rotas(cliente):
    resposta = entrar(cliente)
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Pessoa fictícia"
    cabecalho = resposta.headers["set-cookie"]
    assert "HttpOnly" in cabecalho and "SameSite=strict" in cabecalho and "Path=/" in cabecalho
    assert SENHA not in cabecalho
    assert cliente.get("/api/eu").json()["nome"] == "Pessoa fictícia"
    assert cliente.get("/api/painel").status_code == 200


def test_erro_de_login_e_generico(cliente):
    errada = entrar(cliente, senha="outra-senha-123")
    inexistente = entrar(cliente, email="ninguem@example.invalid")
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"detail": "E-mail ou senha inválidos."}
    assert "set-cookie" not in errada.headers


def test_email_ignora_maiusculas_e_espacos(cliente):
    assert entrar(cliente, email="  TESTE@Example.Invalid ").status_code == 200


def test_sair_invalida_a_sessao_no_servidor(cliente):
    entrar(cliente)
    token = cliente.cookies.get(COOKIE)
    assert cliente.post("/api/sair").status_code == 200
    # Mesmo quem guardou o cookie antigo não entra mais.
    cliente.cookies.set(COOKIE, token)
    assert cliente.get("/api/eu").status_code == 401


def test_nova_entrada_descarta_sessao_anterior(cliente):
    entrar(cliente)
    antigo = cliente.cookies.get(COOKIE)
    entrar(cliente)
    assert cliente.cookies.get(COOKIE) != antigo
    cliente.cookies.set(COOKIE, antigo)
    assert cliente.get("/api/eu").status_code == 401


def test_cookie_inventado_nao_entra(cliente):
    cliente.cookies.set(COOKIE, "inventado")
    assert cliente.get("/api/eu").status_code == 401


def test_sessao_expira_em_oito_horas_sem_prorrogar(cliente, monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(sessoes.time, "monotonic", lambda: agora[0])
    entrar(cliente)
    agora[0] += sessoes.DURACAO_SEGUNDOS - 1
    assert cliente.get("/api/eu").status_code == 200  # uso não prorroga
    agora[0] += 1
    assert cliente.get("/api/eu").status_code == 401


def test_senhas_erradas_nao_bloqueiam_o_login(cliente):
    # Decisão do Legacia em 27/10/2026: sem bloqueio por tentativas erradas.
    for _ in range(10):
        assert entrar(cliente, senha="errada-123456").status_code == 401
    assert entrar(cliente).status_code == 200


def test_calculadora_caso_obrigatorio_da_margem(cliente):
    entrar(cliente)
    r = cliente.post("/api/calculadora/simular", json={"preco": "59,90", "custo": "20,00"}).json()
    assert Decimal(r["contribuicao"]) == Decimal("14.33")
    assert Decimal(r["margem_pct"]).quantize(Decimal("0.001")) == Decimal("0.239")
    assert r["preco_minimo"] == "55.56"
    # Dinheiro sai como texto, nunca como número de ponto flutuante.
    assert all(isinstance(r[c], str) for c in ("contribuicao", "margem_pct", "preco_minimo"))


def test_calculadora_explica_entrada_invalida(cliente):
    entrar(cliente)
    r = cliente.post("/api/calculadora/simular", json={"preco": "0", "custo": "20"})
    assert r.status_code == 400
    assert r.json()["detail"]


def test_configuracao_em_texto_decimal(cliente):
    entrar(cliente)
    r = cliente.get("/api/configuracao").json()
    assert r["parametros"]["comissao_pct"] == "0.20"
    assert r["parametros"]["tarifa_fixa"] == "4.5"
    assert r["limite_cotacao_dias"] == 15


def test_painel_reconcilia_com_as_regras(cliente, db):
    salvar_tarefa("Tarefa fictícia", 1, "Anna", True, caminho=db)
    entrar(cliente)
    r = cliente.get("/api/painel").json()
    assert r["concluidas"] == 1 and r["tarefas"][0]["responsavel"] == "Anna"
    assert r["orcamento_total_centavos"] == 100000
    assert [e["etapa"] for e in r["funil"]][0] == "Descoberto"


def test_api_nao_publica_lista_de_rotas(cliente):
    for caminho in ("/docs", "/redoc", "/openapi.json"):
        assert cliente.get(caminho).status_code == 404


def test_painel_traz_fracao_comprometida_do_orcamento(cliente):
    entrar(cliente)
    r = cliente.get("/api/painel").json()
    assert r["comprometido_centavos"] == 0
    assert Decimal(r["comprometido_pct"]) == 0


def test_criar_e_concluir_tarefa(cliente):
    entrar(cliente)
    criada = cliente.post("/api/tarefas", json={"titulo": "Pedir amostra fictícia", "semana": 2, "responsavel": "Anna"})
    assert criada.status_code == 200
    tarefa_id = criada.json()["id"]
    alterada = cliente.put(f"/api/tarefas/{tarefa_id}", json={
        "titulo": "Pedir amostra fictícia", "semana": 2, "responsavel": "Anna", "concluida": True})
    assert alterada.status_code == 200
    painel = cliente.get("/api/painel").json()
    assert painel["concluidas"] == 1
    assert painel["tarefas"][0]["titulo"] == "Pedir amostra fictícia"


@pytest.mark.parametrize("dados, mensagem", [
    ({"titulo": " ", "semana": 1, "responsavel": "Anna"}, "título"),
    ({"titulo": "T", "semana": 5, "responsavel": "Anna"}, "semana"),
    ({"titulo": "T", "semana": 1, "responsavel": ""}, "responsável"),
    ({"titulo": "T", "semana": "2", "responsavel": "Anna"}, "formato inválido"),
    ({"titulo": "T", "semana": True, "responsavel": "Anna"}, "formato inválido"),
    ({"titulo": "T", "responsavel": "Anna"}, "formato inválido"),
])
def test_tarefa_invalida_explica_em_portugues(cliente, dados, mensagem):
    entrar(cliente)
    resposta = cliente.post("/api/tarefas", json=dados)
    assert resposta.status_code == 400
    assert mensagem in resposta.json()["detail"].lower()


def test_alterar_tarefa_inexistente(cliente):
    entrar(cliente)
    resposta = cliente.put("/api/tarefas/999", json={"titulo": "T", "semana": 1, "responsavel": "Anna"})
    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Tarefa não encontrada."


PADRAO = {"comissao": "20", "tributo": "6", "margem_alvo": "20", "tarifa_fixa": "4,50",
          "embalagem": "2,50", "outros": "3,00", "limite_cotacao_dias": 15}


def test_configuracao_traz_campos_para_a_tela(cliente):
    entrar(cliente)
    campos = cliente.get("/api/configuracao").json()["campos"]
    assert campos == {"comissao": "20,00", "tributo": "6,00", "margem_alvo": "20,00",
                      "tarifa_fixa": "4,50", "embalagem": "2,50", "outros": "3,00"}


def test_salvar_parametros_muda_a_simulacao(cliente):
    entrar(cliente)
    r = cliente.put("/api/configuracao", json={**PADRAO, "comissao": "14,5", "margem_alvo": "25", "limite_cotacao_dias": 30})
    assert r.status_code == 200
    assert r.json()["parametros"]["comissao_pct"] == "0.145"
    assert r.json()["parametros"]["margem_alvo_pct"] == "0.25"
    assert r.json()["limite_cotacao_dias"] == 30
    simulado = cliente.post("/api/calculadora/simular", json={"preco": "59,90", "custo": "20,00"}).json()
    # 59,90 - 20 - 8,6855 - 4,50 - 2,50 - 3,594 - 3,00 = 17,6205, arredondado pela regra para 17,62
    assert Decimal(simulado["contribuicao"]) == Decimal("17.62")


def test_caso_da_margem_continua_com_os_padroes_salvos(cliente):
    entrar(cliente)
    assert cliente.put("/api/configuracao", json=PADRAO).status_code == 200
    r = cliente.post("/api/calculadora/simular", json={"preco": "59,90", "custo": "20,00"}).json()
    assert Decimal(r["contribuicao"]) == Decimal("14.33")
    assert r["preco_minimo"] == "55.56"


@pytest.mark.parametrize("campos, mensagem", [
    ({"comissao": "abc"}, "Informe um número"),
    ({"tarifa_fixa": "4,555"}, "duas casas"),
    ({"comissao": "60", "tributo": "30", "margem_alvo": "20"}, ""),
    ({"limite_cotacao_dias": 0}, "entre 1 e 3650"),
    ({"limite_cotacao_dias": "15"}, "formato inválido"),
])
def test_parametros_invalidos_nao_salvam(cliente, campos, mensagem):
    entrar(cliente)
    antes = cliente.get("/api/configuracao").json()
    r = cliente.put("/api/configuracao", json={**PADRAO, **campos})
    if r.status_code == 200:
        # Soma de 110% é aceita como parâmetro; a calculadora avisa que não existe preço mínimo.
        aviso = cliente.post("/api/calculadora/simular", json={"preco": "59,90", "custo": "20"}).json()["aviso_preco_minimo"]
        assert "menor que 100%" in aviso
        return
    assert r.status_code == 400 and mensagem in r.json()["detail"]
    assert cliente.get("/api/configuracao").json() == antes

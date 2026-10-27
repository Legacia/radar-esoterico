"""Revisão da API: cenários de proteção que faltavam na entrega inicial.

Tudo usa banco e arquivos temporários. Não sobe servidor nem usa data/radar.db.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from http.cookies import SimpleCookie
from threading import Barrier

from argon2 import extract_parameters
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import radar.api as api
import radar.usuarios as usuarios
from radar.api.limite import JANELA_SEGUNDOS, MAXIMO_FALHAS, LimiteTentativas
from radar.api.sessao import COOKIE, Sessoes
from radar.margem.configuracao import obter_configuracao, salvar_configuracao
from tests.test_api import rotas_da_api

EMAIL = "teste@example.invalid"
SENHA = "senha-ficticia-123"


@pytest.fixture
def cliente(db, conta, tmp_path, monkeypatch):
    monkeypatch.setattr(api, "INTERFACE", tmp_path / "sem_interface")
    with TestClient(api.criar_app()) as cliente:
        yield cliente


def entrar(cliente, **alteracoes):
    return cliente.post("/api/entrar", json={"email": EMAIL, "senha": SENHA, **alteracoes})


def test_senha_correta_entra_mesmo_apos_cinco_falhas(cliente):
    for _ in range(MAXIMO_FALHAS):
        assert entrar(cliente, senha="incorreta-ficticia").status_code == 401
    assert entrar(cliente, senha="incorreta-ficticia").status_code == 429
    assert entrar(cliente).status_code == 200
    assert cliente.get("/api/eu").status_code == 200
    # O acerto limpa o contador: uma nova falha não herda o bloqueio.
    assert entrar(cliente, senha="incorreta-ficticia").status_code == 401


@pytest.mark.parametrize("corpo", [{"senha": SENHA}, {"email": {"senha": SENHA}, "senha": SENHA}])
def test_validacao_de_login_nao_devolve_senha_no_erro(cliente, corpo):
    resposta = cliente.post("/api/entrar", json=corpo)
    assert resposta.status_code == 422
    assert SENHA not in resposta.text
    assert resposta.json() == {"detail": "Dados de entrada inválidos. Confira os campos informados."}


@pytest.mark.parametrize("caminho", ["/api/arquivo.json", "/%61pi/arquivo.json",
    "/publico/%2e%2e/api/arquivo.json", "/publico%5c..%5capi/arquivo.json"])
def test_estaticos_nao_burlam_login_no_namespace_da_api(db, conta, tmp_path, monkeypatch, caminho):
    interface = tmp_path / "interface"
    (interface / "api").mkdir(parents=True)
    (interface / "index.html").write_text("<h1>Login fictício</h1>", encoding="utf-8")
    (interface / "api" / "arquivo.json").write_text('{"dado_ficticio": true}', encoding="utf-8")
    monkeypatch.setattr(api, "INTERFACE", interface)
    with TestClient(api.criar_app()) as cliente:
        assert cliente.get("/").status_code == 200  # O shell do login é público.
        resposta = cliente.get(caminho)
        assert resposta.status_code == 401
        assert "dado_ficticio" not in resposta.text
        assert cliente.get("/api/painel").status_code == 401
        assert cliente.get("/api/entrar").status_code == 401  # Só POST é público.


def test_inventario_de_rotas_nao_ignora_subaplicacao_api(cliente):
    subapp = FastAPI()
    subapp.add_api_route("/dados", lambda: {"ficticio": True})
    cliente.app.mount("/api/futura", subapp)
    with pytest.raises(AssertionError):
        rotas_da_api(cliente.app)


def test_rota_montada_sem_dependencia_nao_vaza_dados(cliente):
    subapp = FastAPI()
    subapp.add_api_route("/dados", lambda: {"ficticio": True})
    cliente.app.mount("/api/futura", subapp)
    assert cliente.get("/api/futura/dados").status_code == 401


def test_rota_nova_fora_dos_dois_roteadores_e_detectada(cliente):
    cliente.app.add_api_route("/api/esquecida", lambda: {"ficticio": True})
    with pytest.raises(AssertionError):
        rotas_da_api(cliente.app)


def test_sem_sessao_corpo_invalido_nao_passa_pela_validacao(cliente):
    resposta = cliente.post("/api/calculadora/simular", content='{"preco":', headers={"Content-Type": "application/json"})
    assert resposta.status_code == 401


def test_verificacao_argon_e_equivalente_para_email_ausente_e_senha_errada(cliente, monkeypatch):
    hashes = []
    classe_hasher = type(usuarios._HASHER)
    verificar = classe_hasher.verify

    def observar(hasher, senha_hash, senha):
        hashes.append(senha_hash)
        return verificar(hasher, senha_hash, senha)

    monkeypatch.setattr(classe_hasher, "verify", observar)
    real = entrar(cliente, senha="incorreta-ficticia")
    ausente = entrar(cliente, email="ausente@example.invalid", senha="incorreta-ficticia")
    assert real.status_code == ausente.status_code == 401
    assert real.json() == ausente.json()
    assert len(hashes) == 2
    assert extract_parameters(hashes[0]) == extract_parameters(hashes[1])


def test_bloqueio_expira_na_janela_e_isola_ips():
    agora = [0]
    limite = LimiteTentativas(relogio=lambda: agora[0])
    for _ in range(MAXIMO_FALHAS):
        limite.falhou("ip-ficticio-a")
    assert limite.bloqueado("ip-ficticio-a")
    assert not limite.bloqueado("ip-ficticio-b")
    agora[0] = JANELA_SEGUNDOS - 1
    assert limite.bloqueado("ip-ficticio-a")
    agora[0] = JANELA_SEGUNDOS
    assert not limite.bloqueado("ip-ficticio-a")


def test_respostas_concorrentes_respeitam_cinco_falhas_atomicamente():
    limite = LimiteTentativas(relogio=lambda: 0)
    with ThreadPoolExecutor(max_workers=8) as executor:
        aceitas = list(executor.map(lambda _: limite.falhou("ip-ficticio"), range(24)))
    assert aceitas.count(True) == MAXIMO_FALHAS
    assert aceitas.count(False) == 24 - MAXIMO_FALHAS


def test_pedidos_concorrentes_na_api_nao_ultrapassam_cinco_falhas(cliente, monkeypatch):
    barreira = Barrier(8)

    def autenticar_ficticio(email, senha):
        barreira.wait(timeout=10)
        return None

    monkeypatch.setattr(api, "autenticar", autenticar_ficticio)

    def tentar(_):
        with TestClient(cliente.app) as outro:
            return entrar(outro, senha="incorreta-ficticia").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        respostas = list(executor.map(tentar, range(8)))
    assert respostas.count(401) == MAXIMO_FALHAS
    assert respostas.count(429) == 8 - MAXIMO_FALHAS


def test_bloqueio_na_api_nao_e_compartilhado_com_outro_ip(cliente):
    for _ in range(MAXIMO_FALHAS):
        entrar(cliente, senha="incorreta-ficticia")
    assert entrar(cliente, senha="incorreta-ficticia").status_code == 429
    with TestClient(cliente.app, client=("192.0.2.20", 50000)) as outro:
        assert entrar(outro, senha="incorreta-ficticia").status_code == 401


def test_cookie_tem_todas_as_flags_e_nao_e_renovado_no_uso(cliente):
    resposta = entrar(cliente)
    cookie = SimpleCookie()
    cookie.load(resposta.headers["set-cookie"])
    sessao = cookie[COOKIE]
    assert sessao["httponly"]
    assert sessao["samesite"] == "strict"
    assert sessao["max-age"] == str(8 * 60 * 60)
    assert sessao["path"] == "/"
    assert not sessao["secure"]
    assert len(sessao.value) >= 43
    assert EMAIL not in sessao.value and SENHA not in sessao.value
    assert "set-cookie" not in cliente.get("/api/eu").headers


def test_duas_pessoas_tem_sessoes_independentes(cliente, db):
    usuarios.criar_usuario("Segunda pessoa fictícia", "outra@example.invalid", "outra-ficticia-123", db)
    assert entrar(cliente).status_code == 200
    with TestClient(cliente.app) as outro:
        assert entrar(outro, email="outra@example.invalid", senha="outra-ficticia-123").status_code == 200
        assert outro.cookies.get(COOKIE) != cliente.cookies.get(COOKIE)
        assert outro.post("/api/sair").status_code == 200
        assert cliente.get("/api/eu").json()["nome"] == "Pessoa fictícia"


def test_sessoes_concorrentes_nao_misturam_usuarios():
    sessoes = Sessoes()

    def exercitar(numero):
        usuario = {"id": numero + 1, "nome": f"Pessoa fictícia {numero}"}
        token = sessoes.abrir(usuario)
        assert sessoes.usuario(token) == usuario
        sessoes.fechar(token)
        assert sessoes.usuario(token) is None
        return token

    with ThreadPoolExecutor(max_workers=8) as executor:
        tokens = list(executor.map(exercitar, range(40)))
    assert len(set(tokens)) == len(tokens)


def test_calculadora_trata_alvo_impossivel_sem_perder_contribuicao(cliente, db):
    p = obter_configuracao(db).parametros
    salvar_configuracao(replace(p, margem_alvo_pct=Decimal("0.90")), 15, db)
    entrar(cliente)
    resposta = cliente.post("/api/calculadora/simular", json={"preco": "59.90", "custo": "20.00"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["contribuicao"] == "14.33"
    assert dados["preco_minimo"] is None
    assert "Não existe preço mínimo" in dados["aviso_preco_minimo"]


def test_erro_de_regra_e_em_portugues_sem_repetir_a_entrada(cliente):
    entrar(cliente)
    resposta = cliente.post("/api/calculadora/simular", json={"preco": "entrada-ficticia-nao-numerica", "custo": "20.00"})
    assert resposta.status_code == 400
    assert resposta.json() == {"detail": "Informe um número, por exemplo 20,00 ou 1.234,56."}
    assert "entrada-ficticia-nao-numerica" not in resposta.text


def test_json_de_rotas_nao_contem_numeros_float(cliente):
    def verificar(valor):
        assert not isinstance(valor, float)
        if isinstance(valor, dict):
            for filho in valor.values():
                verificar(filho)
        elif isinstance(valor, list):
            for filho in valor:
                verificar(filho)

    entrar(cliente)
    for caminho in ("/api/eu", "/api/painel", "/api/configuracao"):
        verificar(cliente.get(caminho).json())
    verificar(cliente.post("/api/calculadora/simular", json={"preco": "59.90", "custo": "20.00"}).json())


@pytest.mark.parametrize("argumentos,endereco,porta", [
    ([], "0.0.0.0", 8501),
    (["--endereco", "127.0.0.1", "--porta", "8502"], "127.0.0.1", 8502),
])
def test_comando_do_servidor_configura_host_e_porta_sem_subir_servidor(monkeypatch, argumentos, endereco, porta):
    import radar.servidor as servidor

    aplicativo = object()
    chamadas = []
    monkeypatch.setattr(servidor, "criar_app", lambda: aplicativo)
    monkeypatch.setattr(servidor.uvicorn, "run", lambda app, **kwargs: chamadas.append((app, kwargs)))
    servidor.main(argumentos)
    assert chamadas == [(aplicativo, {"host": endereco, "port": porta})]

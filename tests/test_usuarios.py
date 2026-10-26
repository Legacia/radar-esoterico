import pytest
from argon2 import PasswordHasher

from radar.banco import conectar
from radar.usuarios import autenticar, criar_usuario, redefinir_senha, main


def test_cria_usuario_com_hash(conta, db):
    with conectar(db) as c:
        usuario = c.execute("SELECT * FROM usuario").fetchone()
    assert usuario["id"] == conta
    assert usuario["senha_hash"].startswith("$argon2id$")
    assert "senha-ficticia-123" not in usuario["senha_hash"]
    assert PasswordHasher().verify(usuario["senha_hash"], "senha-ficticia-123")


def test_login_correto_normaliza_email(conta, db):
    assert autenticar(" TESTE@EXAMPLE.INVALID ", "senha-ficticia-123", db) == {
        "id": conta, "nome": "Pessoa fictícia"}


@pytest.mark.parametrize("email,senha", [
    ("teste@example.invalid", "errada"), ("ausente@example.invalid", "senha-ficticia-123"),
    ("' OR 1=1 --", "senha-ficticia-123"), ("", ""),
])
def test_login_incorreto(conta, db, email, senha):
    assert autenticar(email, senha, db) is None


def test_email_duplicado_sem_diferenciar_maiusculas(conta, db):
    with pytest.raises(ValueError, match="Já existe"):
        criar_usuario("Outro fictício", "TESTE@example.invalid", "outra-ficticia-123", db)


@pytest.mark.parametrize("nome,email,senha", [
    ("", "teste@example.invalid", "senha-ficticia-123"),
    ("Teste", "sem-arroba", "senha-ficticia-123"),
    ("Teste", "teste@example.invalid", "curta"),
])
def test_validacao_cadastro(db, nome, email, senha):
    with pytest.raises(ValueError):
        criar_usuario(nome, email, senha, db)


def test_hashs_tem_sal_proprio(db):
    criar_usuario("Um", "um@example.invalid", "senha-ficticia-123", db)
    criar_usuario("Dois", "dois@example.invalid", "senha-ficticia-123", db)
    with conectar(db) as c:
        hashes = [r[0] for r in c.execute("SELECT senha_hash FROM usuario")]
    assert hashes[0] != hashes[1]


def test_redefinir_invalida_senha_antiga(conta, db):
    redefinir_senha("teste@example.invalid", "nova-ficticia-456", db)
    assert autenticar("teste@example.invalid", "senha-ficticia-123", db) is None
    assert autenticar("teste@example.invalid", "nova-ficticia-456", db)["id"] == conta


def test_redefinir_ausente(db):
    with pytest.raises(ValueError, match="não encontrada"):
        redefinir_senha("ausente@example.invalid", "nova-ficticia-456", db)


def test_hash_corrompido_falha_fechado(conta, db):
    with conectar(db) as c:
        c.execute("UPDATE usuario SET senha_hash='invalido'")
    assert autenticar("teste@example.invalid", "senha-ficticia-123", db) is None


def test_comando_criar_e_redefinir(db, monkeypatch, capsys):
    import radar.usuarios as usuarios
    respostas = iter(["Pessoa fictícia", "cli@example.invalid"])
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))
    monkeypatch.setattr(usuarios, "getpass", lambda _: "senha-ficticia-123")
    assert main(["criar"]) == 0
    assert autenticar("cli@example.invalid", "senha-ficticia-123", db)
    monkeypatch.setattr("builtins.input", lambda _: "cli@example.invalid")
    monkeypatch.setattr(usuarios, "getpass", lambda _: "nova-ficticia-456")
    assert main(["redefinir"]) == 0
    assert autenticar("cli@example.invalid", "senha-ficticia-123", db) is None
    assert autenticar("cli@example.invalid", "nova-ficticia-456", db)
    saida = capsys.readouterr().out
    assert "senha-ficticia-123" not in saida
    assert "nova-ficticia-456" not in saida


def test_comando_senhas_diferentes_nao_cria(db, monkeypatch):
    import radar.usuarios as usuarios
    respostas = iter(["Fictício", "cli@example.invalid"])
    senhas = iter(["senha-ficticia-123", "outra-ficticia-456"])
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))
    monkeypatch.setattr(usuarios, "getpass", lambda _: next(senhas))
    assert main(["criar"]) == 1
    with conectar(db) as c:
        assert c.execute("SELECT count(*) FROM usuario").fetchone()[0] == 0

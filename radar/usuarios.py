"""Contas locais: criadas pela tela Contas (por quem já entrou) ou pelo terminal do servidor."""
import argparse
from getpass import getpass
import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from radar.banco import conectar, inicializar

_HASHER = PasswordHasher()
# Hash efêmero para executar a mesma verificação quando o e-mail não existe.
_HASH_AUSENTE = _HASHER.hash(__import__("secrets").token_urlsafe(32))


def normalizar_email(email):
    email = email.strip().casefold()
    if len(email) > 254 or email.count("@") != 1 or any(c.isspace() for c in email):
        raise ValueError("Informe um e-mail válido.")
    local, dominio = email.split("@")
    if not local or not dominio or "." not in dominio or dominio.startswith(".") or dominio.endswith("."):
        raise ValueError("Informe um e-mail válido.")
    return email


def _validar_senha(senha):
    if len(senha) < 8:
        raise ValueError("Use uma senha com pelo menos 8 caracteres.")


def criar_usuario(nome, email, senha, caminho=None):
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe o nome.")
    email = normalizar_email(email)
    _validar_senha(senha)
    senha_hash = _HASHER.hash(senha)
    with conectar(caminho) as conexao:
        try:
            cursor = conexao.execute(
                "INSERT INTO usuario(nome, email, senha_hash) VALUES (?, ?, ?)",
                (nome, email, senha_hash),
            )
        except sqlite3.IntegrityError as erro:
            raise ValueError("Já existe uma conta com esse e-mail.") from erro
        return cursor.lastrowid


def redefinir_senha(email, senha, caminho=None):
    email = normalizar_email(email)
    _validar_senha(senha)
    senha_hash = _HASHER.hash(senha)
    with conectar(caminho) as conexao:
        cursor = conexao.execute("UPDATE usuario SET senha_hash = ? WHERE email = ?", (senha_hash, email))
        if cursor.rowcount != 1:
            raise ValueError("Conta não encontrada.")


def redefinir_senha_por_id(usuario_id, senha, caminho=None):
    _validar_senha(senha)
    senha_hash = _HASHER.hash(senha)
    with conectar(caminho) as conexao:
        cursor = conexao.execute("UPDATE usuario SET senha_hash = ? WHERE id = ?", (senha_hash, usuario_id))
        if cursor.rowcount != 1:
            raise ValueError("Conta não encontrada.")


def listar_usuarios(caminho=None):
    """Nome e e-mail de cada conta; o hash da senha nunca sai daqui."""
    with conectar(caminho) as conexao:
        linhas = conexao.execute("SELECT id, nome, email FROM usuario ORDER BY nome COLLATE NOCASE, id").fetchall()
    return [dict(linha) for linha in linhas]


def autenticar(email, senha, caminho=None):
    email = email.strip().casefold()
    with conectar(caminho) as conexao:
        usuario = conexao.execute("SELECT id, nome, senha_hash FROM usuario WHERE email = ?", (email,)).fetchone()
    senha_hash = usuario["senha_hash"] if usuario else _HASH_AUSENTE
    try:
        _HASHER.verify(senha_hash, senha)
    except (VerificationError, InvalidHashError):
        return None
    if usuario is None:
        return None
    return {"id": usuario["id"], "nome": usuario["nome"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gerenciar contas do Radar no servidor.")
    parser.add_argument("acao", choices=["criar", "redefinir"])
    args = parser.parse_args(argv)
    try:
        nome = input("Nome: ") if args.acao == "criar" else None
        email = input("E-mail: ")
        senha = getpass("Senha (mínimo 8 caracteres): ")
        if senha != getpass("Repita a senha: "):
            raise ValueError("As senhas não coincidem.")
        inicializar()
        if args.acao == "criar":
            criar_usuario(nome, email, senha)
        else:
            redefinir_senha(email, senha)
    except (ValueError, EOFError, KeyboardInterrupt) as erro:
        print(str(erro) or "Operação cancelada.")
        return 1
    print("Conta criada." if args.acao == "criar" else "Senha redefinida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

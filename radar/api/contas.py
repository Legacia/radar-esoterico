"""Rotas da tela Contas: quem já entrou cadastra outra pessoa ou troca uma senha.

Não existe cadastro aberto: estas rotas ficam no roteador protegido (decisão do Legacia em 28/10/2026).
"""
from fastapi import Depends, Request
from pydantic import BaseModel

from radar.api import protegido
from radar.api.sessao import COOKIE, exigir_sessao
from radar.usuarios import criar_usuario, listar_usuarios, redefinir_senha_por_id


class NovaConta(BaseModel):
    nome: str
    email: str
    senha: str


class NovaSenha(BaseModel):
    senha: str


@protegido.get("/contas")
def contas():
    return {"contas": listar_usuarios()}


@protegido.post("/contas")
def criar_conta(dados: NovaConta):
    return {"id": criar_usuario(dados.nome, dados.email, dados.senha)}


@protegido.put("/contas/{usuario_id}/senha")
def trocar_senha(usuario_id: int, dados: NovaSenha, request: Request, usuario: dict = Depends(exigir_sessao)):
    redefinir_senha_por_id(usuario_id, dados.senha)
    # Senha nova encerra as sessões abertas com a antiga; quem trocou a própria continua conectado.
    request.app.state.sessoes.fechar_do_usuario(usuario_id, exceto=request.cookies.get(COOKIE))
    return {"ok": True}

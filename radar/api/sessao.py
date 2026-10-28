"""Sessões guardadas no servidor; o navegador recebe só um identificador aleatório.

Reiniciar o servidor encerra todas as sessões.
"""
import secrets
from threading import Lock

from fastapi import HTTPException, Request

from radar.sessoes import DURACAO_SEGUNDOS, criar_sessao, usuario_da_sessao

COOKIE = "radar_sessao"


class Sessoes:
    def __init__(self):
        self._dados = {}
        self._trava = Lock()

    def abrir(self, usuario):
        token = secrets.token_urlsafe(32)
        with self._trava:
            self._limpar()
            self._dados[token] = criar_sessao(usuario)
        return token

    def usuario(self, token):
        if not token:
            return None
        with self._trava:
            sessao = self._dados.get(token)
            usuario = usuario_da_sessao(sessao)
            if usuario is None:
                self._dados.pop(token, None)
            return usuario

    def fechar(self, token):
        with self._trava:
            self._dados.pop(token, None)

    def fechar_do_usuario(self, usuario_id, exceto=None):
        """Encerra as sessões de uma conta (senha trocada), menos a do próprio navegador, se indicada."""
        with self._trava:
            for token in [t for t, s in self._dados.items()
                          if t != exceto and s.get("usuario", {}).get("id") == usuario_id]:
                del self._dados[token]

    def _limpar(self):
        # Remove expiradas para a memória não crescer com logins antigos.
        for token in [t for t, s in self._dados.items() if usuario_da_sessao(s) is None]:
            del self._dados[token]


def gravar_cookie(resposta, token):
    # HttpOnly: o JavaScript da página não lê o cookie. SameSite=Strict: outro site não o envia.
    # Sem Secure porque o Radar roda em HTTP na rede doméstica (limite registrado no AGENTS.md).
    resposta.set_cookie(COOKIE, token, max_age=DURACAO_SEGUNDOS, httponly=True, samesite="strict", path="/")


def apagar_cookie(resposta):
    resposta.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")


def exigir_sessao(request: Request):
    """Dependência aplicada a todas as rotas da API, exceto entrar."""
    usuario = request.app.state.sessoes.usuario(request.cookies.get(COOKIE))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Entre novamente para continuar.")
    return usuario

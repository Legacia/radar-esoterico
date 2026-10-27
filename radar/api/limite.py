"""Freio simples contra quem tenta adivinhar senhas na rede da casa."""
import time
from threading import Lock

MAXIMO_FALHAS = 5
JANELA_SEGUNDOS = 5 * 60


class LimiteTentativas:
    def __init__(self, relogio=time.monotonic):
        self._falhas = {}
        self._trava = Lock()
        self._relogio = relogio

    def _recentes(self, origem):
        agora = self._relogio()
        falhas = [t for t in self._falhas.get(origem, []) if agora - t < JANELA_SEGUNDOS]
        self._falhas[origem] = falhas
        return falhas

    def bloqueado(self, origem):
        with self._trava:
            return len(self._recentes(origem)) >= MAXIMO_FALHAS

    def falhou(self, origem):
        with self._trava:
            self._recentes(origem).append(self._relogio())

    def acertou(self, origem):
        with self._trava:
            self._falhas.pop(origem, None)

"""Sessão com duração absoluta de oito horas, sem prorrogação por atividade."""
import time

DURACAO_SEGUNDOS = 8 * 60 * 60


def criar_sessao(usuario):
    return {"usuario": dict(usuario), "inicio": time.monotonic()}


def usuario_da_sessao(sessao):
    if not isinstance(sessao, dict):
        return None
    inicio = sessao.get("inicio")
    if not isinstance(inicio, (int, float)):
        return None
    idade = time.monotonic() - inicio
    if not 0 <= idade < DURACAO_SEGUNDOS:
        return None
    usuario = sessao.get("usuario")
    if not isinstance(usuario, dict) or not usuario.get("id") or not usuario.get("nome"):
        return None
    return dict(usuario)

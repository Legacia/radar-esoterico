"""Contrato opcional; o aplicativo não depende de uma API de marketplace."""
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class AnuncioObservado:
    marketplace: str
    titulo: str
    url: str
    preco: Decimal
    data: date
    sinal: str | None = None


class ConectorMarketplace(ABC):
    @abstractmethod
    def buscar(self, termo: str) -> Iterable[AnuncioObservado]:
        """Retornar anúncios; nenhum conector real é implementado no MVP 0.1."""
        raise NotImplementedError

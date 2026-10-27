// Tabela ordenável. Cada coluna diz como mostrar o valor e, se quiser, por qual chave ordenar.
// A ordenação compara textos e inteiros (centavos, quantidades), nunca reais em ponto flutuante.
import { useMemo, useState, type ReactNode } from "react";

export type Coluna<T> = {
  chave: string;
  titulo: string;
  mostrar: (linha: T) => ReactNode;
  ordenar?: (linha: T) => string | number | bigint | null;
  alinhar?: "direita";
};

type Ordem = { chave: string; crescente: boolean } | null;

function comparar(a: string | number | bigint | null, b: string | number | bigint | null): number {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
  if (typeof a === "string" && typeof b === "string") return a.localeCompare(b, "pt-BR", { sensitivity: "base" });
  return a < b ? -1 : a > b ? 1 : 0;
}

export function Tabela<T>({ titulo, colunas, linhas, chaveLinha, vazio = "Nada cadastrado ainda.", aoClicar }: {
  titulo: string;
  colunas: Coluna<T>[];
  linhas: T[];
  chaveLinha: (linha: T) => string | number;
  vazio?: string;
  aoClicar?: (linha: T) => void;
}) {
  const [ordem, setOrdem] = useState<Ordem>(null);
  const ordenadas = useMemo(() => {
    const coluna = colunas.find((c) => c.chave === ordem?.chave);
    if (!ordem || !coluna?.ordenar) return linhas;
    const chave = coluna.ordenar;
    // Nulos ficam no fim nos dois sentidos.
    return [...linhas].sort((a, b) => {
      const [x, y] = [chave(a), chave(b)];
      if (x === null || y === null) return comparar(x, y);
      return ordem.crescente ? comparar(x, y) : comparar(y, x);
    });
  }, [linhas, colunas, ordem]);

  if (!linhas.length) return <p className="vazio">{vazio}</p>;

  const alternar = (chave: string) =>
    setOrdem((atual) => (atual?.chave === chave ? { chave, crescente: !atual.crescente } : { chave, crescente: true }));

  return (
    <div className="tabela-moldura">
      <table className="tabela">
        <caption className="so-leitor">{titulo}</caption>
        <thead>
          <tr>
            {colunas.map((c) => {
              const ativa = ordem?.chave === c.chave;
              return (
                <th key={c.chave} scope="col" className={c.alinhar === "direita" ? "direita" : undefined}
                  aria-sort={ativa ? (ordem!.crescente ? "ascending" : "descending") : undefined}>
                  {c.ordenar ? (
                    <button type="button" className="ordenar" onClick={() => alternar(c.chave)}>
                      {c.titulo}
                      <span aria-hidden="true">{ativa ? (ordem!.crescente ? " ▲" : " ▼") : " ↕"}</span>
                    </button>
                  ) : c.titulo}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {ordenadas.map((linha) => (
            <tr key={chaveLinha(linha)} className={aoClicar ? "clicavel" : undefined}
              tabIndex={aoClicar ? 0 : undefined}
              onClick={aoClicar ? () => aoClicar(linha) : undefined}
              onKeyDown={aoClicar ? (e) => { if (e.key === "Enter") aoClicar(linha); } : undefined}>
              {colunas.map((c) => (
                <td key={c.chave} className={c.alinhar === "direita" ? "direita" : undefined}>{c.mostrar(linha)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

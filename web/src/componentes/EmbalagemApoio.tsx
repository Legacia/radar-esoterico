// Embalagem de um produto ou de um kit: os itens de apoio indicados (caixa, sacola, papel...) e a
// embalagem que vale na conta. A soma e as margens vêm prontas da API; aqui só se mostra e se indica.
import { useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { reais, reaisDeCentavos, dataBr } from "../formato";
import { enderecoDe } from "../rotas";
import { Aviso, Selo } from "./basicos";
import { mensagemDeErro } from "./gravacao";
import { Tabela } from "./Tabela";

export type ItemIndicado = {
  id: number; nome: string; fornecedor: string | null; custo_centavos: number; data_cotacao: string;
  quantidade: number; subtotal_centavos: number;
};
export type Apoio = { itens: ItemIndicado[]; embalagem_centavos: number | null };
type ItemOpcao = { id: number; nome: string; custo_centavos: number };

export function EmbalagemApoio({ apoio, padrao, caminho, quem, ocupado, gravar }: {
  apoio: Apoio;
  /** Embalagem padrão da configuração, em texto decimal ("2.50"). */
  padrao: string;
  /** Rota base da indicação, por exemplo "/produtos/3/apoio". */
  caminho: string;
  /** "do produto" ou "do kit", para os textos. */
  quem: string;
  ocupado: boolean;
  gravar: (acao: () => Promise<unknown>, sucesso: string) => Promise<unknown>;
}) {
  const [opcoes, setOpcoes] = useState<ItemOpcao[] | null>(null);
  const [itemId, setItemId] = useState<number | null>(null);
  const [quantidade, setQuantidade] = useState("1");
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let valido = true;
    pedir<{ itens: ItemOpcao[] }>("/apoio").then((r) => {
      if (!valido) return;
      setOpcoes(r.itens);
      setItemId(r.itens[0]?.id ?? null);
    }, (e) => { if (valido) setErro(mensagemDeErro(e)); });
    return () => { valido = false; };
  }, []);

  async function indicar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    // Quantidade é um inteiro de unidades, não dinheiro; o servidor confere de novo.
    if (!/^\d{1,4}$/.test(quantidade.trim()) || Number(quantidade) < 1) return setErro("A quantidade deve ser um inteiro de 1 a 1000.");
    if (itemId === null) return;
    try {
      await gravar(() => pedir(`${caminho}/${itemId}`, { metodo: "PUT", corpo: { quantidade: Number.parseInt(quantidade, 10) } }),
        "Item de apoio indicado.");
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  const propria = apoio.embalagem_centavos !== null;
  return (
    <div className="pilha">
      <p>
        Embalagem usada no cálculo de margem: <strong>
          {propria ? reaisDeCentavos(apoio.embalagem_centavos!) : reais(padrao)}
        </strong>{" "}
        {propria ? <Selo tom="azul">Soma dos itens {quem}</Selo> : <Selo>Padrão da configuração</Selo>}
      </p>
      <Tabela titulo={`Itens de apoio ${quem}`} linhas={apoio.itens} chaveLinha={(i) => i.id}
        vazio={`Nenhum item indicado: vale a embalagem padrão (${reais(padrao)}).`} colunas={[
          { chave: "nome", titulo: "Item", mostrar: (i) => i.nome, ordenar: (i) => i.nome },
          { chave: "fornecedor", titulo: "Fornecedor", mostrar: (i) => i.fornecedor ?? "—" },
          { chave: "custo", titulo: "Custo unitário", alinhar: "direita", mostrar: (i) => `${reaisDeCentavos(i.custo_centavos)} · ${dataBr(i.data_cotacao)}` },
          { chave: "quantidade", titulo: "Quantidade", alinhar: "direita", mostrar: (i) => i.quantidade },
          { chave: "subtotal", titulo: "Subtotal", alinhar: "direita", mostrar: (i) => reaisDeCentavos(i.subtotal_centavos), ordenar: (i) => i.subtotal_centavos },
          { chave: "retirar", titulo: "Ação", mostrar: (i) => (
            <button type="button" className="botao-discreto link" disabled={ocupado} aria-label={`Retirar ${i.nome}`}
              onClick={() => gravar(() => pedir(`${caminho}/${i.id}`, { metodo: "DELETE" }), "Item de apoio retirado.").catch(() => {})}>
              Retirar
            </button>
          ) },
        ]} />
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {opcoes === null ? <p className="legenda">Carregando itens de apoio…</p> : !opcoes.length ? (
        <Aviso>Cadastre caixas, sacolas e outros itens na tela <a href={enderecoDe("apoio")}>Itens de apoio</a>.</Aviso>
      ) : (
        <form className="formulario" onSubmit={indicar}>
          <div className="campos-2">
            <label>Item de apoio
              <select value={itemId ?? ""} onChange={(e) => setItemId(Number(e.target.value))}>
                {opcoes.map((o) => <option key={o.id} value={o.id}>{o.nome} · {reaisDeCentavos(o.custo_centavos)}</option>)}
              </select>
            </label>
            <label>Quantidade por unidade vendida
              <input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} />
            </label>
          </div>
          <p className="legenda">Indicar de novo um item já usado troca a quantidade.</p>
          <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Indicar item"}</button></div>
        </form>
      )}
    </div>
  );
}

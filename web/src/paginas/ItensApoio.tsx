// Itens de apoio: caixas, sacolas, papel de seda e outros materiais de envio, com custo, fornecedor
// e data. Cada produto e cada kit indica os seus na própria ficha; a soma substitui a embalagem padrão.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Painel as Caixa } from "../componentes/basicos";
import { BotaoExcluir } from "../componentes/Excluir";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela } from "../componentes/Tabela";
import { dataBr, hojeIso, reaisDeCentavos, textoDeCentavos } from "../formato";
import { enderecoDe } from "../rotas";
import { Dica } from "../componentes/Dica";

export type ItemApoio = {
  id: number; nome: string; fornecedor_id: number | null; fornecedor: string | null;
  custo_centavos: number; data_cotacao: string; produtos: number; kits: number;
};
type FornecedorOpcao = { id: number; nome: string };
type DadosItem = { nome: string; fornecedor_id: number | null; custo: string; data: string };

export function ItensApoio() {
  const [itens, setItens] = useState<ItemApoio[] | null>(null);
  const [fornecedores, setFornecedores] = useState<FornecedorOpcao[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  // null: gaveta fechada; "novo": cadastro; item: edição.
  const [editando, setEditando] = useState<ItemApoio | "novo" | null>(null);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  const carregar = useCallback(() => pedir<{ itens: ItemApoio[]; fornecedores: FornecedorOpcao[] }>("/apoio").then(
    (r) => { setItens(r.itens); setFornecedores(r.fornecedores); setErro(null); },
    (e) => setErro(mensagemDeErro(e)),
  ), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!itens) return <p className="legenda">Carregando itens de apoio…</p>;

  const item = editando === "novo" ? null : editando;
  return (
    <>
      <div className="cabecalho-acoes">
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado} onClick={() => setEditando("novo")}>
          Cadastrar item
        </button>
      </div>
      <Caixa titulo="Embalagens e outros itens de apoio">
        <Tabela titulo="Itens de apoio" linhas={itens} chaveLinha={(i) => i.id} aoClicar={(i) => setEditando(i)}
          vazio='Nenhum item cadastrado. Use "Cadastrar item" para começar.' colunas={[
            { chave: "nome", titulo: "Item", mostrar: (i) => i.nome, ordenar: (i) => i.nome },
            { chave: "fornecedor", titulo: "Fornecedor", mostrar: (i) => i.fornecedor ?? "—", ordenar: (i) => i.fornecedor },
            { chave: "custo", titulo: "Custo unitário", alinhar: "direita", mostrar: (i) => reaisDeCentavos(i.custo_centavos), ordenar: (i) => i.custo_centavos },
            { chave: "data", titulo: "Data da cotação", mostrar: (i) => dataBr(i.data_cotacao), ordenar: (i) => i.data_cotacao },
            { chave: "uso", titulo: "Usado em", mostrar: (i) => `${i.produtos} produto(s), ${i.kits} kit(s)`, ordenar: (i) => i.produtos + i.kits },
          ]} />
        <p className="legenda">
          Indique os itens de cada produto na ficha dele, em <a href={enderecoDe("produtos")}>Produtos e SKUs</a>, e os de
          cada kit em <a href={enderecoDe("kits")}>Kits</a>. A soma substitui a embalagem padrão da configuração no cálculo
          de margem. Um kit usa só os próprios itens, não os dos componentes.
        </p>
      </Caixa>

      <Gaveta aberta={editando !== null} titulo={item ? item.nome : "Cadastrar item de apoio"} aoFechar={() => setEditando(null)}>
        {editando !== null && (
          <div className="pilha">
            <FormularioItem key={item?.id ?? "novo"} item={item} fornecedores={fornecedores} ocupado={gravacao.ocupado}
              aoEnviar={(dados) => gravacao.executar(async () => {
                await pedir(item ? `/apoio/${item.id}` : "/apoio", { metodo: item ? "PUT" : "POST", corpo: dados });
                notificar(item ? "Item de apoio salvo. As margens já usam o custo novo." : "Item de apoio cadastrado.");
                setEditando(null);
                await carregar();
              })} />
            {item && (
              <BotaoExcluir rotulo="Excluir item" pergunta={`Excluir ${item.nome}?`} ocupado={gravacao.ocupado}
                aoConfirmar={() => gravacao.executar(async () => {
                  await pedir(`/apoio/${item.id}?${new URLSearchParams({ nome: item.nome })}`, { metodo: "DELETE" });
                  notificar(`${item.nome} excluído.`);
                  setEditando(null);
                  await carregar();
                })} />
            )}
          </div>
        )}
      </Gaveta>
    </>
  );
}

function FormularioItem({ item, fornecedores, ocupado, aoEnviar }: {
  item: ItemApoio | null;
  fornecedores: FornecedorOpcao[];
  ocupado: boolean;
  aoEnviar: (dados: DadosItem) => Promise<unknown>;
}) {
  const [nome, setNome] = useState(item?.nome ?? "");
  const [fornecedor, setFornecedor] = useState(item?.fornecedor_id ? String(item.fornecedor_id) : "");
  const [custo, setCusto] = useState(item ? textoDeCentavos(item.custo_centavos) : "");
  const [data, setData] = useState(item?.data_cotacao ?? hojeIso());
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await aoEnviar({ nome, fornecedor_id: fornecedor ? Number(fornecedor) : null, custo, data });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div className="campos-2">
        <label><span className="rotulo">Nome do item<Dica de="Nome do item" /></span><input required value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Caixa P, sacola kraft…" /></label>
        <label><span className="rotulo">Fornecedor (opcional)<Dica de="Fornecedor (opcional)" /></span>
          <select value={fornecedor} onChange={(e) => setFornecedor(e.target.value)}>
            <option value="">Sem fornecedor</option>
            {fornecedores.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
          </select>
        </label>
        <label><span className="rotulo">Custo unitário (R$)<Dica de="Custo unitário (R$)" /></span><input required inputMode="decimal" value={custo} onChange={(e) => setCusto(e.target.value)} /></label>
        <label><span className="rotulo">Data da cotação<Dica de="Data da cotação" /></span><input type="date" required max={hojeIso()} value={data} onChange={(e) => setData(e.target.value)} /></label>
      </div>
      <p className="legenda">Ao mudar o custo, todos os produtos e kits que usam o item passam a usar o valor novo.</p>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar item"}</button></div>
    </form>
  );
}

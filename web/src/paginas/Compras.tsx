// Decisão de compra: orçamento, reserva e os seis critérios de cada produto do primeiro lote.
// Só planeja e verifica critérios; não faz compras nem movimenta dinheiro. Critérios, valores,
// margens e o limite de 20% para produto não validado vêm prontos de GET /api/compras.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Indicador, Painel as Caixa, Selo, SelosCriterios } from "../componentes/basicos";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { dataBr, percentual, reais, reaisDeCentavos, textoDeCentavos } from "../formato";
import { enderecoDe } from "../rotas";

type Item = {
  produto_id: number; produto: string; pronto: boolean; validado: number; justificativa_validacao: string;
  acima_vinte: boolean; quantidade: number; valor_centavos: number; fornecedor: string; codigo: string;
  data_cotacao: string; sku_fornecedor_id: number; preco_venda_centavos: number;
  demanda_confirmada: number; justificativa_demanda: string; concorrencia_confirmada: number; justificativa_concorrencia: string;
  criterios: { nome: string; cumprido: boolean }[]; percentual_orcamento: string; contribuicao: string; margem_pct: string;
};
type ProdutoOpcao = { id: number; nome: string; validado: number; justificativa_validacao: string };
export type Lote = {
  orcamento: { total_centavos: number; reserva_centavos: number };
  campos_orcamento: { total: string; reserva: string };
  comprometido_centavos: number;
  disponivel_centavos: number;
  excede_disponivel: boolean;
  uso_pct: number;
  itens: Item[];
  produtos: ProdutoOpcao[];
};
type Cotacao = {
  id: number; fornecedor: string; codigo: string; data_cotacao: string; custo_centavos: number;
  quantidade_minima: number; preco_venda_centavos: number | null;
};
type Edicao = { tipo: "orcamento" } | { tipo: "plano"; produtoId?: number };

export function Compras() {
  const [lote, setLote] = useState<Lote | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [edicao, setEdicao] = useState<Edicao | null>(null);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  const carregar = useCallback(() => pedir<Lote>("/compras").then(
    (l) => { setLote(l); setErro(null); }, (e) => setErro(mensagemDeErro(e))), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!lote) return <p className="legenda">Carregando o plano de compra…</p>;

  // Grava, fecha a gaveta, recarrega o lote e só então libera os botões.
  const gravar = (acao: () => Promise<unknown>, sucesso: string) => gravacao.executar(async () => {
    await acao();
    setEdicao(null);
    notificar(sucesso);
    await carregar();
  });

  const prontos = lote.itens.filter((i) => i.pronto).length;
  const itemEditado = edicao?.tipo === "plano" && edicao.produtoId !== undefined
    ? lote.itens.find((i) => i.produto_id === edicao.produtoId) : undefined;

  return (
    <>
      <Aviso>Esta tela só planeja o lote e verifica critérios. Não faz compras nem movimenta dinheiro.</Aviso>

      <Caixa titulo="Orçamento do lote" acoes={
        <button type="button" className="botao" disabled={gravacao.ocupado} onClick={() => setEdicao({ tipo: "orcamento" })}>
          Configurar orçamento e reserva
        </button>}>
        <div className="grade-4">
          <Indicador rotulo="Orçamento" valor={reaisDeCentavos(lote.orcamento.total_centavos)} />
          <Indicador rotulo="Reserva de reposição" valor={reaisDeCentavos(lote.orcamento.reserva_centavos)} />
          <Indicador rotulo="Comprometido" valor={reaisDeCentavos(lote.comprometido_centavos)} detalhe="Soma de todos os itens do plano, prontos ou pendentes." />
          <Indicador rotulo="Disponível após reserva" valor={reaisDeCentavos(lote.disponivel_centavos)}
            tom={lote.disponivel_centavos < 0 ? "vermelho" : undefined} />
        </div>
        <div className="resultado">
          <div className="progresso-rotulo">{lote.uso_pct}% do valor disponível para compra (orçamento menos reserva)</div>
          <progress className="progresso" max={100} value={lote.uso_pct} aria-label="Uso do valor disponível para compra" />
        </div>
        {lote.excede_disponivel && <Aviso tipo="atencao">O total planejado ultrapassa o orçamento após a reserva de reposição.</Aviso>}
      </Caixa>

      <Caixa titulo={`Produtos no plano · ${prontos} de ${lote.itens.length} prontos`} acoes={
        <button type="button" className="botao botao-principal" disabled={gravacao.ocupado || !lote.produtos.length}
          onClick={() => setEdicao({ tipo: "plano" })}>
          Adicionar produto ao plano
        </button>}>
        {!lote.produtos.length && (
          <Aviso>Cadastre produtos e cotações em <a href={enderecoDe("produtos")}>Produtos e SKUs</a> antes de planejar o lote.</Aviso>
        )}
        {lote.produtos.length > 0 && !lote.itens.length && <p className="vazio">Nenhum produto no plano ainda.</p>}
        <div className="pilha">
          {lote.itens.map((item) => (
            <CartaoItem key={item.produto_id} item={item} ocupado={gravacao.ocupado}
              aoEditar={() => setEdicao({ tipo: "plano", produtoId: item.produto_id })}
              aoRetirar={() => gravar(() => pedir(`/compras/plano/${item.produto_id}`, { metodo: "DELETE" }), "Produto retirado do plano.")
                .catch((e) => notificar(mensagemDeErro(e), "erro"))} />
          ))}
        </div>
        <p className="legenda">
          Pronto exige os seis critérios: Fornecedor, Produto, Margem, Demanda, Concorrência e Estoque. Produto não
          validado não pode passar de 20% do orçamento. A decisão de compra é de vocês.
        </p>
      </Caixa>

      <Gaveta aberta={edicao?.tipo === "orcamento"} titulo="Configurar orçamento e reserva" aoFechar={() => setEdicao(null)}>
        <FormularioOrcamento campos={lote.campos_orcamento} ocupado={gravacao.ocupado}
          aoEnviar={(dados) => gravar(() => pedir("/compras/orcamento", { metodo: "PUT", corpo: dados }), "Orçamento salvo.")} />
      </Gaveta>

      <Gaveta aberta={edicao?.tipo === "plano"} larga
        titulo={itemEditado ? `Editar no plano: ${itemEditado.produto}` : "Adicionar produto ao plano"} aoFechar={() => setEdicao(null)}>
        {edicao?.tipo === "plano" && (
          <FormularioPlano produtos={lote.produtos} itens={lote.itens} produtoFixo={edicao.produtoId} ocupado={gravacao.ocupado}
            aoEnviar={(produtoId, dados) => gravar(() => pedir(`/compras/plano/${produtoId}`, { metodo: "PUT", corpo: dados }),
              "Planejamento salvo e critérios recalculados.")} />
        )}
      </Gaveta>
    </>
  );
}

function CartaoItem({ item, ocupado, aoEditar, aoRetirar }: { item: Item; ocupado: boolean; aoEditar: () => void; aoRetirar: () => void }) {
  return (
    <article className="cartao" aria-label={item.produto}>
      <header className="cartao-topo">
        <div>
          <strong>{item.produto}</strong>{" "}
          <Selo tom={item.pronto ? "verde" : "laranja"}>{item.pronto ? "Pronto" : "Pendente"}</Selo>
          {!item.validado && <> <Selo tom="amarelo">Não validado</Selo></>}
        </div>
        <div className="cartao-acoes">
          <button type="button" className="botao" disabled={ocupado} onClick={aoEditar}>Editar</button>
          <button type="button" className="botao" disabled={ocupado} onClick={aoRetirar}>Retirar do plano</button>
        </div>
      </header>
      <dl className="fatos">
        <div><dt>Quantidade</dt><dd>{item.quantidade} unidades</dd></div>
        <div><dt>Valor</dt><dd>{reaisDeCentavos(item.valor_centavos)} · {percentual(item.percentual_orcamento)} do orçamento</dd></div>
        <div><dt>Contribuição por venda</dt><dd>{reais(item.contribuicao)}</dd></div>
        <div><dt>Margem</dt><dd>{percentual(item.margem_pct)}</dd></div>
      </dl>
      <p className="legenda">{item.fornecedor} · {item.codigo} · cotação de {dataBr(item.data_cotacao)}</p>
      <SelosCriterios criterios={Object.fromEntries(item.criterios.map((c) => [c.nome, c.cumprido]))} />
      {item.acima_vinte && <Aviso tipo="atencao">Produto ainda não validado compromete mais de 20% do orçamento.</Aviso>}
    </article>
  );
}

function FormularioOrcamento({ campos, ocupado, aoEnviar }: {
  campos: Lote["campos_orcamento"];
  ocupado: boolean;
  aoEnviar: (dados: { total: string; reserva: string }) => Promise<unknown>;
}) {
  const [total, setTotal] = useState(campos.total);
  const [reserva, setReserva] = useState(campos.reserva);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try { await aoEnviar({ total, reserva }); } catch (e) { setErro(mensagemDeErro(e)); }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label>Orçamento do lote (R$)<input required inputMode="decimal" value={total} onChange={(e) => setTotal(e.target.value)} /></label>
      <label>Reserva de reposição (R$)<input required inputMode="decimal" value={reserva} onChange={(e) => setReserva(e.target.value)} /></label>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar orçamento"}</button></div>
    </form>
  );
}

type DadosPlano = {
  cotacao_id: number; quantidade: number; preco_venda: string;
  demanda: boolean; justificativa_demanda: string; concorrencia: boolean; justificativa_concorrencia: string;
  validado: boolean; justificativa_validacao: string;
};

function FormularioPlano({ produtos, itens, produtoFixo, ocupado, aoEnviar }: {
  produtos: ProdutoOpcao[];
  itens: Item[];
  produtoFixo?: number;
  ocupado: boolean;
  aoEnviar: (produtoId: number, dados: DadosPlano) => Promise<unknown>;
}) {
  // Ao adicionar, começa por um produto que ainda não está no plano.
  const inicial = produtoFixo ?? (produtos.find((p) => !itens.some((i) => i.produto_id === p.id)) ?? produtos[0]).id;
  const [produtoId, setProdutoId] = useState(inicial);
  return (
    <div className="pilha">
      {produtoFixo === undefined && (
        <label className="formulario">Produto do plano
          <select value={produtoId} onChange={(e) => setProdutoId(Number(e.target.value))}>
            {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}{itens.some((i) => i.produto_id === p.id) ? " · já no plano" : ""}</option>)}
          </select>
        </label>
      )}
      <CamposPlano key={produtoId} produto={produtos.find((p) => p.id === produtoId)!}
        item={itens.find((i) => i.produto_id === produtoId)} ocupado={ocupado}
        aoEnviar={(dados) => aoEnviar(produtoId, dados)} />
    </div>
  );
}

function CamposPlano({ produto, item, ocupado, aoEnviar }: {
  produto: ProdutoOpcao;
  item?: Item;
  ocupado: boolean;
  aoEnviar: (dados: DadosPlano) => Promise<unknown>;
}) {
  const [cotacoes, setCotacoes] = useState<Cotacao[] | null>(null);
  const [cotacaoId, setCotacaoId] = useState<number | null>(null);
  const [quantidade, setQuantidade] = useState(item ? String(item.quantidade) : "");
  const [preco, setPreco] = useState(item ? textoDeCentavos(item.preco_venda_centavos) : "");
  const [demanda, setDemanda] = useState(!!item?.demanda_confirmada);
  const [textoDemanda, setTextoDemanda] = useState(item?.justificativa_demanda ?? "");
  const [concorrencia, setConcorrencia] = useState(!!item?.concorrencia_confirmada);
  const [textoConcorrencia, setTextoConcorrencia] = useState(item?.justificativa_concorrencia ?? "");
  const [validado, setValidado] = useState(!!produto.validado);
  const [textoValidacao, setTextoValidacao] = useState(produto.justificativa_validacao ?? "");
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let valido = true;
    pedir<Cotacao[]>(`/pesquisa/cotacoes?produto_id=${produto.id}`).then((lista) => {
      // Resposta de uma consulta já substituída não entra no formulário.
      if (!valido) return;
      setCotacoes(lista);
      const escolhida = lista.find((c) => c.id === item?.sku_fornecedor_id) ?? lista[0];
      if (!escolhida) return;
      setCotacaoId(escolhida.id);
      // Sem plano anterior, começa pela quantidade mínima e pelo preço conservador da cotação.
      if (!item) {
        setQuantidade(String(escolhida.quantidade_minima));
        if (escolhida.preco_venda_centavos !== null) setPreco(textoDeCentavos(escolhida.preco_venda_centavos));
      }
    }, (e) => { if (valido) setErro(mensagemDeErro(e)); });
    return () => { valido = false; };
  }, [produto.id, item]);

  if (cotacoes === null) return erro ? <Aviso tipo="erro">{erro}</Aviso> : <p className="legenda">Carregando cotações…</p>;
  if (!cotacoes.length) {
    return <Aviso>Este produto precisa de uma cotação de fornecedor. Registre em <a href={enderecoDe("produtos", { ficha: String(produto.id) })}>Produtos e SKUs</a>.</Aviso>;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    // Quantidade é um inteiro de unidades, não dinheiro; o servidor confere de novo.
    if (!/^\d{1,9}$/.test(quantidade.trim()) || Number(quantidade) < 1) {
      return setErro("A quantidade deve ser um inteiro positivo.");
    }
    try {
      await aoEnviar({
        cotacao_id: cotacaoId!, quantidade: Number.parseInt(quantidade, 10), preco_venda: preco,
        demanda, justificativa_demanda: textoDemanda, concorrencia, justificativa_concorrencia: textoConcorrencia,
        validado, justificativa_validacao: textoValidacao,
      });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <label>Cotação para o plano
        <select value={cotacaoId ?? ""} onChange={(e) => setCotacaoId(Number(e.target.value))}>
          {cotacoes.map((c) => (
            <option key={c.id} value={c.id}>{c.fornecedor} · {c.codigo} · {dataBr(c.data_cotacao)} · {reaisDeCentavos(c.custo_centavos)}</option>
          ))}
        </select>
      </label>
      <div className="campos-2">
        <label>Quantidade planejada<input required inputMode="numeric" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} /></label>
        <label>Preço conservador de venda no plano (R$)<input required inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} /></label>
      </div>
      <fieldset className="grupo">
        <legend>Confirmações manuais</legend>
        <p className="legenda">Cada confirmação exige uma justificativa com a evidência que vocês encontraram.</p>
        <div className="campos-3">
          <div className="pilha">
            <label className="tarefa"><input type="checkbox" checked={demanda} onChange={(e) => setDemanda(e.target.checked)} />Demanda confirmada</label>
            <label>Justificativa de demanda<textarea rows={3} value={textoDemanda} onChange={(e) => setTextoDemanda(e.target.value)} /></label>
          </div>
          <div className="pilha">
            <label className="tarefa"><input type="checkbox" checked={concorrencia} onChange={(e) => setConcorrencia(e.target.checked)} />Concorrência confirmada</label>
            <label>Justificativa de concorrência<textarea rows={3} value={textoConcorrencia} onChange={(e) => setTextoConcorrencia(e.target.value)} /></label>
          </div>
          <div className="pilha">
            <label className="tarefa"><input type="checkbox" checked={validado} onChange={(e) => setValidado(e.target.checked)} />Produto validado</label>
            <label>Justificativa da validação<textarea rows={3} value={textoValidacao} onChange={(e) => setTextoValidacao(e.target.value)} /></label>
          </div>
        </div>
      </fieldset>
      <div><button type="submit" className="botao botao-principal" disabled={ocupado || cotacaoId === null}>{ocupado ? "Salvando…" : "Salvar planejamento"}</button></div>
    </form>
  );
}

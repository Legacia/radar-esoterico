import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ItensApoio, type ItemApoio } from "../src/paginas/ItensApoio";
import { EmbalagemApoio, type Apoio } from "../src/componentes/EmbalagemApoio";
import { Kits } from "../src/paginas/Kits";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const ITENS: ItemApoio[] = [
  { id: 4, nome: "Caixa fictícia M", fornecedor_id: 2, fornecedor: "Fornecedor fictício", custo_centavos: 180, data_cotacao: "2026-10-20", produtos: 1, kits: 0 },
  { id: 5, nome: "Sacola fictícia", fornecedor_id: null, fornecedor: null, custo_centavos: 135, data_cotacao: "2026-10-21", produtos: 0, kits: 0 },
];

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(respostas: (c: Chamada) => unknown) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const c = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(c);
    return new Response(JSON.stringify(c.metodo !== "GET" ? { id: 9, ok: true } : respostas(c)), { status: 200 });
  });
  return chamadas;
}

const comNotificacoes = (filho: ReactElement) => render(<ProvedorNotificacoes>{filho}</ProvedorNotificacoes>);

describe("Itens de apoio", () => {
  it("lista os itens com custo, fornecedor e uso, e cadastra um novo", async () => {
    const chamadas = simular(() => ({ itens: ITENS, fornecedores: [{ id: 2, nome: "Fornecedor fictício" }] }));
    comNotificacoes(<ItensApoio />);
    const linha = (await screen.findByRole("cell", { name: "Caixa fictícia M" })).closest("tr")!;
    expect(linha).toHaveTextContent("R$ 1,80");
    expect(linha).toHaveTextContent("20/10/2026");
    expect(linha).toHaveTextContent("1 produto(s), 0 kit(s)");
    await userEvent.click(screen.getByRole("button", { name: "Cadastrar item" }));
    await userEvent.type(screen.getByLabelText("Nome do item"), "Papel de seda fictício");
    await userEvent.type(screen.getByLabelText("Custo unitário (R$)"), "0,25");
    await userEvent.selectOptions(screen.getByLabelText("Fornecedor (opcional)"), "2");
    await userEvent.click(screen.getByRole("button", { name: "Salvar item" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "POST")).toBe(true));
    const post = chamadas.find((c) => c.metodo === "POST")!;
    expect(post.caminho).toBe("/api/apoio");
    expect(post.corpo).toMatchObject({ nome: "Papel de seda fictício", custo: "0,25", fornecedor_id: 2 });
  });

  it("edita e exclui mandando o nome confirmado", async () => {
    const chamadas = simular(() => ({ itens: ITENS, fornecedores: [] }));
    comNotificacoes(<ItensApoio />);
    await userEvent.click(await screen.findByRole("cell", { name: "Sacola fictícia" }));
    expect(screen.getByLabelText("Custo unitário (R$)")).toHaveValue("1,35");
    await userEvent.click(screen.getByRole("button", { name: "Excluir item" }));
    await userEvent.click(screen.getByRole("button", { name: "Sim, excluir" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "DELETE")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "DELETE")!.caminho).toBe("/api/apoio/5?nome=Sacola+fict%C3%ADcia");
  });
});

describe("Embalagem de um produto ou kit", () => {
  const APOIO: Apoio = { itens: [{ id: 4, nome: "Caixa fictícia M", fornecedor: null, custo_centavos: 180, data_cotacao: "2026-10-20", quantidade: 2, subtotal_centavos: 360 }], embalagem_centavos: 360 };

  it("mostra a soma da API e indica um item com a quantidade", async () => {
    const chamadas = simular(() => ({ itens: ITENS, fornecedores: [] }));
    const gravar = vi.fn((acao: () => Promise<unknown>) => acao());
    render(<EmbalagemApoio apoio={APOIO} padrao="2.50" caminho="/produtos/3/apoio" quem="do produto" ocupado={false} gravar={gravar} />);
    expect(screen.getByText("Embalagem usada no cálculo de margem:", { exact: false })).toHaveTextContent("R$ 3,60");
    expect(screen.getByText("Soma dos itens do produto")).toBeInTheDocument();
    await userEvent.selectOptions(await screen.findByLabelText("Item de apoio"), "5");
    await userEvent.clear(screen.getByLabelText("Quantidade por unidade vendida"));
    await userEvent.type(screen.getByLabelText("Quantidade por unidade vendida"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Indicar item" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({ caminho: "/api/produtos/3/apoio/5", corpo: { quantidade: 3 } });
    await userEvent.click(screen.getByRole("button", { name: "Retirar Caixa fictícia M" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "DELETE")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "DELETE")!.caminho).toBe("/api/produtos/3/apoio/4");
  });

  it("sem itens mostra a embalagem padrão e recusa quantidade inválida", async () => {
    const chamadas = simular(() => ({ itens: ITENS, fornecedores: [] }));
    render(<EmbalagemApoio apoio={{ itens: [], embalagem_centavos: null }} padrao="2.50" caminho="/kits/1/apoio" quem="do kit"
      ocupado={false} gravar={(acao) => acao()} />);
    expect(screen.getByText("Padrão da configuração")).toBeInTheDocument();
    await screen.findByLabelText("Item de apoio");
    await userEvent.clear(screen.getByLabelText("Quantidade por unidade vendida"));
    await userEvent.type(screen.getByLabelText("Quantidade por unidade vendida"), "1,5");
    await userEvent.click(screen.getByRole("button", { name: "Indicar item" }));
    expect(await screen.findByText("A quantidade deve ser um inteiro de 1 a 1000.")).toBeInTheDocument();
    expect(chamadas.some((c) => c.metodo === "PUT")).toBe(false);
  });
});

describe("Margem do kit", () => {
  const KIT = {
    id: 1, nome: "Kit fictício", quantidade_planejada: 0, custo_unitario: "20", custo_lote: null, preco_venda_centavos: 5990,
    componentes: [], apoio: { itens: [], embalagem_centavos: null },
    margem: { embalagem: "2.50", embalagem_propria: false, contribuicao: "14.33", margem_pct: "0.2392320534",
              preco_minimo: "55.56", aviso_preco_minimo: null },
  };

  it("mostra a margem da API e manda o preço conservador no plano", async () => {
    const chamadas = simular((c) => c.caminho === "/api/kits" ? { kits: [KIT], produtos: [], necessidade: [] }
      : c.caminho === "/api/apoio" ? { itens: [], fornecedores: [] } : KIT);
    window.location.hash = "#/kits";
    comNotificacoes(<Kits />);
    const margem = await screen.findByRole("region", { name: "Margem do kit" });
    expect(within(margem).getByText("R$ 14,33")).toBeInTheDocument();
    expect(within(margem).getByText("Margem de 23,9%")).toBeInTheDocument();
    expect(within(margem).getByText("R$ 55,56")).toBeInTheDocument();
    const preco = screen.getByLabelText("Preço conservador de venda do kit (R$), opcional");
    expect(preco).toHaveValue("59,90");
    await userEvent.clear(preco);
    await userEvent.type(preco, "64,90");
    await userEvent.click(screen.getByRole("button", { name: "Salvar plano do kit" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({
      caminho: "/api/kits/1", corpo: { nome: "Kit fictício", quantidade_planejada: 0, preco_venda: "64,90" } });
  });
});

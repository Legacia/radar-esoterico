import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Compras, type Lote } from "../src/paginas/Compras";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const CRITERIOS = ["Fornecedor", "Produto", "Margem", "Demanda", "Concorrência", "Estoque"];
const ITEM = {
  produto_id: 1, produto: "Kit fictício", pronto: false, validado: 0, justificativa_validacao: "", acima_vinte: true,
  quantidade: 11, valor_centavos: 22000, fornecedor: "Fornecedor fictício", codigo: "KIT", data_cotacao: "2026-10-20",
  sku_fornecedor_id: 8, preco_venda_centavos: 5990, demanda_confirmada: 1, justificativa_demanda: "Busca fictícia",
  concorrencia_confirmada: 0, justificativa_concorrencia: "",
  criterios: CRITERIOS.map((nome) => ({ nome, cumprido: !["Concorrência", "Estoque"].includes(nome) })),
  percentual_orcamento: "0.22", contribuicao: "14.33", margem_pct: "0.2392320534223706176961602671",
};
const LOTE: Lote = {
  orcamento: { total_centavos: 100000, reserva_centavos: 20000 },
  campos_orcamento: { total: "1000,00", reserva: "200,00" },
  comprometido_centavos: 22000, disponivel_centavos: 58000, excede_disponivel: false, uso_pct: 27,
  itens: [ITEM],
  produtos: [{ id: 1, nome: "Kit fictício", validado: 0, justificativa_validacao: "" },
             { id: 2, nome: "Cristal fictício", validado: 1, justificativa_validacao: "Venda teste fictícia" }],
};
const COTACOES: Record<string, unknown[]> = {
  "1": [{ id: 8, fornecedor: "Fornecedor fictício", codigo: "KIT", data_cotacao: "2026-10-20", custo_centavos: 2000, quantidade_minima: 5, preco_venda_centavos: 5990 }],
  "2": [{ id: 9, fornecedor: "Fornecedor fictício", codigo: "CRI", data_cotacao: "2026-10-21", custo_centavos: 900, quantidade_minima: 10, preco_venda_centavos: 1800 }],
};

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(lote: Lote = LOTE, falhar?: (c: Chamada) => string | undefined) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const c = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(c);
    const erro = falhar?.(c);
    if (erro) return new Response(JSON.stringify({ detail: erro }), { status: 400 });
    const corpo = c.metodo !== "GET" ? { ok: true }
      : c.caminho === "/api/compras" ? lote
      : COTACOES[c.caminho.split("=").pop()!];
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const mostrar = () => render(<ProvedorNotificacoes><Compras /></ProvedorNotificacoes>);

describe("Decisão de compra", () => {
  it("mostra orçamento e critérios como a API calculou", async () => {
    simular();
    mostrar();
    expect(await screen.findByText(/Não faz compras nem movimenta dinheiro/)).toBeInTheDocument();
    expect(screen.getByText("Comprometido").nextSibling).toHaveTextContent("R$ 220,00");
    expect(screen.getByText("Disponível após reserva").nextSibling).toHaveTextContent("R$ 580,00");
    expect(screen.getByText(/27% do valor disponível/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Produtos no plano · 0 de 1 prontos" })).toBeInTheDocument();
    const cartao = screen.getByRole("article", { name: "Kit fictício" });
    expect(cartao).toHaveTextContent("Pendente");
    expect(cartao).toHaveTextContent("Não validado");
    expect(cartao).toHaveTextContent("R$ 220,00 · 22,0% do orçamento");
    expect(cartao).toHaveTextContent("R$ 14,33");
    expect(cartao).toHaveTextContent("23,9%");
    expect(within(cartao).getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "✓ Fornecedor: cumprido", "✓ Produto: cumprido", "✓ Margem: cumprido", "✓ Demanda: cumprido",
      "○ Concorrência: pendente", "○ Estoque: pendente"]);
    expect(within(cartao).getByText(/compromete mais de 20% do orçamento/)).toBeInTheDocument();
  });

  it("orçamento estourado mostra aviso", async () => {
    simular({ ...LOTE, excede_disponivel: true, disponivel_centavos: -5000, uso_pct: 100 });
    mostrar();
    expect(await screen.findByText(/ultrapassa o orçamento após a reserva/)).toBeInTheDocument();
    expect(screen.getByText("Disponível após reserva").nextSibling).toHaveTextContent("-R$ 50,00");
  });

  it("adicionar começa por produto fora do plano com quantidade mínima e preço da cotação", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Adicionar produto ao plano" }));
    const gaveta = screen.getByRole("dialog", { name: "Adicionar produto ao plano" });
    expect(within(gaveta).getByLabelText("Produto do plano")).toHaveValue("2");
    await waitFor(() => expect(within(gaveta).getByLabelText("Quantidade planejada")).toHaveValue("10"));
    expect(within(gaveta).getByLabelText("Preço conservador de venda no plano (R$)")).toHaveValue("18,00");
    expect(within(gaveta).getByLabelText("Produto validado")).toBeChecked();
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar planejamento" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({ caminho: "/api/compras/plano/2", corpo: {
      cotacao_id: 9, quantidade: 10, preco_venda: "18,00", demanda: false, concorrencia: false,
      validado: true, justificativa_validacao: "Venda teste fictícia" } });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("editar traz o plano salvo e erro da regra fica na gaveta", async () => {
    simular(LOTE, (c) => (c.metodo === "PUT" ? "Informe a justificativa de concorrência." : undefined));
    mostrar();
    const cartao = await screen.findByRole("article", { name: "Kit fictício" });
    await userEvent.click(within(cartao).getByRole("button", { name: "Editar" }));
    const gaveta = screen.getByRole("dialog", { name: "Editar no plano: Kit fictício" });
    await waitFor(() => expect(within(gaveta).getByLabelText("Cotação para o plano")).toHaveValue("8"));
    expect(within(gaveta).queryByLabelText("Produto do plano")).toBeNull();
    expect(within(gaveta).getByLabelText("Quantidade planejada")).toHaveValue("11");
    expect(within(gaveta).getByLabelText("Preço conservador de venda no plano (R$)")).toHaveValue("59,90");
    expect(within(gaveta).getByLabelText("Justificativa de demanda")).toHaveValue("Busca fictícia");
    await userEvent.click(within(gaveta).getByLabelText("Concorrência confirmada"));
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar planejamento" }));
    expect(await within(gaveta).findByRole("alert")).toHaveTextContent("Informe a justificativa de concorrência.");
    expect(within(gaveta).getByLabelText("Concorrência confirmada")).toBeChecked();
  });

  it("quantidade que não é inteiro é recusada antes de enviar", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(within(await screen.findByRole("article", { name: "Kit fictício" })).getByRole("button", { name: "Editar" }));
    const gaveta = screen.getByRole("dialog", { name: "Editar no plano: Kit fictício" });
    await waitFor(() => expect(within(gaveta).getByLabelText("Cotação para o plano")).toHaveValue("8"));
    await userEvent.clear(within(gaveta).getByLabelText("Quantidade planejada"));
    await userEvent.type(within(gaveta).getByLabelText("Quantidade planejada"), "2,5");
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar planejamento" }));
    expect(await within(gaveta).findByRole("alert")).toHaveTextContent("inteiro positivo");
    expect(chamadas.some((c) => c.metodo === "PUT")).toBe(false);
  });

  it("orçamento salvo uma vez só, mesmo com cliques repetidos", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Configurar orçamento e reserva" }));
    const gaveta = screen.getByRole("dialog", { name: "Configurar orçamento e reserva" });
    expect(within(gaveta).getByLabelText("Orçamento do lote (R$)")).toHaveValue("1000,00");
    await userEvent.clear(within(gaveta).getByLabelText("Reserva de reposição (R$)"));
    await userEvent.type(within(gaveta).getByLabelText("Reserva de reposição (R$)"), "150,00");
    const formulario = within(gaveta).getByRole("button", { name: "Salvar orçamento" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    expect(await screen.findByText("Orçamento salvo.")).toBeInTheDocument();
    const puts = chamadas.filter((c) => c.metodo === "PUT");
    expect(puts).toHaveLength(1);
    expect(puts[0]).toMatchObject({ caminho: "/api/compras/orcamento", corpo: { total: "1000,00", reserva: "150,00" } });
  });

  it("retirar do plano trava os botões até recarregar", async () => {
    let liberar!: () => void;
    const chamadas: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      chamadas.push(`${init?.method ?? "GET"} ${String(entrada)}`);
      if (init?.method === "DELETE") await new Promise<void>((r) => { liberar = r; });
      return new Response(JSON.stringify(init?.method === "DELETE" ? { ok: true } : LOTE), { status: 200 });
    });
    mostrar();
    const cartao = await screen.findByRole("article", { name: "Kit fictício" });
    await userEvent.click(within(cartao).getByRole("button", { name: "Retirar do plano" }));
    expect(within(cartao).getByRole("button", { name: "Editar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Adicionar produto ao plano" })).toBeDisabled();
    liberar();
    await screen.findByText("Produto retirado do plano.");
    expect(chamadas).toContain("DELETE /api/compras/plano/1");
  });
});

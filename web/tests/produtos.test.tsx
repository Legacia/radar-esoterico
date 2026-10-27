import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Produtos, type Produto } from "../src/paginas/Produtos";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";
import { hojeIso } from "../src/formato";

const KIT: Produto = {
  id: 1, nome: "Kit fictício de incensos", familia: "Incensos", status: "Candidato",
  especificacoes_conferidas: 1, procedencia_conferida: 1, qualidade_conferida: 0, validado: 0, estoque_atual: 4,
};
const CATALOGO = {
  produtos: [KIT, { ...KIT, id: 2, nome: "Cristal fictício", familia: null, especificacoes_conferidas: 0, procedencia_conferida: 0, validado: 1, estoque_atual: 0 }],
  fornecedores: [{ id: 3, nome: "Fornecedor fictício Alfa" }, { id: 4, nome: "Fornecedor fictício Beta" }],
};
const FICHA = {
  ...KIT, limite_cotacao_dias: 15,
  skus: [{
    id: 9, codigo: "KIT-01", produto_id: 1, produto: KIT.nome, fornecedor_id: 3, fornecedor: "Fornecedor fictício Alfa",
    custo_centavos: 2000, quantidade_minima: 10, data_cotacao: "2026-10-20", cotacao_antiga: false,
    preco_venda_centavos: 5990, contribuicao: "14.33", margem_pct: "0.2392320534223706176961602671",
    preco_minimo: "55.56", aviso_preco_minimo: null,
  }],
};

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(catalogo: unknown = CATALOGO) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const caminho = String(entrada);
    const metodo = init?.method ?? "GET";
    chamadas.push({ caminho, metodo, corpo: init?.body ? JSON.parse(String(init.body)) : undefined });
    const corpo = metodo !== "GET" ? { id: 1 }
      : caminho === "/api/produtos" ? catalogo
      : { ...FICHA, id: Number(caminho.split("/").pop()) };
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const mostrar = (hash = "#/produtos") => {
  window.location.hash = hash;
  return render(<ProvedorNotificacoes><Produtos /></ProvedorNotificacoes>);
};

describe("Produtos e SKUs", () => {
  it("lista o catálogo com conferências, validação e estoque", async () => {
    simular();
    mostrar();
    const linha = (await screen.findByRole("cell", { name: "Kit fictício de incensos" })).closest("tr")!;
    expect(linha).toHaveTextContent("Incensos");
    expect(linha).toHaveTextContent("2 de 3");
    expect(linha).toHaveTextContent("Não");
    expect(linha).toHaveTextContent("4");
    const cristal = screen.getByRole("cell", { name: "Cristal fictício" }).closest("tr")!;
    expect(cristal).toHaveTextContent("Não informada");
    expect(cristal).toHaveTextContent("Sim");
  });

  it("abre a ficha com as cotações calculadas pela API", async () => {
    simular();
    mostrar();
    await userEvent.click(await screen.findByRole("cell", { name: "Kit fictício de incensos" }));
    expect(window.location.hash).toBe("#/produtos?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Kit fictício de incensos" });
    expect(within(ficha).getByText("Qualidade").closest(".selo")).toHaveTextContent("Qualidade: pendente");
    const linha = within(ficha).getByRole("cell", { name: "KIT-01" }).closest("tr")!;
    expect(linha).toHaveTextContent("Fornecedor fictício Alfa");
    expect(linha).toHaveTextContent("R$ 14,33");
    expect(linha).toHaveTextContent("23,9%");
    expect(linha).toHaveTextContent("R$ 55,56");
  });

  it("registra cotação com o fornecedor escolhido, data ISO e preço opcional vazio", async () => {
    const chamadas = simular();
    mostrar("#/produtos?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Kit fictício de incensos" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Registrar cotação" }));
    await userEvent.selectOptions(within(ficha).getByLabelText("Fornecedor da cotação"), "Fornecedor fictício Beta");
    await userEvent.type(within(ficha).getByLabelText("Código no fornecedor"), "SUP-01");
    await userEvent.type(within(ficha).getByLabelText("Custo unitário (R$)"), "6,00");
    await userEvent.clear(within(ficha).getByLabelText("Quantidade mínima"));
    await userEvent.type(within(ficha).getByLabelText("Quantidade mínima"), "12");
    expect(within(ficha).getByLabelText("Data da cotação")).toHaveAttribute("max", hojeIso());
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar cotação" }));
    await waitFor(() => expect(chamadas.some((c) => c.caminho === "/api/produtos/1/cotacoes")).toBe(true));
    expect(chamadas.find((c) => c.caminho === "/api/produtos/1/cotacoes")!.corpo).toEqual({
      fornecedor_id: 4, codigo: "SUP-01", custo: "6,00", quantidade_minima: 12, data: hojeIso(), preco_venda: null });
    expect(await screen.findByText("Cotação registrada.")).toBeInTheDocument();
  });

  it("quantidade que não é inteiro é recusada antes de enviar", async () => {
    const chamadas = simular();
    mostrar("#/produtos?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Kit fictício de incensos" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Registrar cotação" }));
    await userEvent.type(within(ficha).getByLabelText("Código no fornecedor"), "X");
    await userEvent.type(within(ficha).getByLabelText("Custo unitário (R$)"), "1");
    await userEvent.clear(within(ficha).getByLabelText("Quantidade mínima"));
    await userEvent.type(within(ficha).getByLabelText("Quantidade mínima"), "2,5");
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar cotação" }));
    expect(await within(ficha).findByRole("alert")).toHaveTextContent("inteiro maior que zero");
    expect(chamadas.some((c) => c.metodo === "POST")).toBe(false);
  });

  it("sem fornecedores, orienta a cadastrar um", async () => {
    simular({ ...CATALOGO, fornecedores: [] });
    mostrar("#/produtos?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Kit fictício de incensos" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Registrar cotação" }));
    expect(within(ficha).getByRole("link", { name: "Fornecedores" })).toHaveAttribute("href", "#/fornecedores");
  });

  it("cadastra produto uma vez só, mesmo com cliques repetidos, e abre a ficha", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar produto" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar produto" });
    await userEvent.type(within(gaveta).getByLabelText("Nome do produto"), "Vela fictícia");
    await userEvent.click(within(gaveta).getByLabelText("Qualidade conferida pela Anna"));
    const formulario = within(gaveta).getByRole("button", { name: "Salvar produto" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    await waitFor(() => expect(window.location.hash).toBe("#/produtos?ficha=1"));
    const posts = chamadas.filter((c) => c.caminho === "/api/produtos" && c.metodo === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0].corpo).toEqual({ nome: "Vela fictícia", familia: "", status: "Candidato",
      especificacoes_conferidas: false, procedencia_conferida: false, qualidade_conferida: true });
  });

  it("erro da API na edição mantém o que foi digitado", async () => {
    simular();
    mostrar("#/produtos?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Kit fictício de incensos" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Editar produto e avaliação" }));
    await userEvent.clear(within(ficha).getByLabelText("Família"));
    await userEvent.type(within(ficha).getByLabelText("Família"), "Velas");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => (init?.method === "PUT"
      ? new Response(JSON.stringify({ detail: "Informe o status do produto." }), { status: 400 })
      : new Response(JSON.stringify(String(entrada) === "/api/produtos" ? CATALOGO : FICHA), { status: 200 })));
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar produto" }));
    expect(await within(ficha).findByRole("alert")).toHaveTextContent("Informe o status do produto.");
    expect(within(ficha).getByLabelText("Família")).toHaveValue("Velas");
  });
});

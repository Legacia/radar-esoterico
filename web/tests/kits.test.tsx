import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Kits, type FichaKit } from "../src/paginas/Kits";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

const BASE = {
  kits: [{ id: 1, nome: "Kit fictício 3 incensos", quantidade_planejada: 10 }, { id: 2, nome: "Kit fictício vazio", quantidade_planejada: 0 }],
  produtos: [{ id: 5, nome: "Incenso fictício", estoque_atual: 25 }, { id: 6, nome: "Suporte fictício", estoque_atual: 0 }],
  necessidade: [{ produto: "Incenso fictício", necessario: 30, estoque: 25, falta: 5 }, { produto: "Suporte fictício", necessario: 10, estoque: 12, falta: 0 }],
};
const KIT: FichaKit = {
  id: 1, nome: "Kit fictício 3 incensos", quantidade_planejada: 10, custo_unitario: "19.5", custo_lote: "195",
  componentes: [
    { produto_id: 5, produto: "Incenso fictício", quantidade: 3, estoque_atual: 25, custo_unitario_centavos: 450, codigo: "INC", data_cotacao: "2026-10-20", sku_fornecedor_id: 8 },
    { produto_id: 6, produto: "Suporte fictício", quantidade: 1, estoque_atual: 0, custo_unitario_centavos: null, codigo: null, data_cotacao: null, sku_fornecedor_id: null },
  ],
};
const COTACOES: Record<string, unknown[]> = {
  "5": [{ id: 8, fornecedor: "Fornecedor fictício", codigo: "INC", data_cotacao: "2026-10-20", custo_centavos: 450 }],
  "6": [],
};

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular() {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const c = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(c);
    const corpo = c.metodo !== "GET" ? { id: 3, ok: true }
      : c.caminho === "/api/kits" ? BASE
      : c.caminho.startsWith("/api/pesquisa/cotacoes") ? COTACOES[c.caminho.split("=").pop()!]
      : c.caminho === "/api/kits/2" ? { ...BASE.kits[1], componentes: [], custo_unitario: null, custo_lote: null }
      : { ...KIT, id: Number(c.caminho.split("/").pop()) };
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const mostrar = (hash = "#/kits") => {
  window.location.hash = hash;
  return render(<ProvedorNotificacoes><Kits /></ProvedorNotificacoes>);
};

describe("Kits", () => {
  it("mostra custo do kit e do lote como a API calculou e a necessidade conjunta", async () => {
    simular();
    mostrar();
    expect(await screen.findByText("Custo de um kit")).toBeInTheDocument();
    expect(screen.getByText("Custo de um kit").nextSibling).toHaveTextContent("R$ 19,50");
    expect(screen.getByText("Custo dos 10 kits planejados").nextSibling).toHaveTextContent("R$ 195,00");
    const suporte = screen.getAllByRole("cell", { name: "Suporte fictício" })[0].closest("tr")!;
    expect(suporte).toHaveTextContent("Sem cotação");
    const necessidade = screen.getByRole("region", { name: "Necessidade conjunta dos kits planejados" });
    const incenso = within(necessidade).getByRole("cell", { name: "Incenso fictício" }).closest("tr")!;
    expect(incenso).toHaveTextContent("30");
    expect(incenso).toHaveTextContent("5");
  });

  it("kit sem componentes pede para completar a composição", async () => {
    simular();
    mostrar("#/kits?kit=2");
    expect(await screen.findByText(/Complete a composição/)).toBeInTheDocument();
    expect(screen.getByText("Kit ainda sem componentes.")).toBeInTheDocument();
  });

  it("salva componente com a cotação escolhida e mantém o componente selecionado", async () => {
    const chamadas = simular();
    mostrar();
    const caixa = await screen.findByRole("region", { name: "Adicionar ou atualizar componente" });
    await within(caixa).findByLabelText("Cotação de custo do componente");
    await userEvent.clear(within(caixa).getByLabelText("Unidades desse componente por kit"));
    await userEvent.type(within(caixa).getByLabelText("Unidades desse componente por kit"), "4");
    await userEvent.click(within(caixa).getByRole("button", { name: "Salvar componente" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PUT")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({ caminho: "/api/kits/1/componentes/5", corpo: { quantidade: 4, cotacao_id: 8 } });
    expect(await screen.findByText("Componente salvo.")).toBeInTheDocument();
  });

  it("componente sem cotação orienta e estoque fica no produto escolhido depois de salvar", async () => {
    const chamadas = simular();
    mostrar();
    const caixa = await screen.findByRole("region", { name: "Adicionar ou atualizar componente" });
    await userEvent.selectOptions(within(caixa).getByLabelText("Componente"), "6");
    expect(await within(caixa).findByText(/Cadastre uma cotação para este componente/)).toBeInTheDocument();
    await userEvent.clear(within(caixa).getByLabelText("Estoque físico atual do componente"));
    await userEvent.type(within(caixa).getByLabelText("Estoque físico atual do componente"), "12");
    await userEvent.click(within(caixa).getByRole("button", { name: "Atualizar estoque físico" }));
    await waitFor(() => expect(chamadas.find((c) => c.caminho === "/api/estoque/6")?.corpo).toEqual({ estoque: 12 }));
    await screen.findByText("Estoque atualizado por produto.");
    await waitFor(() => expect(within(screen.getByRole("region", { name: "Adicionar ou atualizar componente" })).getByLabelText("Componente")).toHaveValue("6"));
  });

  it("campo de estoque mostra o valor salvo mesmo se a lista de produtos chegar depois da ficha", async () => {
    let salvo = false;
    let liberarLista!: () => void;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      const caminho = String(entrada);
      const metodo = init?.method ?? "GET";
      if (metodo === "PUT") { salvo = true; return new Response(JSON.stringify({ ok: true }), { status: 200 }); }
      if (caminho === "/api/kits") {
        if (salvo) await new Promise<void>((r) => { liberarLista = r; });
        const produtos = BASE.produtos.map((p) => (p.id === 5 && salvo ? { ...p, estoque_atual: 12 } : p));
        return new Response(JSON.stringify({ ...BASE, produtos }), { status: 200 });
      }
      if (caminho.startsWith("/api/pesquisa/cotacoes")) return new Response(JSON.stringify(COTACOES["5"]), { status: 200 });
      return new Response(JSON.stringify(KIT), { status: 200 });
    });
    mostrar();
    const caixa = await screen.findByRole("region", { name: "Adicionar ou atualizar componente" });
    const campo = () => within(screen.getByRole("region", { name: "Adicionar ou atualizar componente" })).getByLabelText("Estoque físico atual do componente");
    expect(within(caixa).getByLabelText("Estoque físico atual do componente")).toHaveValue("25");
    await userEvent.clear(campo());
    await userEvent.type(campo(), "12");
    await userEvent.click(within(caixa).getByRole("button", { name: "Atualizar estoque físico" }));
    await waitFor(() => expect(liberarLista).toBeDefined());
    liberarLista();
    await screen.findByText("Estoque atualizado por produto.");
    await waitFor(() => expect(campo()).toHaveValue("12"));
    await new Promise((r) => setTimeout(r, 50));
    expect(campo()).toHaveValue("12");
  });

  it("quantidades que não são inteiras são recusadas antes de enviar", async () => {
    const chamadas = simular();
    mostrar();
    const plano = await screen.findByRole("region", { name: "Plano do kit" });
    await userEvent.clear(within(plano).getByLabelText("Kits planejados"));
    await userEvent.type(within(plano).getByLabelText("Kits planejados"), "2,5");
    await userEvent.click(within(plano).getByRole("button", { name: "Salvar plano do kit" }));
    expect(await within(plano).findByRole("alert")).toHaveTextContent("inteiro não negativo");
    expect(chamadas.some((c) => c.metodo === "PUT")).toBe(false);
  });

  it("remove componente e cria kit uma vez só, abrindo o kit novo", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Remover Suporte fictício do kit" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "DELETE" && c.caminho === "/api/kits/1/componentes/6")).toBe(true));
    await screen.findByText("Componente removido.");
    await userEvent.click(screen.getByRole("button", { name: "Criar kit" }));
    const gaveta = screen.getByRole("dialog", { name: "Criar kit" });
    await userEvent.type(within(gaveta).getByLabelText("Nome do novo kit"), "Kit fictício novo");
    const formulario = within(gaveta).getByRole("button", { name: "Criar kit" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    await waitFor(() => expect(window.location.hash).toBe("#/kits?kit=3"));
    expect(chamadas.filter((c) => c.metodo === "POST")).toHaveLength(1);
  });
});

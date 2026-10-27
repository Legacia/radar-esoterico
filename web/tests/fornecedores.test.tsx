import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Fornecedores, type Ficha } from "../src/paginas/Fornecedores";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";
import { hojeIso } from "../src/formato";

const ETAPAS = ["Descoberto", "Em contato", "Cotado", "Em avaliação", "Fornecedor oficial", "Descartado ou pausado"];
const LISTA = {
  etapas: ETAPAS,
  fornecedores: [
    { id: 1, nome: "Fornecedor fictício Alfa", status: "Em avaliação", prazo: "7 dias", condicao_pagamento: "Pix", data_ultima_cotacao: "2026-10-20" },
    { id: 2, nome: "Fornecedor fictício Beta", status: "Em contato", prazo: "", condicao_pagamento: null, data_ultima_cotacao: null },
  ],
};
const FICHA: Ficha = {
  ...LISTA.fornecedores[0],
  cnpj: "00.000.000/0001-00", contato: "Contato fictício", pedido_minimo_centavos: 30000,
  data_oficial: null, motivo_descarte: null,
  cnpj_verificado: 1, condicoes_verificadas: 1, emite_nota: 0, amostra_avaliada: 1, reposicao_confirmada: 1,
  checklist: [
    { item: "Fornecedor ativo", cumprido: true },
    { item: "Emite nota fiscal", cumprido: false },
  ],
  margem_minima_pct: "0.20",
  limite_cotacao_dias: 15,
  skus: [{
    id: 5, codigo: "KIT-01", produto_id: 3, produto: "Kit fictício", fornecedor_id: 1, fornecedor: "Fornecedor fictício Alfa",
    custo_centavos: 2000, quantidade_minima: 10, data_cotacao: "2026-09-01", cotacao_antiga: true,
    preco_venda_centavos: 5990, contribuicao: "14.33", margem_pct: "0.2392320534223706176961602671",
    preco_minimo: "55.56", aviso_preco_minimo: null,
  }],
  contatos: [{ id: 1, data: "2026-10-19", canal: "WhatsApp", resumo: "Pedido de catálogo", situacao_resposta: "aguardando" }],
};

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(respostas: Record<string, unknown> = {}) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const caminho = String(entrada);
    const metodo = init?.method ?? "GET";
    chamadas.push({ caminho, metodo, corpo: init?.body ? JSON.parse(String(init.body)) : undefined });
    const chave = `${metodo} ${caminho}`;
    const corpo = chave in respostas ? respostas[chave]
      : caminho === "/api/fornecedores" && metodo === "GET" ? LISTA
      : /^\/api\/fornecedores\/\d+$/.test(caminho) && metodo === "GET" ? { ...FICHA, id: Number(caminho.split("/").pop()) }
      : { id: 7, ok: true };
    return new Response(JSON.stringify(corpo), { status: 200 });
  });
  return chamadas;
}

const mostrar = (hash = "#/fornecedores") => {
  window.location.hash = hash;
  return render(<ProvedorNotificacoes><Fornecedores /></ProvedorNotificacoes>);
};

describe("Fornecedores", () => {
  it("lista com contadores por etapa e filtra pelo endereço", async () => {
    simular();
    mostrar("#/fornecedores?etapa=Em+contato");
    expect(await screen.findByRole("cell", { name: "Fornecedor fictício Beta" })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "Fornecedor fictício Alfa" })).toBeNull();
    const filtro = screen.getByRole("link", { name: /1\s*Em contato/ });
    expect(filtro).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: /2\s*Todas as etapas/ })).toBeInTheDocument();
    expect(screen.getAllByText("Não informado").length).toBeGreaterThan(0);
  });

  it("abre a ficha ao clicar e mostra o que a API calculou", async () => {
    simular();
    mostrar();
    await userEvent.click(await screen.findByRole("cell", { name: "Fornecedor fictício Alfa" }));
    expect(window.location.hash).toBe("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    expect(within(ficha).getByText("1 de 2 itens do checklist")).toBeInTheDocument();
    expect(within(ficha).getByText("R$ 300,00")).toBeInTheDocument();
    expect(within(ficha).getByText(/pelo menos 20,0% em três produtos/)).toBeInTheDocument();
    await userEvent.click(within(ficha).getByRole("tab", { name: "SKUs cotados (1)" }));
    const linha = within(ficha).getByRole("cell", { name: "KIT-01" }).closest("tr")!;
    expect(linha).toHaveTextContent("R$ 14,33");
    expect(linha).toHaveTextContent("23,9%");
    expect(linha).toHaveTextContent("R$ 55,56");
    expect(within(ficha).getByText(/mais de 15 dias/)).toBeInTheDocument();
  });

  it("promover com pendências lista o que falta e não finge que promoveu", async () => {
    const chamadas = simular({ "POST /api/fornecedores/1/promover": { promovido: false, pendencias: ["Emite nota fiscal"] } });
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(within(ficha).getByRole("button", { name: "Promover a fornecedor oficial" }));
    const aviso = await within(ficha).findByRole("alert");
    expect(aviso).toHaveTextContent("Promoção não realizada");
    expect(aviso).toHaveTextContent("Emite nota fiscal");
    expect(chamadas.filter((c) => c.caminho === "/api/fornecedores/1/promover")).toHaveLength(1);
    expect(screen.queryByText("Fornecedor promovido a oficial.")).toBeNull();
  });

  it("cadastra e abre a ficha do novo fornecedor", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar fornecedor" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar fornecedor" });
    await userEvent.type(within(gaveta).getByLabelText("Nome do fornecedor"), "Fornecedor fictício Gama");
    await userEvent.clear(within(gaveta).getByLabelText("Pedido mínimo (R$)"));
    await userEvent.type(within(gaveta).getByLabelText("Pedido mínimo (R$)"), "1.234,56");
    await userEvent.click(within(gaveta).getByLabelText("Emite nota fiscal"));
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar fornecedor" }));
    await waitFor(() => expect(window.location.hash).toBe("#/fornecedores?ficha=7"));
    const post = chamadas.find((c) => c.caminho === "/api/fornecedores" && c.metodo === "POST")!;
    expect(post.corpo).toMatchObject({ nome: "Fornecedor fictício Gama", pedido_minimo: "1.234,56", emite_nota: true, cnpj_verificado: false });
  });

  it("cliques repetidos ao salvar enviam uma vez só", async () => {
    const chamadas = simular();
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar fornecedor" }));
    const gaveta = screen.getByRole("dialog", { name: "Cadastrar fornecedor" });
    await userEvent.type(within(gaveta).getByLabelText("Nome do fornecedor"), "Fornecedor fictício");
    const formulario = within(gaveta).getByRole("button", { name: "Salvar fornecedor" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    await waitFor(() => expect(window.location.hash).toBe("#/fornecedores?ficha=7"));
    expect(chamadas.filter((c) => c.caminho === "/api/fornecedores" && c.metodo === "POST")).toHaveLength(1);
  });

  it("erro da API aparece no formulário da ficha", async () => {
    simular();
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Condições e verificações" }));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Informe o CNPJ antes de marcá-lo como verificado." }), { status: 400 }));
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar fornecedor" }));
    expect(await within(ficha).findByRole("alert")).toHaveTextContent("Informe o CNPJ antes");
  });

  it("registra contato com data ISO e limpa o formulário", async () => {
    const chamadas = simular();
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Contatos (1)" }));
    expect(within(ficha).getByRole("cell", { name: "19/10/2026" })).toBeInTheDocument();
    expect(within(ficha).getByLabelText("Data do contato")).toHaveAttribute("max", hojeIso());
    await userEvent.type(within(ficha).getByLabelText("Canal"), "E-mail");
    await userEvent.type(within(ficha).getByLabelText("Resumo do contato"), "Pedido de amostra fictício");
    await userEvent.selectOptions(within(ficha).getByLabelText("Situação da resposta"), "aguardando");
    await userEvent.click(within(ficha).getByRole("button", { name: "Adicionar contato" }));
    await waitFor(() => expect(within(ficha).getByLabelText("Canal")).toHaveValue(""));
    const post = chamadas.find((c) => c.caminho === "/api/fornecedores/1/contatos")!;
    expect(post.corpo).toEqual({ data: hojeIso(), canal: "E-mail", resumo: "Pedido de amostra fictício", situacao_resposta: "aguardando" });
  });

  it("descartar exige motivo antes de enviar", async () => {
    const chamadas = simular();
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.selectOptions(within(ficha).getByLabelText("Etapa de acompanhamento"), "Descartado ou pausado");
    expect(within(ficha).getByLabelText("Motivo para descartar ou pausar")).toBeRequired();
    expect(within(ficha).queryByRole("option", { name: "Fornecedor oficial" })).toBeNull();
    await userEvent.type(within(ficha).getByLabelText("Motivo para descartar ou pausar"), "Preço alto");
    await userEvent.click(within(ficha).getByRole("button", { name: "Alterar etapa" }));
    await waitFor(() => expect(chamadas.some((c) => c.caminho === "/api/fornecedores/1/etapa")).toBe(true));
    expect(chamadas.find((c) => c.caminho === "/api/fornecedores/1/etapa")!.corpo)
      .toEqual({ etapa: "Descartado ou pausado", motivo: "Preço alto" });
  });

  it("formulário reaberto durante a gravação mostra os dados salvos quando a ficha recarrega", async () => {
    simular();
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Condições e verificações" }));
    await userEvent.click(within(ficha).getByLabelText("Emite nota fiscal"));
    let liberar!: () => void;
    let salvo = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      const caminho = String(entrada);
      if (init?.method === "PUT") { await new Promise<void>((r) => { liberar = r; }); salvo = true; }
      const corpo = caminho === "/api/fornecedores" && init?.method === "GET" ? LISTA
        : caminho === "/api/fornecedores/1" && init?.method === "GET" ? { ...FICHA, emite_nota: salvo ? 1 : 0 } : { id: 1 };
      return new Response(JSON.stringify(corpo), { status: 200 });
    });
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar fornecedor" }));
    await userEvent.click(within(ficha).getByRole("tab", { name: "Checklist e etapa" }));
    await userEvent.click(within(ficha).getByRole("tab", { name: "Condições e verificações" }));
    expect(within(ficha).getByLabelText("Emite nota fiscal")).not.toBeChecked();
    liberar();
    await waitFor(() => expect(within(ficha).getByLabelText("Emite nota fiscal")).toBeChecked());
  });

  it("ficha fechada e reaberta durante a gravação recarrega quando ela termina", async () => {
    simular();
    mostrar("#/fornecedores?ficha=1");
    let ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(within(ficha).getByRole("tab", { name: "Condições e verificações" }));
    await userEvent.click(within(ficha).getByLabelText("Emite nota fiscal"));
    let liberar!: () => void;
    let salvo = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
      const caminho = String(entrada);
      if (init?.method === "PUT") { await new Promise<void>((r) => { liberar = r; }); salvo = true; }
      const corpo = caminho === "/api/fornecedores" && init?.method === "GET" ? LISTA
        : caminho === "/api/fornecedores/1" && init?.method === "GET" ? { ...FICHA, emite_nota: salvo ? 1 : 0 } : { id: 1 };
      return new Response(JSON.stringify(corpo), { status: 200 });
    });
    await userEvent.click(within(ficha).getByRole("button", { name: "Salvar fornecedor" }));
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    window.location.hash = "#/fornecedores?ficha=1";
    ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    await userEvent.click(await within(ficha).findByRole("tab", { name: "Condições e verificações" }));
    expect(within(ficha).getByLabelText("Emite nota fiscal")).not.toBeChecked();
    liberar();
    await waitFor(() => expect(within(ficha).getByLabelText("Emite nota fiscal")).toBeChecked());
  });

  it("abas trocam com as setas do teclado", async () => {
    simular();
    mostrar("#/fornecedores?ficha=1");
    const ficha = await screen.findByRole("dialog", { name: "Fornecedor fictício Alfa" });
    within(ficha).getByRole("tab", { name: "Checklist e etapa" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(within(ficha).getByRole("tab", { name: "Condições e verificações" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(within(ficha).getByRole("tab", { name: "Contatos (1)" })).toHaveFocus();
  });
});

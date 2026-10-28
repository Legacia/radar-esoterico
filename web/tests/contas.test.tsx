import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Contas, type Conta } from "../src/paginas/Contas";
import { ProvedorNotificacoes } from "../src/componentes/Notificacoes";

type Chamada = { caminho: string; metodo: string; corpo: unknown };

function simular(resposta: (c: Chamada) => { status?: number; corpo: unknown }) {
  const chamadas: Chamada[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada, init) => {
    const chamada = { caminho: String(entrada), metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(chamada);
    const r = resposta(chamada);
    return new Response(JSON.stringify(r.corpo), { status: r.status ?? 200 });
  });
  return chamadas;
}

const ANNA: Conta = { id: 2, nome: "Pessoa B", email: "b@example.invalid" };
const mostrar = () => render(<ProvedorNotificacoes><Contas /></ProvedorNotificacoes>);

async function preencherNova(senha: string, repetir: string) {
  const caixa = await screen.findByRole("region", { name: "Nova conta" });
  await userEvent.type(within(caixa).getByLabelText("Nome"), "Pessoa B");
  await userEvent.type(within(caixa).getByLabelText("E-mail"), "b@example.invalid");
  await userEvent.type(within(caixa).getByLabelText("Senha (mínimo 8 caracteres)"), senha);
  await userEvent.type(within(caixa).getByLabelText("Repita a senha"), repetir);
  await userEvent.click(within(caixa).getByRole("button", { name: "Criar conta" }));
  return caixa;
}

describe("Contas", () => {
  it("cria uma conta, recarrega a lista e limpa o formulário", async () => {
    let lista: Conta[] = [{ id: 1, nome: "Pessoa A", email: "a@example.invalid" }];
    const chamadas = simular((c) => {
      if (c.metodo === "POST") { lista = [...lista, ANNA]; return { corpo: { id: 2 } }; }
      return { corpo: { contas: lista } };
    });
    mostrar();
    const caixa = await preencherNova("senha-ficticia-1", "senha-ficticia-1");
    expect(await screen.findByText("b@example.invalid")).toBeInTheDocument();
    expect(chamadas.find((c) => c.metodo === "POST")!.corpo).toEqual({ nome: "Pessoa B", email: "b@example.invalid", senha: "senha-ficticia-1" });
    expect(within(caixa).getByLabelText("Nome")).toHaveValue("");
  });

  it("não envia quando as senhas não coincidem e mostra o erro da API", async () => {
    const chamadas = simular((c) => c.metodo === "POST"
      ? { status: 400, corpo: { detail: "Já existe uma conta com esse e-mail." } }
      : { corpo: { contas: [] } });
    mostrar();
    const caixa = await preencherNova("senha-ficticia-1", "outra-coisa-12");
    expect(within(caixa).getByRole("alert")).toHaveTextContent("As senhas não coincidem.");
    expect(chamadas.some((c) => c.metodo === "POST")).toBe(false);
    await userEvent.clear(within(caixa).getByLabelText("Repita a senha"));
    await userEvent.type(within(caixa).getByLabelText("Repita a senha"), "senha-ficticia-1");
    await userEvent.click(within(caixa).getByRole("button", { name: "Criar conta" }));
    expect(await within(caixa).findByRole("alert")).toHaveTextContent("Já existe uma conta com esse e-mail.");
    expect(within(caixa).getByLabelText("Nome")).toHaveValue("Pessoa B");
  });

  it("troca a senha de uma conta pela gaveta", async () => {
    const chamadas = simular((c) => c.metodo === "PUT" ? { corpo: { ok: true } } : { corpo: { contas: [ANNA] } });
    mostrar();
    await userEvent.click(await screen.findByRole("button", { name: "Trocar senha" }));
    const gaveta = screen.getByRole("dialog", { name: "Trocar senha de Pessoa B" });
    await userEvent.type(within(gaveta).getByLabelText("Senha (mínimo 8 caracteres)"), "senha-nova-123");
    await userEvent.type(within(gaveta).getByLabelText("Repita a senha"), "senha-nova-123");
    await userEvent.click(within(gaveta).getByRole("button", { name: "Salvar senha" }));
    expect(await screen.findByText(/Senha de Pessoa B trocada/)).toBeInTheDocument();
    expect(chamadas.find((c) => c.metodo === "PUT")).toMatchObject({ caminho: "/api/contas/2/senha", corpo: { senha: "senha-nova-123" } });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

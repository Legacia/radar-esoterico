import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Importar, type Relatorio } from "../src/paginas/Importar";

const CSV = "marketplace;titulo;url;preco;data\nLoja fictícia;Kit;https://example.invalid/1;59,90;2026-10-20\n";
const arquivo = () => new File([CSV], "anuncios.csv", { type: "text/csv" });

function simular(resposta: { status?: number; corpo: unknown }, espera?: Promise<void>) {
  const chamadas: RequestInit[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_e, init) => {
    chamadas.push(init!);
    if (espera) await espera;
    return new Response(JSON.stringify(resposta.corpo), { status: resposta.status ?? 200 });
  });
  return chamadas;
}

describe("Importar CSV", () => {
  it("envia o arquivo cru e mostra o relatório com as linhas rejeitadas", async () => {
    const relatorio: Relatorio = { importadas: 3, repetidas: 1, erros: [
      { linha: 5, erro: "Data inválida. Use AAAA-MM-DD." }, { linha: 7, erro: "O preço observado deve ser maior que zero." }] };
    const chamadas = simular({ corpo: relatorio });
    render(<Importar />);
    const botao = screen.getByRole("button", { name: "Importar arquivo" });
    expect(botao).toBeDisabled();
    await userEvent.upload(screen.getByLabelText("Arquivo CSV"), arquivo());
    await userEvent.click(botao);
    expect(await screen.findByRole("region", { name: "Última importação: anuncios.csv" })).toBeInTheDocument();
    expect(screen.getByText("Preços adicionados").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("Já existentes").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Linhas com erro").nextSibling).toHaveTextContent("2");
    expect(screen.getByRole("cell", { name: "Data inválida. Use AAAA-MM-DD." })).toBeInTheDocument();
    expect(chamadas[0].body).toBeInstanceOf(File);
    expect((chamadas[0].headers as Record<string, string>)["Content-Type"]).toBe("text/csv");
    expect(screen.getByRole("button", { name: "Importar arquivo" })).toBeDisabled();
  });

  it("arquivo recusado mostra a explicação do servidor", async () => {
    simular({ status: 400, corpo: { detail: "Salve o CSV com codificação UTF-8." } });
    render(<Importar />);
    await userEvent.upload(screen.getByLabelText("Arquivo CSV"), arquivo());
    await userEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("UTF-8");
    expect(screen.queryByText(/Última importação/)).toBeNull();
  });

  it("cliques repetidos enviam o arquivo uma vez só", async () => {
    let liberar!: () => void;
    const chamadas = simular({ corpo: { importadas: 1, repetidas: 0, erros: [] } }, new Promise((r) => { liberar = r; }));
    render(<Importar />);
    await userEvent.upload(screen.getByLabelText("Arquivo CSV"), arquivo());
    const formulario = screen.getByRole("button", { name: "Importar arquivo" }).closest("form")!;
    fireEvent.submit(formulario);
    fireEvent.submit(formulario);
    expect(await screen.findByRole("button", { name: "Importando…" })).toBeDisabled();
    liberar();
    await waitFor(() => expect(screen.getByText("Preços adicionados")).toBeInTheDocument());
    expect(chamadas).toHaveLength(1);
  });
});

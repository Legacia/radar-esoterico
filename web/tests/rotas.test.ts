import { describe, expect, it } from "vitest";
import { PAGINAS, SECOES, enderecoDe, lerRota } from "../src/rotas";

describe("rotas", () => {
  it("lê página e filtros do endereço", () => {
    expect(lerRota("#/fornecedores?etapa=Cotado&q=bru%C3%A7a")).toEqual({
      pagina: "fornecedores", filtros: { etapa: "Cotado", q: "bruça" },
    });
  });

  it("volta ao painel quando a página não existe", () => {
    expect(lerRota("").pagina).toBe("painel");
    expect(lerRota("#/nao-existe").pagina).toBe("painel");
  });

  it("monta o endereço sem filtros vazios", () => {
    expect(enderecoDe("kits")).toBe("#/kits");
    expect(enderecoDe("pesquisa", { q: "incenso", etapa: "" })).toBe("#/pesquisa?q=incenso");
  });

  it("tem as oito telas nas quatro seções", () => {
    expect(SECOES.map((s) => s.titulo)).toEqual(["Visão geral", "Fornecimento", "Mercado", "Decisão"]);
    expect(PAGINAS).toHaveLength(8);
    expect(new Set(PAGINAS.map((p) => p.chave)).size).toBe(8);
  });
});

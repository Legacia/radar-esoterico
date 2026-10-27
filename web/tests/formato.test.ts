import { describe, expect, it } from "vitest";
import { dataBr, percentual, reais, reaisDeCentavos } from "../src/formato";

describe("formatação de valores", () => {
  it("mostra o caso obrigatório da margem como vem da API", () => {
    expect(reais("14.33")).toBe("R$ 14,33");
    expect(percentual("0.2392320534223706176961602671")).toBe("23,9%");
    expect(reais("55.56")).toBe("R$ 55,56");
  });

  it("arredonda texto decimal sem ponto flutuante", () => {
    expect(reais("1.005")).toBe("R$ 1,01"); // em float, 1.005 viraria 1,00
    expect(reais("0.1")).toBe("R$ 0,10");
    expect(reais("999.995")).toBe("R$ 1.000,00");
    expect(reais("1234567.8")).toBe("R$ 1.234.567,80");
    expect(reais("12345678901234567890.12")).toBe("R$ 12.345.678.901.234.567.890,12");
  });

  it("trata negativos e zero", () => {
    expect(reais("-3")).toBe("-R$ 3,00");
    expect(reais("-0.001")).toBe("R$ 0,00");
    expect(percentual("-0.05")).toBe("-5,0%");
    expect(percentual("0")).toBe("0,0%");
  });

  it("converte centavos inteiros", () => {
    expect(reaisDeCentavos(143300)).toBe("R$ 1.433,00");
    expect(reaisDeCentavos(5)).toBe("R$ 0,05");
    expect(reaisDeCentavos(-250)).toBe("-R$ 2,50");
    expect(() => reaisDeCentavos(1.5)).toThrow();
  });

  it("formata percentuais e datas", () => {
    expect(percentual("0.20")).toBe("20,0%");
    expect(percentual("0.2", 0)).toBe("20%");
    expect(percentual("12.5")).toBe("1.250,0%");
    expect(dataBr("2026-10-26")).toBe("26/10/2026");
  });

  it("recusa valores que não são decimais", () => {
    expect(() => reais("14,33")).toThrow();
    expect(() => reais("abc")).toThrow();
    expect(() => percentual("")).toThrow();
    expect(() => dataBr("26/10/2026")).toThrow();
  });
});

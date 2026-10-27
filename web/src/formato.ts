// Só apresentação: a API manda dinheiro como texto decimal ("14.33") ou centavos inteiros e
// percentuais como fração em texto ("0.2392"). Nada aqui usa número de ponto flutuante:
// os valores são tratados como texto e inteiros grandes (BigInt). Nenhuma conta de negócio.

const DECIMAL = /^(-)?(\d+)(?:\.(\d+))?$/;

/** Arredonda um texto decimal para `casas` casas (metade para longe do zero). */
export function arredondar(texto: string, casas: number): { negativo: boolean; inteiro: string; fracao: string } {
  const partes = DECIMAL.exec(texto.trim());
  if (!partes) throw new Error(`Valor inválido: ${texto}`);
  const [, sinal, inteiro, fracao = ""] = partes;
  const completo = (fracao + "0".repeat(casas + 1)).slice(0, casas + 1);
  let unidades = BigInt(inteiro + completo.slice(0, casas));
  if (Number(completo[casas]) >= 5) unidades += 1n;
  const digitos = unidades.toString().padStart(casas + 1, "0");
  const corte = digitos.length - casas;
  return {
    negativo: sinal === "-" && unidades !== 0n,
    inteiro: digitos.slice(0, corte),
    fracao: digitos.slice(corte),
  };
}

function milhares(inteiro: string): string {
  return inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** "1234.5" → "R$ 1.234,50"; "-3" → "-R$ 3,00". */
export function reais(texto: string): string {
  const { negativo, inteiro, fracao } = arredondar(texto, 2);
  return `${negativo ? "-" : ""}R$ ${milhares(inteiro)},${fracao}`;
}

/** 143300 → "R$ 1.433,00". */
export function reaisDeCentavos(centavos: number): string {
  if (!Number.isSafeInteger(centavos)) throw new Error(`Centavos inválidos: ${centavos}`);
  const texto = BigInt(centavos).toString();
  const negativo = texto.startsWith("-");
  const digitos = (negativo ? texto.slice(1) : texto).padStart(3, "0");
  return reais(`${negativo ? "-" : ""}${digitos.slice(0, -2)}.${digitos.slice(-2)}`);
}

/** Fração em texto para percentual: "0.2392" → "23,9%". */
export function percentual(fracao: string, casas = 1): string {
  const partes = DECIMAL.exec(fracao.trim());
  if (!partes) throw new Error(`Valor inválido: ${fracao}`);
  const [, sinal = "", inteiro, decimais = ""] = partes;
  // Multiplicar por 100 é só mover a vírgula duas casas.
  const deslocado = (decimais + "00");
  const texto = `${sinal}${inteiro}${deslocado.slice(0, 2)}.${deslocado.slice(2) || "0"}`;
  const { negativo, inteiro: parte, fracao: resto } = arredondar(texto, casas);
  const numero = milhares(String(BigInt(parte)));
  return `${negativo ? "-" : ""}${numero}${casas ? "," + resto : ""}%`;
}

/** "2026-10-26" → "26/10/2026". */
export function dataBr(iso: string): string {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!partes) throw new Error(`Data inválida: ${iso}`);
  return `${partes[3]}/${partes[2]}/${partes[1]}`;
}

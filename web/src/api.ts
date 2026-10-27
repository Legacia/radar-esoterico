// Acesso à API do Radar. O cookie de sessão é HttpOnly: a página nunca o lê, o navegador o
// envia sozinho. Toda resposta 401 avisa a aplicação para voltar à tela de entrada.

export type Usuario = { id: number; nome: string };

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

let aoPerderSessao: (() => void) | null = null;

export function quandoPerderSessao(funcao: (() => void) | null) {
  aoPerderSessao = funcao;
}

export async function pedir<T>(caminho: string, opcoes: { metodo?: string; corpo?: unknown; arquivo?: Blob } = {}): Promise<T> {
  // "arquivo" vai cru, como o próprio conteúdo do CSV; "corpo" vai como JSON.
  const envio = opcoes.arquivo ?? (opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo));
  const tipo = opcoes.arquivo ? "text/csv" : "application/json";
  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, {
      method: opcoes.metodo ?? (envio === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      headers: envio === undefined ? undefined : { "Content-Type": tipo },
      body: envio,
    });
  } catch {
    throw new ErroApi(0, "Sem conexão com o servidor do Radar. Confira se ele está ligado.");
  }
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    if (resposta.status === 401 && caminho !== "/entrar") aoPerderSessao?.();
    const detalhe = typeof dados?.detail === "string" ? dados.detail : "Algo deu errado. Tente de novo.";
    throw new ErroApi(resposta.status, detalhe);
  }
  return dados as T;
}

export const entrar = (email: string, senha: string) => pedir<Usuario>("/entrar", { corpo: { email, senha } });
export const sair = () => pedir<{ ok: boolean }>("/sair", { metodo: "POST" });
export const quemSou = () => pedir<Usuario>("/eu");

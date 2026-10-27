// Trava de gravação de uma tela. Liga no início do envio e só desliga depois que a tela recarregou,
// mesmo se a gaveta for fechada no meio. Assim nenhum formulário parte de dados antigos e um
// clique repetido não grava duas vezes.
import { useCallback, useRef, useState } from "react";
import { ErroApi } from "../api";

export type Executar = <T>(acao: () => Promise<T>) => Promise<T | undefined>;

export function useGravacao() {
  const [ocupado, setOcupado] = useState(false);
  const trava = useRef(false);

  const executar: Executar = useCallback(async (acao) => {
    if (trava.current) return undefined;
    trava.current = true;
    setOcupado(true);
    try {
      return await acao();
    } finally {
      trava.current = false;
      setOcupado(false);
    }
  }, []);

  return { ocupado, executar };
}

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : "Não foi possível salvar. Tente de novo.";
}

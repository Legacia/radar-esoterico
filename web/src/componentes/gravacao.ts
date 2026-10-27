// Trava de gravação de uma tela. Liga no início do envio e só desliga depois que a tela recarregou,
// mesmo se a gaveta for fechada no meio. Assim nenhum formulário parte de dados antigos e um
// clique repetido não grava duas vezes.
import { useCallback, useRef, useState } from "react";
import { ErroApi } from "../api";

export type Executar = <T>(acao: () => Promise<T>) => Promise<T | undefined>;

export function useGravacao() {
  const [ocupado, setOcupado] = useState(false);
  // Conta as gravações terminadas: quem abriu dados durante uma gravação recarrega quando ela acaba.
  const [concluidas, setConcluidas] = useState(0);
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
      setConcluidas((n) => n + 1);
    }
  }, []);

  return { ocupado, executar, concluidas };
}

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : "Não foi possível salvar. Tente de novo.";
}

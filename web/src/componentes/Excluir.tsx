// Exclusão em dois passos: o primeiro clique pede confirmação, o segundo apaga. Se a API recusar
// (por exemplo, por haver histórico ligado), a explicação dela aparece ao lado do botão.
import { useState } from "react";
import { Aviso } from "./basicos";
import { mensagemDeErro } from "./gravacao";

export function BotaoExcluir({ rotulo, pergunta, ocupado, aoConfirmar }: {
  rotulo: string;
  pergunta: string;
  ocupado: boolean;
  aoConfirmar: () => Promise<unknown>;
}) {
  const [confirmando, setConfirmando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function confirmar() {
    setErro(null);
    try {
      await aoConfirmar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
    setConfirmando(false);
  }

  return (
    <div className="pilha">
      {!confirmando ? (
        <div><button type="button" className="botao botao-perigo" disabled={ocupado} onClick={() => { setErro(null); setConfirmando(true); }}>{rotulo}</button></div>
      ) : (
        <div role="group" aria-label={pergunta}>
          <span>{pergunta} Não dá para desfazer. </span>
          <button type="button" className="botao botao-perigo" disabled={ocupado} onClick={confirmar}>Sim, excluir</button>{" "}
          <button type="button" className="botao" onClick={() => setConfirmando(false)}>Cancelar</button>
        </div>
      )}
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
    </div>
  );
}

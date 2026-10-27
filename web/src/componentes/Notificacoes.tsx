// Notificações passageiras ("Fornecedor salvo."). Somem sozinhas depois de alguns segundos.
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Notificacao = { id: number; texto: string; tipo: "sucesso" | "erro" };
type Notificar = (texto: string, tipo?: Notificacao["tipo"]) => void;

const Contexto = createContext<Notificar>(() => {});
const DURACAO_MS = 5000;
let proximo = 1;

export function ProvedorNotificacoes({ children }: { children: ReactNode }) {
  const [lista, setLista] = useState<Notificacao[]>([]);
  const fechar = useCallback((id: number) => setLista((atual) => atual.filter((n) => n.id !== id)), []);
  const notificar = useCallback<Notificar>((texto, tipo = "sucesso") => {
    const id = proximo++;
    setLista((atual) => [...atual, { id, texto, tipo }]);
    window.setTimeout(() => fechar(id), DURACAO_MS);
  }, [fechar]);

  return (
    <Contexto.Provider value={notificar}>
      {children}
      <div className="notificacoes" aria-live="polite">
        {lista.map((n) => (
          <div key={n.id} className={`notificacao notificacao-${n.tipo}`}>
            <span>{n.texto}</span>
            <button type="button" className="botao-discreto" aria-label="Fechar aviso" onClick={() => fechar(n.id)}>✕</button>
          </div>
        ))}
      </div>
    </Contexto.Provider>
  );
}

export const useNotificar = () => useContext(Contexto);

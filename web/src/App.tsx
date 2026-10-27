import { useCallback, useEffect, useState } from "react";
import { ErroApi, quandoPerderSessao, quemSou, sair, type Usuario } from "./api";
import { ProvedorNotificacoes } from "./componentes/Notificacoes";
import { Entrada } from "./paginas/Entrada";
import { Shell } from "./paginas/Shell";

type Estado =
  | { tipo: "carregando" }
  | { tipo: "fora"; aviso?: string }
  | { tipo: "dentro"; usuario: Usuario };

export function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });

  useEffect(() => {
    // Qualquer 401 depois da entrada (sessão de 8 horas vencida, servidor reiniciado) volta à entrada.
    quandoPerderSessao(() => setEstado({ tipo: "fora", aviso: "Sua sessão terminou. Entre novamente." }));
    quemSou().then((usuario) => setEstado({ tipo: "dentro", usuario }), () => setEstado({ tipo: "fora" }));
    return () => quandoPerderSessao(null);
  }, []);

  const aoSair = useCallback(async () => {
    // Só volta à entrada se o servidor confirmou a saída ou se a sessão já não valia (401).
    // Sem conexão, a sessão continua viva no servidor: o erro sobe para a tela avisar.
    try {
      await sair();
    } catch (erro) {
      if (!(erro instanceof ErroApi && erro.status === 401)) throw erro;
    }
    setEstado({ tipo: "fora" });
  }, []);

  return (
    <ProvedorNotificacoes>
      {estado.tipo === "carregando" && <p className="carregando">Carregando…</p>}
      {estado.tipo === "fora" && (
        <Entrada aviso={estado.aviso} aoEntrar={(usuario) => setEstado({ tipo: "dentro", usuario })} />
      )}
      {estado.tipo === "dentro" && <Shell usuario={estado.usuario} aoSair={aoSair} />}
    </ProvedorNotificacoes>
  );
}
